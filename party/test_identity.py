import struct,unittest
from unittest.mock import patch
from compat import account,game_user_id,game_user_map
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
if __name__=='__main__':unittest.main(verbosity=2)
