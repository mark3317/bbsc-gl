"""Late discovery with durable, single-writer world sessions.

Each process owns an independent home journal. A guest is durably reserved before
the host commits its admission. Only the host writes that world's state; a guest
never promotes itself on timeout. Legacy unanimous invitations use Engine instead.
The selected private network remains the discovery/trust boundary.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
from pathlib import Path
import queue
import re
import secrets
import socket
import socketserver
import struct
import threading
import time

from engine import MAX_FRAME, atomic_json, canonical, initial, remove_room_guest, transition, validate_invite
from retirement import terminal, scope as native_scope, validate as validate_retirement


def member(offer):
    return {k: offer[k] for k in ('id', 'host', 'port', 'p2p', 'name')}


def validate_offer(offer):
    validate_invite(dict(version=1, secret='00'*32, members=[member(offer)]))
    if not re.fullmatch('[a-f0-9]{64}', offer['seed']):
        raise ValueError('Invalid discovery identity')


def session(cfg, state):
    return [cfg['group'], state['generation']]


def admission_ticket(state, who):
    if who == state['owner']:
        return 0
    if who in state['pending']:
        return state['pending'][who].get('ticket')
    room = state.get('room') or {}
    member = room.get('members', {}).get(who) or room.get('departing', {}).get(who)
    return member.get('admission_ticket', 0) if member else None


def read_frame(sock):
    def exact(size):
        data = bytearray()
        while len(data) < size:
            part = sock.recv(size-len(data))
            if not part:
                raise OSError('Closed party connection')
            data.extend(part)
        return bytes(data)
    size, = struct.unpack('<I', exact(4))
    if not 0 < size <= MAX_FRAME:
        raise ValueError('Oversized party RPC')
    return json.loads(exact(size))


def write_frame(sock, body):
    raw = canonical(body)
    if len(raw) > MAX_FRAME:
        raise ValueError('Oversized party RPC')
    sock.sendall(struct.pack('<I', len(raw))+raw)


class DynamicEngine:
    dynamic = True
    def __init__(self, cfg, who, profile, peers_file):
        validate_invite(cfg)
        self.cfg = copy.deepcopy(cfg)
        self.id, self.profile = who, Path(profile)
        self.identity = copy.deepcopy(cfg['identity'])
        validate_offer(self.identity)
        self.member = member(self.identity)
        if who != self.identity['id'] or cfg['members'] != [self.member]:
            raise ValueError('Dynamic configuration must contain only its own identity')
        self.path = self.profile/'dynamic-journal.json'
        self.peers_file = Path(peers_file)
        self.lock = threading.RLock()
        self.mutation = threading.Lock()
        self.stop_event = threading.Event()
        self.peers = {who: self.identity}
        self.members = {who: self.member}
        self.signs = {}
        self.local_status = {'sign': None}
        self.native_status = {}
        self.native_at = 0
        self.bell_ring_seq = 0
        self.bell_ring_generation = 0
        self.bell_seen = {}
        self.admitted_incarnations = {}
        self.bell_notices = 0
        self.bell_released_notice = 0
        self.yielding_search = None
        self.host_intent_generation = None
        self.update_seq = 0
        self.pending_local = None
        self.finished_commands = {}
        self.storage_error = None
        self.diagnostic = None
        self.relay_error = None
        self.relay_peer_errors = {}
        self.relay_network_errors = {}
        self.relay_reopening = set()
        self.relay_in = queue.Queue(128)
        self.relay_transport = 0
        self.relay_next_stream = 0
        self.relay_peer_streams = {}
        self.relay_workers = {}
        self.relay_sequences = {}
        self.relay_buffers = {}
        self.relay_active = {}
        self.relay_threads = []
        self.relay_enqueue = threading.Lock()
        self.blocked = set()  # Fault injection on isolated test networks.
        # Bind before persisting anything; a second process cannot touch this journal.
        outer = self

        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = False
            daemon_threads = True
            request_queue_size = 128

            def server_bind(self):
                if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                super().server_bind()

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.settimeout(2)
                try:
                    request = read_frame(self.request)
                    sender = request['from']
                    with outer.lock:
                        known = sender in outer.peers
                    if not known:
                        outer.refresh_peers()
                    with outer.lock:
                        peer = outer.peers.get(sender)
                        if not peer or peer['host'] != self.client_address[0] or sender in outer.blocked:
                            return
                        outer.verify(sender, request)
                    try:
                        result = {'ok': True, 'result': outer.dispatch(sender, request['body'])}
                    except (ValueError, KeyError) as error:
                        result = {'ok': False, 'error': str(error)}
                    write_frame(self.request, outer.signed(sender, dict(result, nonce=request['nonce'])))
                except (OSError, ValueError, KeyError, TypeError):
                    pass

        self.server = Server((self.member['host'], self.member['port']), Handler)
        try:
            previous = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else None
            if previous and (previous['group'] != cfg['group'] or previous['id'] != who):
                raise ValueError('Dynamic journal identity mismatch')
            home = initial(cfg)
            # Keep only the counters that fence old messages still in flight.
            # Room membership, admissions, cached routes and receipts are per launch.
            self.boot_generation = previous['home']['generation'] + 1 if previous else 0
            home['generation'] = self.boot_generation
            self.disk = dict(group=cfg['group'], id=who,
                             incarnation=previous['incarnation'] + 1 if previous else 1,
                             counter=previous['counter'] if previous else 0,
                             home=home, attachment=None, staged=None,
                             retired=[], closed={}, receipts={}, identities={})
            self.persist()
        except (OSError, ValueError, KeyError):
            self.server.server_close()
            raise
        self.refresh_peers()

    @property
    def state(self):
        attached = self.disk['attachment']
        return attached['state'] if attached else self.disk['home']

    def persist(self):
        try:
            atomic_json(self.path, self.disk)
            self.storage_error = None
        except OSError as error:
            self.storage_error = str(error)
            raise

    def refresh_peers(self):
        try:
            offers = json.loads(self.peers_file.read_text(encoding='utf-8'))
            if not isinstance(offers, list) or len(offers) > 17:
                return
            with self.lock:
                advertised = {p['id'] for p in offers if isinstance(p, dict) and isinstance(p.get('id'), str)}
                pinned = set(self.state['roster']) if self.state['owner'] else {self.id}
                if self.disk['staged']:
                    pinned.update(self.disk['staged']['state']['roster'])
                for who in set(self.peers) - advertised - pinned:
                    if time.monotonic()-self.signs.get(who, {}).get('at', float('-inf')) < 5:
                        continue
                    del self.peers[who], self.members[who]
                    self.signs.pop(who, None)
                for offer in offers:
                    try:
                        validate_offer(offer)
                    except (ValueError, KeyError, TypeError):
                        continue
                    who = offer['id']
                    if who == self.id:
                        continue
                    if who not in self.peers and len(self.peers) >= 17:
                        continue
                    old = self.peers.get(who)
                    # The private directory can move an address, but cannot
                    # replace an active identity, key, name or service ports.
                    if old and who in pinned and (old['host'] == offer['host'] or
                                                  old != dict(offer, host=old['host'])):
                        continue
                    rekey = old and old['seed'] != offer['seed']
                    # The local Player shortcuts write this directory from the
                    # profiles on this PC. A previous world may have cached an
                    # older key for the same local endpoint.
                    if rekey and (self.member['host'] != '127.0.0.1' or
                                  offer['host'] != '127.0.0.1' or member(old) != member(offer)):
                        continue
                    if any(p['name'].casefold() == offer['name'].casefold()
                           or (p['host'], p['port']) == (offer['host'], offer['port'])
                           for ident, p in self.peers.items() if ident != who):
                        continue
                    if rekey:
                        self.signs.pop(who, None)
                        self.bell_seen.pop(who, None)
                    self.peers[who] = copy.deepcopy(offer)
                    self.members[who] = member(offer)
                    if self.diagnostic and old and old['host'] != offer['host']:
                        self.diagnostic('peer_address_changed', peer=who, name=offer['name'], pinned=who in pinned)
        except (OSError, ValueError):
            pass

    def pair_key(self, who):
        identities = sorted([(self.id, self.identity['seed']), (who, self.peers[who]['seed'])])
        return hashlib.sha256(b'BBGL-dynamic-v1\0'+canonical(identities)).digest()

    def signed(self, who, body):
        message = dict(body, **{'from': self.id})
        message['mac'] = hmac.new(self.pair_key(who), canonical(message), hashlib.sha256).hexdigest()
        return message

    def verify(self, who, message):
        unsigned = {k: v for k, v in message.items() if k != 'mac'}
        expected = hmac.new(self.pair_key(who), canonical(unsigned), hashlib.sha256).hexdigest()
        if message.get('from') != who or not hmac.compare_digest(message.get('mac', ''), expected):
            raise ValueError('Wrong dynamic peer authentication')

    def rpc(self, who, body):
        with self.lock:
            if who in self.blocked:
                raise OSError('Isolated test peer')
            peer = copy.deepcopy(self.peers[who])
            nonce = secrets.token_hex(16)
            request = self.signed(who, dict(nonce=nonce, body=body))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.5)
            sock.bind((self.member['host'], 0))
            sock.connect((peer['host'], peer['port']))
            write_frame(sock, request)
            try:
                reply = read_frame(sock)
                with self.lock:
                    self.verify(who, reply)
                if reply.get('nonce') != nonce or type(reply.get('ok')) is not bool:
                    raise ValueError('Unexpected RPC reply')
                if ('result' if reply['ok'] else 'error') not in reply:
                    raise ValueError('Incomplete RPC reply')
            except (ValueError, AttributeError, TypeError) as error:
                # The peer may have committed. Only its authenticated rejection
                # for this nonce lets the owner roll back a staged reservation.
                raise OSError('Unconfirmed dynamic RPC reply') from error
        if reply['ok'] is False:
            raise ValueError(reply['error'])
        return reply['result']

    def world(self, expected=None):
        if self.storage_error or self.stop_event.is_set():
            raise OSError('World journal is not durable')
        state = self.disk['home']
        if expected is not None and expected != session(self.cfg, state):
            state = self.disk['closed'].get(canonical(expected).decode())
            if state is None:
                raise ValueError('Stale world session')
        ids = state['roster']
        return dict(session=session(self.cfg, state), state=copy.deepcopy(state),
                    peers=[copy.deepcopy(self.peers.get(p) or self.disk['identities'][p]) for p in ids])

    def dispatch(self, sender, body):
        if self.stop_event.is_set():
            raise OSError('World runtime is closing')
        kind = body['kind']
        if kind == 'presence':
            with self.lock:
                attached = self.disk['attachment']
                home = self.disk['home']
                eligible = home['owner'] is None and (not attached or attached['host'] == sender)
                host = self.host_presence()
                active = bool(host and host['generation'] == self.bell_ring_generation and
                              self.native_status.get('bell'))
                released = (not self.storage_error and self.bell_ring_seq > 0 and
                            (home['generation'] > self.bell_ring_generation or
                             (home['generation'] == self.bell_ring_generation and home['owner'] is None)))
                return dict(body=copy.deepcopy(self.local_status) if eligible else {'sign': None},
                            stamp=[self.disk['incarnation'], self.update_seq], host=host,
                            bell=[self.bell_ring_seq, active, released])
        if kind == 'reserve':
            return self.reserve(sender, body)
        if kind == 'view':
            with self.lock:
                return self.participant_view(sender,body['session'])
        if kind == 'command':
            with self.mutation:
                with self.lock:
                    if self.stop_event.is_set():
                        raise OSError('World runtime is closing')
                    if body['op']['kind'] in ('acquire', 'claim', 'membership'):
                        raise ValueError('Only the local world owner may reserve players')
                    home = self.disk['home']
                    if body['session'] != session(self.cfg, home):
                        raise ValueError('Stale world command')
                    if str(body['seq']) in home['results'].get(sender, {}):
                        return self.participant_view(sender,body['session'])
                    if 'admission' in body and body['admission'] != admission_ticket(home, sender):
                        raise ValueError('Stale guest command admission')
                    self.apply(sender, body['seq'], body['op'])
                    return self.world()
        if kind == 'relay':
            return self.receive_relay(sender, body)
        raise ValueError('Unknown dynamic RPC')

    def participant_view(self,sender,session_id):
        if (isinstance(session_id, list) and len(session_id) == 2 and
                session_id[0] == self.cfg['group'] and type(session_id[1]) is int and
                0 <= session_id[1] < self.boot_generation):
            return dict(session=session_id, ended_by_restart=True)
        world = self.world(session_id)
        state = world['state']
        if sender in state['roster']:
            return world
        receipts = state['results'].get(sender)
        if not receipts:
            raise ValueError('Not a world participant')
        # Another admission can remove a departed guest from the roster while
        # its leave response is in flight. Return only its own receipts and
        # proof of absence, never the new guests' identities or room contents.
        departed = initial(self.cfg)
        departed.update(revision=state['revision'],generation=state['generation'],
                        epoch=state['epoch'],roster=[],results={sender:receipts})
        return dict(session=world['session'],state=departed,peers=[])

    def world_offers(self, world, host):
        peers = world['peers']
        offered = {peer['id']: peer for peer in peers}
        if (len(offered) != len(peers) or set(offered) != set(world['state']['roster']) or
                offered.get(self.id) != self.identity or offered.get(host) != self.peers[host]):
            raise ValueError('World identities disagree')
        for peer in peers:
            validate_offer(peer)
        validate_invite(dict(version=1, secret='00'*32, members=[member(peer) for peer in peers]))
        return offered

    def reserve(self, sender, body):
        world = body['world']
        state = world['state']
        reservation = [*world['session'], body['seq']]
        with self.lock:
            if self.storage_error or self.stop_event.is_set():
                raise OSError('Guest journal is not durable')
            if body.get('target_incarnation', self.disk['incarnation']) != self.disk['incarnation']:
                raise ValueError('Invitation belongs to a previous guest launch')
            attached = self.disk['attachment']
            if attached:
                if attached['host'] == sender and attached['reservation'] == reservation:
                    return self.disk['incarnation']
                raise ValueError('Player already belongs to another world')
            if reservation in self.disk['retired']:
                raise ValueError('Admission already retired')
            if self.disk['home']['owner'] is not None or self.pending_local or not self.local_status.get('sign'):
                raise ValueError('Player is not searching as a guest')
            if state['owner'] != sender or self.id not in state['pending'] or len(state['roster']) > 5:
                raise ValueError('Invalid world reservation')
            offered = self.world_offers(world, sender)
            for who, peer in offered.items():
                self.peers[who] = copy.deepcopy(peer)
                self.members[who] = member(peer)
                if who != self.id:
                    self.disk['identities'][who] = copy.deepcopy(peer)
            self.disk['attachment'] = dict(host=sender, session=world['session'], reservation=reservation,
                                           state=copy.deepcopy(state), confirmed=False)
            self.persist()  # Native never sees a claim before the host confirms it.
            self.reset_relay()
            if self.diagnostic:
                self.diagnostic('admission_reserved', peer=sender, sequence=body['seq'],
                                ticket=admission_ticket(state, self.id), room_id=(state['room'] or {}).get('id'))
            return self.disk['incarnation']

    def apply(self, sender, seq, op):
        state = self.disk['home']
        if op['kind'] == 'room_create' and self.yielding_search == state['generation']:
            raise ValueError('Empty search is yielding to a network host')
        if self.disk['staged']:
            raise ValueError('Admission confirmation pending')
        if sender not in state['roster']:
            raise ValueError('Not a world participant')
        done = state['completed'].get(sender, [0, None])
        if seq <= done[0]:
            if str(seq) not in state['results'].get(sender, {}):
                raise ValueError('Expired request receipt')
            return
        next_state = transition(state, sender, seq, op)
        if op['kind'] == 'room_join':
            next_state['room']['members'][sender]['admission_ticket'] = state['pending'][sender].get('ticket', 0)
        if op['kind'] == 'room_create':
            # Native callbacks carry only room_id, not our owner/session tuple.
            # Different independent hosts must not produce the same native ID.
            room_id = secrets.randbits(63) or 1
            next_state['room']['id'] = room_id
            next_state['completed'][sender][1] = room_id
            next_state['results'][sender][str(seq)] = room_id
        self.disk['home'] = next_state
        if op['kind'] in ('admission_cancel', 'room_leave'):
            self.admitted_incarnations.pop(sender, None)
        if next_state['generation'] != state['generation']:
            self.admitted_incarnations.clear()
        if op['kind'] == 'release':
            self.disk['closed'][canonical(session(self.cfg, next_state)).decode()] = copy.deepcopy(next_state)
            while len(self.disk['closed']) > 32:
                del self.disk['closed'][next(iter(self.disk['closed']))]
        self.persist()
        if next_state['generation'] != state['generation']:
            # Receipts are scoped to the world generation. A new world must
            # start its outgoing stream at seq=1 too, even if native TCP stays up.
            self.reset_relay()

    def stage_claim(self, seq, op):
        with self.lock:
            if self.yielding_search == self.disk['home']['generation']:
                raise ValueError('Empty search is yielding to a network host')
            if self.disk['attachment']:
                raise ValueError('Guest cannot claim another player')
            if self.disk['staged']:
                return
            state = copy.deepcopy(self.disk['home'])
            if state['owner'] != self.id:
                raise ValueError('Only the local world owner may claim')
            target = op['target']
            if target not in self.peers or target == self.id:
                raise ValueError('Unknown claim target')
            # Idle/offline acquaintances never become voting members or consume slots.
            room = state['room'] or {}
            active = {self.id, target} | set(state['joined']) | set(state['pending']) | set(room.get('members', {})) | set(room.get('departing', {}))
            state['roster'] = sorted(active)
            if len(active) > 5:
                raise ValueError('World full')
            next_state = transition(state, self.id, seq, op)
            peers = [self.peers[p] for p in next_state['roster']]
            validate_invite(dict(version=1, secret='00'*32, members=[member(p) for p in peers]))
            self.disk['identities'].update({p['id']: copy.deepcopy(p) for p in peers if p['id'] != self.id})
            self.disk['staged'] = dict(seq=seq, target=target, state=next_state)
            seen = self.signs.get(target)
            if seen:
                self.disk['staged']['target_incarnation'] = seen['stamp'][0]
            self.persist()
            if self.diagnostic:
                self.diagnostic('admission_staged', peer=target, sequence=seq,
                                ticket=admission_ticket(next_state, target),
                                room_id=(next_state['room'] or {}).get('id'))

    def finish_claim(self):
        with self.lock:
            staged = copy.deepcopy(self.disk['staged'])
            if not staged:
                return
            world = dict(session=session(self.cfg, staged['state']), state=staged['state'],
                         peers=[copy.deepcopy(self.peers[p]) for p in staged['state']['roster']])
        request = dict(kind='reserve', seq=staged['seq'], world=world)
        if 'target_incarnation' in staged:
            request['target_incarnation'] = staged['target_incarnation']
        try:
            incarnation = self.rpc(staged['target'], request)
        except ValueError as error:
            # A signed rejection guarantees that this reservation was not accepted.
            with self.lock:
                self.disk['staged'] = None
                self.persist()
                if self.diagnostic:
                    self.diagnostic('admission_rejected', peer=staged['target'], sequence=staged['seq'],
                                    reason=str(error)[:160])
            raise
        with self.lock:
            self.disk['home'] = staged['state']
            self.disk['staged'] = None
            if type(incarnation) is int and incarnation > 0:
                self.admitted_incarnations[staged['target']] = incarnation
            self.reset_relay_peer(staged['target'])
            self.persist()
            if self.diagnostic:
                state = self.disk['home']
                self.diagnostic('admission_committed', peer=staged['target'], sequence=staged['seq'],
                                ticket=admission_ticket(state, staged['target']),
                                room_id=(state['room'] or {}).get('id'))

    def forget_restarted_guest(self, who, stamp):
        admitted = self.admitted_incarnations.get(who)
        if (admitted is None or not isinstance(stamp, list) or len(stamp) != 2 or
                type(stamp[0]) is not int or stamp[0] <= admitted or
                self.disk['staged'] or self.disk['home']['owner'] != self.id):
            return
        state = copy.deepcopy(self.disk['home'])
        state['pending'].pop(who, None)
        remove_room_guest(state, who)
        state['revision'] += 1
        self.disk['home'] = state
        self.admitted_incarnations.pop(who)
        self.reset_relay_peer(who)
        self.persist()
        if self.diagnostic:
            self.diagnostic('guest_restarted', peer=who, incarnation=stamp[0], room_id=(state['room'] or {}).get('id'))

    def accept_world(self, world):
        with self.lock:
            attached = self.disk['attachment']
            if not attached or world['session'] != attached['session']:
                raise ValueError('Unexpected world snapshot')
            if world.get('ended_by_restart') is True:
                self.retire_attachment(attached)
                if self.pending_local:
                    self.pending_local['error'] = 'Host restarted'
                self.reset_relay()
                self.persist()
                if self.diagnostic:
                    self.diagnostic('host_restarted', peer=attached['host'], previous_session=attached['session'],
                                    room_id=(attached['state']['room'] or {}).get('id'))
                return
            state = world['state']
            previous = attached['state']
            # During reserve, the host may still be persisting its commit.
            if state['revision'] < previous['revision']:
                return
            same_revision = state['revision'] == previous['revision']
            if same_revision and state != previous:
                raise ValueError('Conflicting world snapshot')
            peer_updates = set()
            if self.id in state['roster']:
                for peer in state['roster']:
                    ticket = admission_ticket(state, peer)
                    if (peer != self.id and ticket is not None and
                            (peer not in self.disk['identities'] or ticket != admission_ticket(previous, peer))):
                        peer_updates.add(peer)
            if same_revision and attached['confirmed'] and not peer_updates and not self.storage_error:
                return
            if peer_updates:
                offered = self.world_offers(world, attached['host'])
                # A guest already in the room may learn about a late guest
                # only from the host. Install the route with its admission.
                for peer in peer_updates:
                    offer = offered[peer]
                    self.peers[peer] = copy.deepcopy(offer)
                    self.members[peer] = member(offer)
                    self.disk['identities'][peer] = copy.deepcopy(offer)
            old_scope = (previous['owner'], previous['generation'])
            first_confirmation = not attached['confirmed']
            attached['state'] = copy.deepcopy(state)
            attached['confirmed'] = True
            pending = self.pending_local
            if pending and pending.get('destination') and pending['destination']['session'] == world['session']:
                receipts = state.get('results', {}).get(self.id, {})
                if str(pending['seq']) in receipts:
                    pending['result'] = receipts[str(pending['seq'])]
            room = state['room'] or {}
            if self.id not in state['pending'] and self.id not in state['joined'] and self.id not in room.get('members', {}) and self.id not in room.get('departing', {}):
                self.retire_attachment(attached)
            if not self.disk['attachment'] or old_scope != (state['owner'], state['generation']):
                self.reset_relay()
            else:
                for peer in state['roster']:
                    if peer != self.id and (peer in peer_updates or
                            admission_ticket(previous, peer) != admission_ticket(state, peer)):
                        self.reset_relay_peer(peer)
            self.persist()
            if self.diagnostic and first_confirmation:
                self.diagnostic('admission_confirmed', peer=attached['host'], sequence=attached['reservation'][-1],
                                ticket=admission_ticket(state, self.id), room_id=room.get('id'))

    def retire_attachment(self, attached):
        self.disk['retired'].append(attached['reservation'])
        self.disk['retired'] = self.disk['retired'][-64:]
        self.disk['attachment'] = None

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.scanner = threading.Thread(target=self.scan, daemon=True)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.thread.start()
        self.scanner.start()
        return self

    def close(self):
        self.stop_event.set()
        self.server.shutdown()
        for thread in (getattr(self, 'thread', None), getattr(self, 'scanner', None)):
            if thread:
                thread.join(8)
        for thread in self.relay_threads:
            thread.join(2)
        # Retain the exclusive endpoint until the old mutation workers are done.
        self.server.server_close()

    def finalized(self, state=None):
        with self.lock:
            attached = self.disk['attachment']
            return not self.storage_error and (not attached or attached['confirmed'])

    def confirmed_state(self, revision):
        with self.lock:
            if not self.finalized():
                return False, None
            return True, copy.deepcopy(self.state) if self.state['revision'] != revision else None

    def snapshot(self):
        with self.lock:
            return dict(id=self.id, state=copy.deepcopy(self.state), final=self.state['revision'] if self.finalized() else -1,
                        pending=copy.deepcopy(self.pending_local), relay_error=self.relay_error,
                        relay_peer_errors=dict(self.relay_peer_errors),
                        tx_phase='reserve' if self.disk['staged'] else None)

    def request(self, op):
        with self.lock:
            self.collect_finished_command()
            if self.pending_local:
                raise ValueError('One outstanding command per member')
            self.disk['counter'] += 1
            self.persist()
            self.pending_local = dict(seq=self.disk['counter'], op=copy.deepcopy(op),
                                      destination=copy.deepcopy(self.disk['attachment']))
            return self.disk['counter']

    def collect_finished_command(self):
        pending = self.pending_local
        if not pending or not self.finalized():
            return
        seq = pending['seq']
        receipts = self.state['results'].get(self.id, {})
        if str(seq) in receipts:
            pending['result'] = receipts[str(seq)]
        if 'result' in pending or 'error' in pending:
            # Waiters and maintenance poll independently. Keep the completed
            # result for its caller without blocking the next operation.
            self.finished_commands[seq] = (pending.get('error'), pending.get('result'))
            if len(self.finished_commands) > 32:
                del self.finished_commands[next(iter(self.finished_commands))]
            self.pending_local = None

    def poll(self, seq):
        with self.lock:
            if seq in self.finished_commands:
                error, result = self.finished_commands.pop(seq)
                if error is not None:
                    raise ValueError(error)
                return True, result
            pending = self.pending_local
            if pending and pending['seq'] == seq:
                if 'error' in pending:
                    self.pending_local = None
                    raise ValueError(pending['error'])
                if 'result' in pending and self.finalized():
                    self.pending_local = None
                    return True, pending['result']
            done = self.state.get('results', {}).get(self.id, {})
            if str(seq) in done and self.finalized():
                if self.pending_local and self.pending_local['seq'] == seq:
                    self.pending_local = None
                return True, done[str(seq)]
            return False, None

    def wait(self, seq, timeout=10):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            ready, result = self.poll(seq)
            if ready:
                return result
            time.sleep(.02)
        raise TimeoutError('Waiting for world owner confirmation')

    def command(self, op, timeout=10):
        return self.wait(self.request(op), timeout)

    def retire_native(self, reason, scope, witness=None):
        with self.mutation, self.lock:
            state = self.state
            if native_scope(state) != scope: raise ValueError('Stale native session')
            validate_retirement(dict(base=state, issuer=self.id, reason=reason, witness=witness))
            if reason == 'host_lost':
                attached = self.disk['attachment']
                if not attached:
                    raise ValueError('No attached host')
                # Retire this exact reservation locally even if its host crashed.
                # A late view/reserve cannot attach it again or affect a new world.
                self.retire_attachment(attached)
            else:
                staged = self.disk['staged']
                base = staged['state'] if staged else self.disk['home']
                closed = terminal(base)
                self.disk['home'] = closed
                self.disk['staged'] = None
                self.admitted_incarnations.clear()
                self.disk['closed'][canonical(session(self.cfg, closed)).decode()] = copy.deepcopy(closed)
                while len(self.disk['closed']) > 32:
                    del self.disk['closed'][next(iter(self.disk['closed']))]
            self.pending_local = None
            self.persist()
            self.reset_relay()

    def publish(self, body):
        with self.lock:
            if body != self.local_status:
                self.local_status = copy.deepcopy(body)
                self.update_seq += 1

    def observe_native(self, body):
        with self.lock:
            self.native_status = copy.deepcopy(body)
            self.native_at = time.monotonic()
            home = self.disk['home']
            seq = body.get('bell_ring_seq')
            if (home['owner'] == self.id and body.get('fresh') is True and
                    type(seq) is int and self.bell_ring_seq < seq < 1 << 63):
                self.bell_ring_seq = seq
                self.bell_ring_generation = home['generation']
            if body.get('bell'):
                self.host_intent_generation = None

    def observe_peer_bell(self, who, stamp, bell):
        if (not isinstance(stamp, list) or len(stamp) != 2 or type(stamp[0]) is not int or
                not isinstance(bell, list) or len(bell) != 3):
            return
        incarnation = stamp[0]
        seq, active, released = bell
        if type(seq) is not int or not 0 <= seq < 1 << 63 or type(active) is not bool or type(released) is not bool:
            return
        previous = self.bell_seen.get(who)
        if previous and (incarnation, seq) < previous[:2]:
            return
        attached = self.disk['attachment']
        eligible = attached['host'] == who if attached else self.disk['home']['owner'] is None
        if previous and incarnation == previous[0]:
            rings = seq - previous[1]
            notice = previous[2] if not rings else 0
        else:
            # A newly discovered host advertises its current bell, not its history.
            rings = 0
            notice = 0
        if not rings and not notice and seq > 0 and active:
            rings = 1
        if rings and eligible:
            self.bell_notices += rings
            notice = self.bell_notices
        if released and notice and notice == self.bell_notices:
            self.bell_released_notice = notice
        self.bell_seen[who] = (incarnation, seq, notice)

    def empty_search(self):
        # Call under lock. An admitted/constructing room must never yield to
        # discovery, including while its actors disappear during a load.
        s = self.disk['home']
        return (not self.disk['attachment'] and not self.disk['staged'] and
                s['owner'] == self.id and not s['room'] and not s['pending'] and not s['joined'])

    def host_presence(self):
        s, n = self.disk['home'], self.native_status
        if (self.storage_error or self.disk['attachment'] or s['owner'] != self.id or
                time.monotonic()-self.native_at >= 1.5 or n.get('fresh') is not True or
                n.get('await_title') or
                not (n.get('bell') or n.get('state') == 3 or not self.empty_search() or
                     self.host_intent_generation == s['generation'])):
            return None
        if s['room'] and s['room'].get('closing'):
            return None
        return dict(owner=self.id, generation=s['generation'], occupied=not self.empty_search())

    def preferred_host(self):
        """Fresh authenticated host; stable ID breaks only empty-search ties."""
        with self.lock:
            if self.disk['attachment'] or (self.state['owner'] == self.id and not self.empty_search()):
                return None
            candidates = []
            for who, entry in self.signs.items():
                host = entry.get('host')
                if (who == self.id or who not in self.peers or time.monotonic()-entry['at'] >= 2 or
                        not isinstance(host, dict) or host.get('owner') != who):
                    continue
                if self.state['owner'] == self.id and not host.get('occupied') and who > self.id:
                    continue
                candidates.append((not bool(host.get('occupied')), who))
            return min(candidates)[1] if candidates else None

    def run(self):
        while not self.stop_event.wait(.03):
            with self.lock:
                if self.storage_error:
                    try:
                        self.persist()
                    except OSError:
                        continue
                self.collect_finished_command()
                pending = copy.deepcopy(self.pending_local)
                staged = bool(self.disk['staged'])
            if not staged and (not pending or 'error' in pending or 'result' in pending):
                continue
            try:
                with self.mutation:
                    # Retirement may have cancelled the operation while this
                    # worker waited for the mutation lock.
                    with self.lock:
                        if pending and (not self.pending_local or self.pending_local['seq'] != pending['seq']):
                            continue
                    if staged:
                        self.finish_claim()
                    if not pending:
                        continue
                    with self.lock:
                        attached = copy.deepcopy(self.disk['attachment'])
                    destination = pending.get('destination')
                    if destination:
                        world = self.rpc(destination['host'], dict(kind='command', session=destination['session'],
                                                               admission=admission_ticket(destination['state'], self.id),
                                                               seq=pending['seq'], op=pending['op']))
                        result = world['state']['results'][self.id][str(pending['seq'])]
                        if attached:
                            self.accept_world(world)
                    else:
                        with self.lock:
                            done = self.disk['home']['results'].get(self.id, {})
                            completed = str(pending['seq']) in done
                        if not completed and pending['op']['kind'] == 'claim':
                            self.stage_claim(pending['seq'], pending['op'])
                            self.finish_claim()
                        elif not completed:
                            with self.lock:
                                self.apply(self.id, pending['seq'], pending['op'])
                        with self.lock:
                            result = self.disk['home']['results'][self.id][str(pending['seq'])]
                    with self.lock:
                        if self.pending_local and self.pending_local['seq'] == pending['seq']:
                            self.pending_local['result'] = result
            except (OSError, TimeoutError):
                pass  # Keep the same durable reservation/request, never release on timeout.
            except (ValueError, KeyError) as error:
                with self.lock:
                    if self.pending_local and pending and self.pending_local['seq'] == pending['seq']:
                        self.pending_local['error'] = str(error)

    def scan(self):
        workers = {}
        while not self.stop_event.is_set():
            self.refresh_peers()
            with self.lock:
                peers = set(self.peers) - {self.id}
            workers = {who: thread for who, thread in workers.items() if thread.is_alive()}
            for who in peers:
                if who in workers:
                    continue
                thread = threading.Thread(target=self.poll_peer, args=(who,), daemon=True)
                workers[who] = thread
                thread.start()
            self.stop_event.wait(.5)
        for thread in workers.values():
            thread.join()

    def poll_peer(self, who):
        view_error = presence_error = None
        while not self.stop_event.is_set():
            with self.lock:
                peer = self.peers.get(who)
                if peer is None:
                    return
                attached = self.disk['attachment']
                session_id = attached['session'] if attached and attached['host'] == who else None
            if session_id:
                try:
                    self.accept_world(self.rpc(who, dict(kind='view', session=session_id)))
                except (OSError, ValueError, KeyError) as error:
                    if self.diagnostic:
                        failure = (tuple(session_id), str(error)[:160])
                        if failure != view_error:
                            self.diagnostic('host_view_failed', peer=who, session=session_id, reason=failure[1])
                        view_error = failure
                else:
                    if view_error and self.diagnostic:
                        self.diagnostic('host_view_resumed', peer=who, session=session_id)
                    view_error = None
            else:
                view_error = None
            try:
                reply = self.rpc(who, dict(kind='presence'))
                with self.lock:
                    if peer == self.peers.get(who) and not self.stop_event.is_set():
                        self.forget_restarted_guest(who, reply['stamp'])
                        if (who in self.relay_peer_errors and who not in self.relay_reopening and
                                admission_ticket(self.state, who) is not None):
                            # Reopen once on authenticated contact. New traffic
                            # starts at sequence one; discarded frames stay retired.
                            self.reset_relay_peer(who)
                            self.relay_reopening.add(who)
                            if self.diagnostic:
                                self.diagnostic('relay_reopened', peer=who, stream=self.relay_stream(who),
                                                room_id=(self.state['room'] or {}).get('id'))
                        self.signs[who] = dict(body=reply['body'], stamp=reply['stamp'],
                                               host=reply.get('host'), at=time.monotonic())
                        self.observe_peer_bell(who, reply['stamp'], reply.get('bell'))
            except (OSError, ValueError, KeyError) as error:
                if self.diagnostic:
                    failure = str(error)[:160]
                    if failure != presence_error:
                        self.diagnostic('peer_presence_failed', peer=who, reason=failure)
                    presence_error = failure
            else:
                if presence_error is not None and self.diagnostic:
                    self.diagnostic('peer_presence_resumed', peer=who)
                presence_error = None
            self.stop_event.wait(.5)

    def reset_relay(self):
        with self.lock:
            self.relay_next_stream += 1
            self.relay_transport = self.relay_next_stream
            self.relay_peer_streams.clear()
            self.relay_error = None
            self.relay_peer_errors.clear()
            self.relay_network_errors.clear()
            self.relay_reopening.clear()
            self.relay_sequences.clear()
            self.relay_buffers.clear()
            self.relay_active.clear()

    def reset_relay_peer(self, who):
        # A new admission fences this peer's old queued/in-flight frames only.
        # Preserve the host role, native TCP and other guests' streams.
        with self.lock:
            self.relay_next_stream += 1
            self.relay_peer_streams[who] = self.relay_next_stream
            self.relay_sequences.pop(who, None)
            self.relay_peer_errors.pop(who, None)
            self.relay_network_errors.pop(who, None)
            self.relay_reopening.discard(who)

    def relay_stream(self, who):
        return self.relay_peer_streams.get(who, self.relay_transport)

    def current_session(self):
        attached = self.disk['attachment']
        return attached['session'] if attached else session(self.cfg, self.disk['home'])

    def relay_scope(self, sender, recipient):
        with self.lock:
            return [self.current_session(), admission_ticket(self.state, sender), admission_ticket(self.state, recipient)]

    def relay(self, raw, binding=None, recipients=None):
        if len(raw) > 65536:
            raise ValueError('Oversized BBSC frame')
        # Apply backpressure before consuming more native frames. A temporary
        # snapshot burst must not permanently fence a healthy recipient and
        # silently discard its later one-shot cutscene/ending requests.
        with self.relay_enqueue:
            with self.lock:
                targets = [who for who in (recipients if recipients is not None else self.state['roster'])
                           if who != self.id]
            accepted = True
            for who in targets:
                accepted = self.enqueue_relay(who, raw, binding) and accepted
            return accepted

    def enqueue_relay(self, who, raw, binding):
        with self.lock:
            if not self.state['owner'] or not self.finalized():
                return False
            if who == self.id or who not in self.state['roster'] or who in self.relay_peer_errors:
                return False
            if who not in self.relay_workers:
                work = queue.Queue(128)
                self.relay_workers[who] = work
                # Keep the previous protocol's 16-frame window; a long-distance
                # ACK must not serialize every multipart BBSC chunk.
                for _ in range(16):
                    thread = threading.Thread(target=self.send_relay, args=(who, work), daemon=True)
                    self.relay_threads.append(thread)
                    thread.start()
            sequence = self.relay_sequences.get(who, 0)+1
            self.relay_sequences[who] = sequence
            body = dict(kind='relay', session=self.current_session(), incarnation=self.disk['incarnation'],
                        stream=self.relay_stream(who), seq=sequence,
                        admission=self.relay_scope(self.id, who),
                        data=base64.b64encode(raw).decode(), binding=binding or {})
            work = self.relay_workers[who]
        # Workers need self.lock to drain/ACK; never wait for capacity under it.
        at = time.monotonic()
        while not self.stop_event.is_set():
            with self.lock:
                if body['session'] != self.current_session() or body['stream'] != self.relay_stream(who):
                    return False
                if who in self.relay_peer_errors:
                    return False
            try:
                work.put((at, body), timeout=.05)
                return True
            except queue.Full:
                with self.lock:
                    unreachable = who in self.relay_network_errors
                if unreachable:
                    self.fail_relay_peer(who, 'Peer relay backlog while unreachable', body['stream'])
                    return False
                if time.monotonic()-at >= 10:
                    self.fail_relay_peer(who, 'Peer relay backlog deadline', body['stream'])
                    return False
        return False

    def fail_relay_peer(self, who, message, stream=None, *, last_error=None):
        # A failed recipient cannot poison healthy streams or release membership.
        # Retain a fence until reset_relay starts a new stream; no silent seq gaps.
        with self.lock:
            if stream is not None and stream != self.relay_stream(who):
                return
            if self.diagnostic and who not in self.relay_peer_errors:
                self.diagnostic('relay_fenced', peer=who, stream=self.relay_stream(who),
                                room_id=(self.state['room'] or {}).get('id'), reason=message,
                                last_error=last_error)
            self.relay_peer_errors[who] = message
            work = self.relay_workers.get(who)
            if work:
                while True:
                    try: work.get_nowait()
                    except queue.Empty: break

    def send_relay(self, who, work):
        while not self.stop_event.is_set():
            try:
                at, body = work.get(timeout=.2)
            except queue.Empty:
                continue
            last_error = None
            while not self.stop_event.is_set():
                with self.lock:
                    if body['session'] != self.current_session() or body['stream'] != self.relay_stream(who):
                        break
                    if self.relay_error:
                        break
                    if who in self.relay_peer_errors:
                        break
                    if time.monotonic()-at > 10:
                        self.fail_relay_peer(who, 'Unacknowledged BBSC frame expired', body['stream'],
                                             last_error=last_error)
                        break
                try:
                    reply = self.rpc(who, body)
                    acknowledged = reply['ack'] >= body['seq']
                    with self.lock:
                        if body['stream'] == self.relay_stream(who):
                            self.relay_network_errors.pop(who, None)
                            if acknowledged:
                                if self.diagnostic and who in self.relay_reopening:
                                    self.diagnostic('relay_recovered', peer=who, stream=body['stream'],
                                                    room_id=(self.state['room'] or {}).get('id'))
                                self.relay_reopening.discard(who)
                    if acknowledged:
                        break
                    self.stop_event.wait(.05)
                except OSError as error:
                    if self.diagnostic: last_error = str(error)[:160]
                    with self.lock:
                        if body['stream'] == self.relay_stream(who):
                            self.relay_network_errors[who] = time.monotonic()
                    self.stop_event.wait(.1)
                except (ValueError, KeyError) as error:
                    if self.diagnostic: last_error = str(error)[:160]
                    self.stop_event.wait(.1)

    def receive_relay(self, sender, body):
        with self.lock:
            if self.stop_event.is_set():
                raise OSError('World runtime is closing')
            if body['session'] != self.current_session() or sender not in self.state['roster'] or not self.state['owner'] or not self.finalized():
                raise ValueError('Stale relay session')
            scope = self.relay_scope(sender, self.id)
            if 'admission' in body and body['admission'] != scope:
                raise ValueError('Stale relay admission')
            key = canonical([body['session'], sender]).decode()
            stamp = (int(body['incarnation']), int(body['stream']), int(body['seq']))
            previous = tuple(self.disk['receipts'].get(key, [0, -1, 0]))
            active = self.relay_active.get(key, previous[:2])
            if stamp[:2] < active:
                raise ValueError('Retired relay stream')
            if stamp <= previous:
                return {'ack': previous[2]}
            expected = previous[2]+1 if stamp[:2] == previous[:2] else 1
            if min(stamp) < 0 or not expected <= stamp[2] < expected+16:
                raise ValueError('Out of order relay frame')
            raw = base64.b64decode(body['data'], validate=True)
            if len(raw) > 65536:
                raise ValueError('Oversized BBSC frame')
            self.relay_active[key] = stamp[:2]
            stream_key = (key, stamp[:2])
            buffered = self.relay_buffers.setdefault(stream_key, {})
            # At most one 16-frame stream per sender; old streams cannot fill RAM.
            for old in list(self.relay_buffers):
                if old[0] == key and old[1] < stamp[:2]:
                    del self.relay_buffers[old]
            buffered.setdefault(stamp[2], (sender, raw, dict(body['binding'], admission=scope)))
            changed = False
            while expected in buffered:
                try:
                    self.relay_in.put_nowait(buffered[expected])
                except queue.Full:
                    break
                del buffered[expected]
                self.disk['receipts'][key] = [*stamp[:2], expected]
                expected += 1
                changed = True
            if changed:
                while len(self.disk['receipts']) > 256:
                    del self.disk['receipts'][next(iter(self.disk['receipts']))]
                self.persist()
            return {'ack': expected-1}
