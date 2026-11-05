"""Local native channel API. The game creates FormData; Party never generates layouts.

Fixed story descriptions below originate in NoDreamForTheHunterBB by Fahad
(GPL-3.0), as credited in server/gameserver/bbsc_gameserver.py. Root rituals
must not receive a story layout or another player's search result.
"""
from __future__ import annotations

import base64
import copy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
import time


FIXED_CHALICES = [
    # (HolyGrailTypeId, RitualLevel, unlock bit, FormData)
    (0, 1, 1, "BQAAAIwAAAAAWgod3RcAAP////////////////////8+pk47WgAAAP////////////////////+g3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAtAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="),
    (0, 2, 128, "BQAAAIwAAAAAWhQdQRgAAP////////////////////8+pk47WgAAAEimTjtbAAAA//////////+g3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="),
    (0, 3, 16384, "BQAAAIwAAAAAWh4dpRgAAKBHXzs9AAAAoOaDO1UAAAA+pk47WgAAAEimTjtbAAAA//////////+g3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="),
    (0, 4, 2097152, "BQAAAIwAAAAAWigdCRkAAEDOYDs+AAAAQANtO0YAAAA+pk47WgAAAEimTjtbAAAAXKZOO10AAACg3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="),
    (0, 5, 268435456, "BQAAAIwAAAAAWjIdbRkAAEDOYDs+AAAA4POGO1cAAAA+pk47WgAAAEimTjtbAAAAXKZOO10AAACg3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAtAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="),
    (1, 2, 256, "BQAAAIwAAAAAWhUdSxgAAP////////////////////+spk47XgAAAMB1ETsKAAAA//////////+g3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="),
    (1, 3, 32768, "BQAAAIwAAAAAWh8drxgAAP//////////QG2FO1YAAACspk47XgAAALamTjtfAAAAwHUROwoAAACg3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="),
    (2, 4, 8388608, "BQAAAIwAAAAAWiodHRkAAP////////////////////8kp047YAAAAP////////////////////+g3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="),
    (2, 5, 1073741824, "BQAAAIwAAAAAWjQdgRkAAP//////////gHqIO1gAAAAkp047YAAAAC6nTjthAAAA//////////+g3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="),
    (3, 5, 2147483648, "BQAAAIwAAAAAWjUdixkAAD6mTjtaAAAAIAGKO1kAAACSp047YgAAAEimTjtbAAAArKZOO14AAACg3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="),
]
GLYPH_LETTERS = 'abcdefghijkmnpqrstuvwxyz23456789'
ENTRY_FIELDS = ('FormDataVersion', 'FormData', 'ShareLevel', 'Status', 'RitualLevel',
                'HolyGrailTypeId', 'FixedOrGeneral', 'SubFeatureFlag', 'TurnoutLevel',
                'WishMaterialList', 'UnlockFlagList')
_locks = {}
_locks_guard = threading.Lock()


def integer(value, *, minimum=0, maximum=(1 << 63)-1):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError('Invalid channel integer')
    number = int(value)
    if not minimum <= number <= maximum:
        raise ValueError('Channel integer out of range')
    return number


def form_bytes(body):
    if integer(body.get('FormDataVersion', 0)) != 0:
        raise ValueError('Unsupported FormDataVersion')
    value = body.get('FormData')
    if not isinstance(value, str) or len(value) > 1368:
        raise ValueError('Invalid FormData')
    try:
        raw = base64.b64decode(value, validate=True)
    except ValueError as ex:
        raise ValueError('Invalid FormData encoding') from ex
    if not 16 <= len(raw) <= 1024:
        raise ValueError('Invalid FormData size')
    return raw


def reply(name, **fields):
    return {**dict(ResKind=0, MessageId=name, ChannelList=[], ChannelInfoList=[],
                   LostChannelIdList=[]), **fields}


def date(now):
    return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(now))


class Channels:
    """A profile catalogue, independent of the current world/party journal.

    Load/mutate under a path lock and atomically replace a uniquely named file.
    Failed persistence never acknowledges an upload. Unknown saved IDs are never
    declared lost; a missing catalogue cannot delete a character's existing altar.
    """
    def __init__(self, path):
        self.path = Path(path)
        with _locks_guard:
            key = os.path.normcase(os.path.abspath(self.path))
            # resolve() can transiently return a \\?\ prefix while another
            # request creates the missing parents on Windows.
            if key.startswith('\\\\?\\'):
                key = key[4:]
            self.lock = _locks.setdefault(key, threading.RLock())

    @contextmanager
    def transaction(self):
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Separate from the replaced JSON inode. Two processes temporarily
            # using one profile must not overwrite each other's successful ritual.
            with self.path.with_suffix('.lock').open('a+b') as stream:
                if stream.seek(0, os.SEEK_END) == 0:
                    stream.write(b'\0')
                    stream.flush()
                if os.name == 'nt':
                    import msvcrt
                    def take():
                        stream.seek(0)
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    def release():
                        stream.seek(0)
                        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    def take():
                        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    def release():
                        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
                deadline = time.monotonic()+3
                while True:
                    try:
                        take()
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            raise TimeoutError('Chalice catalogue is busy')
                        time.sleep(.02)
                    except OSError:
                        if os.name != 'nt' or time.monotonic() >= deadline:
                            raise
                        time.sleep(.02)
                try:
                    yield
                finally:
                    release()

    def load(self):
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('channels'), dict):
            raise ValueError('Unsupported chalice catalogue')
        channels = data['channels']
        glyphs = set()
        for key, entry in channels.items():
            if not isinstance(entry, dict) or str(integer(entry.get('ChannelId'), minimum=1)) != key:
                raise ValueError('Invalid stored channel')
            form_bytes(entry)
            glyph = entry.get('DiscernmentWord')
            if not isinstance(glyph, str) or len(glyph) != 8 or any(c not in GLYPH_LETTERS for c in glyph) or glyph in glyphs:
                raise ValueError('Invalid stored glyph')
            glyphs.add(glyph)
        return channels

    def save(self, channels):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix=self.path.name+'.', suffix='.tmp', delete=False) as stream:
                temp = Path(stream.name)
                json.dump(dict(version=1, channels=channels), stream, separators=(',', ':'))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.path)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)

    def create(self, channels, body, user, character, *, fixed=False):
        raw = form_bytes(body)
        fields = {key: copy.deepcopy(body[key]) for key in ENTRY_FIELDS if key in body}
        fields['FormDataVersion'] = 0
        fields.setdefault('ShareLevel', 0)
        fields.setdefault('Status', 1)
        fields.setdefault('RitualLevel', 1)
        fields.setdefault('HolyGrailTypeId', 0)
        fields.setdefault('FixedOrGeneral', 0)
        fields.setdefault('SubFeatureFlag', 0)
        fields.setdefault('TurnoutLevel', 0)
        fields.setdefault('WishMaterialList', [])
        fields.setdefault('UnlockFlagList', [])
        for key in ('ShareLevel', 'Status', 'RitualLevel', 'HolyGrailTypeId', 'FixedOrGeneral', 'SubFeatureFlag', 'TurnoutLevel'):
            fields[key] = integer(fields[key], maximum=0xffffffff)
        if not all(isinstance(fields[k], list) for k in ('WishMaterialList', 'UnlockFlagList')):
            raise ValueError('Invalid channel list')
        if len(json.dumps(fields)) > 16384:
            raise ValueError('Channel description too large')
        # Only an acknowledged existing ID may update a ritual. Identical new
        # FormData must not collapse separate rituals into one progress/loot scope.
        requested = body.get('ChannelId', 0)
        requested = integer(requested, minimum=-(1 << 63), maximum=(1 << 64)-1) if requested is not None else 0
        old = channels.get(str(requested))
        if old is not None and old['CreateUserId'] == user and old['CreateCharaId'] == character and not old.get('_fixed') and form_bytes(old) == raw:
            entry = dict(old, **fields)
            entry['LastPlayDate'] = date(time.time())
        else:
            # The native JSON DOM has a floating-point number representation.
            # Stay exactly representable there and valid in signed 64-bit saves.
            channel_id = secrets.randbelow((1 << 52)-1)+1
            while str(channel_id) in channels:
                channel_id = secrets.randbelow((1 << 52)-1)+1
            taken = {c['DiscernmentWord'] for c in channels.values()}
            glyph = ''.join(secrets.choice(GLYPH_LETTERS) for _ in range(8))
            while glyph in taken:
                glyph = ''.join(secrets.choice(GLYPH_LETTERS) for _ in range(8))
            now = date(time.time())
            entry = dict(fields, ChannelId=channel_id, DiscernmentWord=glyph,
                         CreateUserId=user, CreateCharaId=character, CreateDate=now,
                         LastPlayDate=now, _fixed=fixed)
        channels[str(entry['ChannelId'])] = entry
        return entry

    @staticmethod
    def public(entry):
        return {k: copy.deepcopy(v) for k, v in entry.items() if not k.startswith('_')}

    def call(self, path, body, user):
        if not isinstance(body, dict):
            raise ValueError('Invalid channel request')
        if 'UserId' in body and integer(body['UserId']) != user:
            raise ValueError('Channel UserId does not belong to this member')
        name = path.rsplit('/', 1)[-1]
        with self.transaction():
            channels = self.load()
            if name == 'upload':
                entry = self.create(channels, body, user, integer(body.get('CharaId', 0)))
                self.save(channels)
                return reply('ChannelUploadResponse', ChannelId=entry['ChannelId'], DiscernmentWord=entry['DiscernmentWord'])
            if name == 'share':
                entry = channels.get(str(integer(body.get('ChannelId') or 0, minimum=-(1 << 63), maximum=(1 << 64)-1)))
                if entry is None or entry['CreateUserId'] != user or entry.get('_fixed'):
                    return reply('ChannelShareResponse')
                entry['ShareLevel'] = integer(body.get('ShareLevel', entry['ShareLevel']), maximum=2)
                self.save(channels)
                return reply('ChannelShareResponse', ChannelId=entry['ChannelId'], DiscernmentWord=entry['DiscernmentWord'])
            if name in ('get_info', 'get_details_info'):
                ids = body.get('ChannelIdList') or []
                if not isinstance(ids, list) or len(ids) > 256:
                    raise ValueError('Invalid ChannelIdList')
                if not ids and body.get('ChannelId') is not None:
                    ids = [body['ChannelId']]
                found = []
                for value in ids:
                    channel_id = integer(value.get('ChannelId') if isinstance(value, dict) else value,
                                         minimum=-(1 << 63), maximum=(1 << 64)-1)
                    entry = channels.get(str(channel_id))
                    if entry is not None:
                        found.append(self.public(entry))
                return reply('ChannelGetInfoResponse' if name == 'get_info' else 'ChannelGetDetailsInfoResponse',
                             **{'ChannelInfoList' if name == 'get_info' else 'ChannelList': found})
            if name == 'word_search':
                word = body.get('SearchWord') or body.get('DiscernmentWord') or ''
                if not isinstance(word, str):
                    raise ValueError('Invalid glyph')
                found = [self.public(c) for c in channels.values() if c['DiscernmentWord'] == word.strip().lower()]
                # Both native response shapes used by the existing channel API.
                return reply('ChannelWordSearchResponse', **dict(found[0] if found else {}, ChannelList=found))
            if name == 'search':
                kinds = body.get('FixedOrGeneralList') or []
                if not isinstance(kinds, list):
                    raise ValueError('Invalid FixedOrGeneralList')
                kinds = {integer(k.get('FixedOrGeneral')) for k in kinds if isinstance(k, dict)}
                # An empty root search lets the native ritual choose/create its
                # own FormData. Never substitute a previous/uploaded root layout.
                found, changed = [], False
                if 2 in kinds:
                    wanted = {k: integer(body[k], maximum=0xffffffff) for k in
                              ('HolyGrailTypeId', 'RitualLevel', 'SubFeatureFlag', 'Status') if body.get(k) is not None}
                    limit = integer(body.get('GetCount') or 1, minimum=1, maximum=256)
                    for grail, level, bit, form in FIXED_CHALICES:
                        values = dict(HolyGrailTypeId=grail, RitualLevel=level, SubFeatureFlag=256, Status=1)
                        if any(values[k] != v for k, v in wanted.items()):
                            continue
                        token = hashlib.sha256(form.encode()).hexdigest()
                        entry = next((c for c in channels.values() if c.get('_fixed') == token), None)
                        if entry is None:
                            entry = self.create(channels, dict(values, FormData=form, FormDataVersion=0,
                                                FixedOrGeneral=2, ShareLevel=2, UnlockFlagList=[0, bit, 0]), 0, 0, fixed=token)
                            changed = True
                        found.append(self.public(entry))
                        if len(found) >= limit:
                            break
                if changed:
                    self.save(channels)
                return reply('ChannelSearchResponse', ChannelList=found)
            messages = {'random_join': 'ChannelRandomJoinResponse', 'add_material': 'ChannelAddMaterialResponse',
                        'notify_add_material_complete': 'ChannelAddMaterialCompleteNotifyResponse'}
            if name in messages:
                return reply(messages[name])
            raise ValueError('Unsupported channel API')
