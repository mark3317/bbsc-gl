import json,runpy,tempfile,unittest
from pathlib import Path
from engine import invite
resolve=runpy.run_path(str(Path(__file__).with_name('launch.py')))['resolve_invitation']
class InvitationStartupTests(unittest.TestCase):
 def test_missing_profile_uses_same_bundled_group(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp); profile=root/'profile'; port=root/'install'
   config=invite([dict(id='A',host='127.0.0.1',port=37600,p2p=37658)])
   bundled=port/'coop/party/invitation.json'; bundled.parent.mkdir(parents=True); bundled.write_text(json.dumps(config))
   target=resolve(profile,port,str(root/'missing.json'))
   self.assertEqual(target,profile/'party/invitation.json'); self.assertEqual(json.loads(target.read_text()),config)
 def test_existing_invite_is_not_overwritten(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp); saved=root/'existing.json'; saved.write_text('existing invitation preserved')
   self.assertEqual(resolve(root,root,str(saved)),saved); self.assertEqual(saved.read_text(),'existing invitation preserved')
 def test_no_invite_fails_without_creating_group(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   with self.assertRaises(FileNotFoundError): resolve(root,root,'')
   self.assertFalse((root/'party/invitation.json').exists())
if __name__=='__main__': unittest.main(verbosity=2)
