import json,os,runpy,struct,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from compat import account,game_user_id,game_user_map
from engine import invite
class IdentityTests(unittest.TestCase):
 def test_recorded_ids_no_longer_change_in_native_int32(self):
  for who,recorded in [('MarkPC',1554240143),('MarkLaptop',1768214827)]:
   self.assertGreater(account(who),0xffffffff)
   self.assertEqual(account(who)&0xffffffff,recorded)
   value=game_user_id(who)
   self.assertEqual(value,recorded)
   self.assertEqual(struct.unpack('<i',struct.pack('<i',value))[0],value)
 def test_collision_rejected_before_startup(self):
  with patch('compat.game_user_id',return_value=7):
   with self.assertRaisesRegex(ValueError,'collision'):game_user_map(['A','B'])
 def test_intro_patch_is_selected_without_changing_other_patches(self):
  launch=runpy.run_path(str(Path(__file__).with_name('launch.py')))
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);profile=root/'profile';profile.mkdir();cfg=root/'invitation.json'
   cfg.write_text(json.dumps(invite([dict(id='A',host='127.0.0.1',port=37600,p2p=37658)])))
   runtime=SimpleNamespace(app_settings=lambda _: {},game_environment=lambda _: {'BB_PATCHES':'Keep Existing'})
   env={'BBGL_PROFILE_DIR':str(profile),'BB_PARTY_CONFIG':str(cfg),'BB_PARTY_MEMBER':'A','BB_PARTY_GAME':'unused'}
   calls=[]
   with patch.dict(os.environ,env),patch.object(sys,'frozen',True,create=True),patch.object(sys,'executable',str(root/'Bloodborne.exe')),patch.object(sys,'argv',['launch.py']),patch('runpy.run_path',lambda *a,**kw:calls.append(a)):
    launch['main'](runtime)
    self.assertEqual(os.environ['BB_PATCHES'],'Keep Existing;Skip Intro')
    self.assertEqual(os.environ['BB_CONFIG'],str(profile/'bbport.ini'))
    self.assertEqual(len(calls),1)
if __name__=='__main__':unittest.main(verbosity=2)
