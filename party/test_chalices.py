"""Native channel responses, durability and isolated HTTP integration; no game/save use."""
import base64
from concurrent.futures import ThreadPoolExecutor
import copy
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from chalices import Channels, FIXED_CHALICES
from compat import Compatibility, game_user_id, start_from_environment
from engine import invite
from test_dynamic import DynamicHelpers


def root_form(variant=0):
    # Different decoded layouts sharing the same virtual stage map. Original
    # layout bytes are opaque to Party, including rites and additional parts.
    raw = bytearray(base64.b64decode(FIXED_CHALICES[-1][3]))
    raw[20:24] = (9910000+variant*10000).to_bytes(4, 'little')
    raw[-4:] = variant.to_bytes(4, 'little')
    return dict(FormDataVersion=0, FormData=base64.b64encode(raw).decode(),
                FixedOrGeneral=1, HolyGrailTypeId=3, RitualLevel=5,
                SubFeatureFlag=7, WishMaterialList=[dict(MaterialId=1, MaterialCount=2)],
                UnlockFlagList=[0, 0x80000000, 0], CharaId=2, ShareLevel=0)


class ChannelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'profile/coop/party/chalices.json'
        self.channels = Channels(self.path)

    def call(self, name, body=None, user=123):
        return self.channels.call('/channel/'+name, body or {}, user)

    def test_native_root_search_upload_reopen_and_restart(self):
        request = dict(FixedOrGeneralList=[dict(FixedOrGeneral=1)], GetCount=1,
                       HolyGrailTypeId=3, RitualLevel=5, SubFeatureFlag=7)
        self.assertEqual(self.call('search', request)['ChannelList'], [])
        self.assertFalse(self.path.exists())
        body = root_form(1)
        original = copy.deepcopy(body)
        result = self.call('upload', body)
        self.assertEqual(body, original)
        self.assertEqual(result['MessageId'], 'ChannelUploadResponse')
        channel_id = result['ChannelId']
        self.assertGreater(channel_id, 0)
        self.assertEqual(int(float(channel_id)), channel_id)
        self.assertEqual(len(result['DiscernmentWord']), 8)
        self.channels = Channels(self.path)
        info = self.call('get_info', dict(ChannelIdList=[dict(ChannelId=channel_id)]))
        entry = info['ChannelInfoList'][0]
        for key in original:
            if key != 'CharaId':
                self.assertEqual(entry[key], original[key])
        self.assertEqual(entry['CreateCharaId'], 2)
        self.assertEqual(entry['CreateUserId'], 123)
        self.assertNotIn('_fixed', entry)
        self.assertEqual(self.call('get_details_info', dict(ChannelIdList=[channel_id]))['ChannelList'], [entry])
        self.assertEqual(self.call('word_search', dict(SearchWord=result['DiscernmentWord'].upper()))['ChannelList'], [entry])
        self.assertEqual(self.call('upload', dict(body, ChannelId=channel_id))['ChannelId'], channel_id)
        self.assertEqual(self.call('search', request)['ChannelList'], [])

    def test_new_ritual_and_changed_layout_do_not_share_identity(self):
        body = root_form(1)
        first = self.call('upload', body)
        same_layout_new_ritual = self.call('upload', body)
        changed = self.call('upload', dict(root_form(2), ChannelId=first['ChannelId']))
        self.assertEqual(len({r['ChannelId'] for r in (first, same_layout_new_ritual, changed)}), 3)
        entries = self.call('get_details_info', dict(ChannelIdList=[first['ChannelId'], changed['ChannelId']]))['ChannelList']
        self.assertNotEqual(entries[0]['FormData'], entries[1]['FormData'])
        self.assertEqual(entries[0]['FormData'], body['FormData'])

    def test_fixed_story_search_is_separate_and_stable(self):
        for grail, level, bit, form in FIXED_CHALICES:
            body = dict(FixedOrGeneralList=[dict(FixedOrGeneral=2)], HolyGrailTypeId=grail,
                        RitualLevel=level, SubFeatureFlag=256, GetCount=1)
            first = self.call('search', body)['ChannelList']
            self.assertEqual(len(first), 1)
            self.assertEqual(first[0]['FormData'], form)
            self.assertEqual(first[0]['UnlockFlagList'], [0, bit, 0])
            self.channels = Channels(self.path)
            self.assertEqual(self.call('search', body)['ChannelList'], first)
            self.assertNotIn('ChannelId', self.call('share', dict(ChannelId=first[0]['ChannelId'], ShareLevel=0), user=0))
        self.assertEqual(len(self.channels.load()), 10)

    def test_unknown_saved_channel_is_never_lost_or_replaced(self):
        for name, key in [('get_info', 'ChannelInfoList'), ('get_details_info', 'ChannelList')]:
            result = self.call(name, dict(ChannelIdList=[999, 0, -(1 << 63), 1 << 63, (1 << 64)-1]))
            self.assertEqual(result[key], [])
            self.assertEqual(result['LostChannelIdList'], [])
            self.assertEqual(self.call(name, dict(ChannelIdList=None))[key], [])
        self.assertEqual(self.call('word_search', dict(SearchWord='unknown'))['ChannelList'], [])
        self.assertFalse(self.path.exists())

    def test_native_unsigned_unassigned_id_uploads_as_a_new_ritual(self):
        result = self.call('upload', dict(root_form(3), ChannelId=1 << 63))
        self.assertGreater(result['ChannelId'], 0)
        self.assertLess(result['ChannelId'], 1 << 52)
        self.assertNotIn('ChannelId', self.call('share', dict(ChannelId=1 << 63, ShareLevel=2)))

    def test_owner_checks_and_invalid_forms_leave_catalogue_unchanged(self):
        first = self.call('upload', root_form(1))
        before = self.path.read_bytes()
        invalid = [dict(root_form(), FormData='?'), dict(root_form(), FormData='AAAA'),
                   dict(root_form(), FormData=base64.b64encode(bytes(1025)).decode()),
                   dict(root_form(), FormDataVersion=1), dict(root_form(), UserId=456)]
        for body in invalid:
            with self.assertRaises(ValueError):
                self.call('upload', body)
        self.assertNotIn('ChannelId', self.call('share', dict(ChannelId=first['ChannelId'], ShareLevel=2), user=456))
        self.assertEqual(before, self.path.read_bytes())
        self.call('share', dict(ChannelId=first['ChannelId'], ShareLevel=2))
        self.assertEqual(self.call('get_info', dict(ChannelId=first['ChannelId']))['ChannelInfoList'][0]['ShareLevel'], 2)

    def test_failed_write_never_acknowledges_and_preserves_previous_catalogue(self):
        self.call('upload', root_form(1))
        before = self.path.read_bytes()
        with patch('chalices.os.replace', side_effect=OSError('simulated write failure')):
            with self.assertRaises(OSError):
                self.call('upload', root_form(2))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])
        self.path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.call('upload', root_form(3))
        self.assertEqual(self.path.read_text(), '{broken')

    def test_concurrent_catalogue_instances_do_not_drop_rituals(self):
        def upload(i):
            return Channels(self.path).call('/channel/upload', root_form(i), 123)['ChannelId']
        with ThreadPoolExecutor(max_workers=5) as pool:
            ids = list(pool.map(upload, range(10)))
        self.assertEqual(len(set(ids)), 10)
        self.assertEqual(len(self.channels.load()), 10)

    def test_two_processes_share_one_profile_without_lost_uploads(self):
        script = ('from chalices import Channels; from test_chalices import root_form; '
                  'import sys; c=Channels(sys.argv[1]); '
                  '[c.call("/channel/upload",root_form(n),123) for n in range(8)]')
        workers = [subprocess.Popen([sys.executable, '-B', '-c', script, str(self.path)],
                                    cwd=Path(__file__).parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                   for _ in range(2)]
        try:
            for worker in workers:
                stdout, stderr = worker.communicate(timeout=15)
                self.assertEqual(worker.returncode, 0, stderr.decode(errors='replace'))
        finally:
            for worker in workers:
                if worker.poll() is None:
                    worker.kill()
                worker.communicate()
        self.assertEqual(len(self.channels.load()), 16)


class ChannelHTTPTests(DynamicHelpers, unittest.TestCase):
    def request(self, bridge, path, body):
        request = urllib.request.Request(f'http://127.0.0.1:{bridge.http_port}/channel/{path}',
                                         json.dumps(body).encode(), {'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.load(response)

    def test_live_dynamic_host_can_create_before_and_after_late_admission(self):
        a, b = self.node('A'), self.node('B')
        self.discover()
        bridges = [Compatibility(e).start() for e in (a, b)]
        self.addCleanup(lambda: [bridge.close() for bridge in bridges])
        host, guest = bridges
        first = self.request(host, 'upload', dict(root_form(1), UserId=game_user_id('A')))
        room = self.host(a)
        self.claim(a, b)
        b.command(dict(kind='room_join', room_id=room))
        self.eventually(lambda: b.id in a.state['joined'])
        before = copy.deepcopy(a.state)
        second = self.request(host, 'upload', root_form(2))
        self.assertNotEqual(first['ChannelId'], second['ChannelId'])
        self.assertEqual(a.state, before)
        self.assertEqual(self.request(guest, 'get_info', dict(ChannelIdList=[first['ChannelId']]))['LostChannelIdList'], [])
        self.assertFalse(guest.channels.path.exists())  # borrowing never creates an altar/catalogue
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request(guest, 'upload', dict(root_form(), UserId=game_user_id('A')))
        self.assertEqual(error.exception.code, 409)
        error.exception.close()

    def test_launcher_catalogue_survives_new_party_group(self):
        profile = self.root/'profile'
        profile.mkdir()
        uploaded = None
        for index in range(2):
            cfg = invite([dict(id='A', host='127.0.0.121', port=37800, p2p=37858)])
            config = self.root/f'config{index}.json'
            config.write_text(json.dumps(cfg), encoding='utf-8')
            env = dict(BB_PARTY_CONFIG=str(config), BB_PARTY_MEMBER='A', BBGL_PROFILE_DIR=str(profile))
            bridge = start_from_environment(env, self.root/'port')
            try:
                self.assertEqual(bridge.channels.path, profile/'coop/party/chalices.json')
                if uploaded is None:
                    uploaded = self.request(bridge, 'upload', root_form(7))
                else:
                    found = self.request(bridge, 'get_details_info', dict(ChannelIdList=[uploaded['ChannelId']]))['ChannelList']
                    self.assertEqual(found[0]['FormData'], root_form(7)['FormData'])
                    self.assertEqual(found[0]['DiscernmentWord'], uploaded['DiscernmentWord'])
            finally:
                bridge.close()


if __name__ == '__main__':
    unittest.main()
