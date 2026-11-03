"""Real production Windows WinHTTP bridge against independent party clients, no game."""
import os,subprocess,tempfile,time,unittest,uuid
from pathlib import Path
from test_processes import Tests as ProcessTests
ROOT=Path(__file__).resolve().parents[2]
SOURCE=r'''
#include <windows.h>
#include <cstdio>
#include <string>
#include "bbsc_party.h"
namespace BbscMod { void LogLine(char,const char*,const std::string&){} }
int main(int argc,char** argv){
 if(argc>1 && std::string(argv[1])=="idle"){
  BbscMod::PartyObserve(3,false,true); BbscMod::PartyMaintain(); Sleep(300);
  BbscMod::PartyCancel(); BbscMod::PartyObserve(0,false,false); BbscMod::PartyMaintain(); return 0;
 }
 if(argc>1 && std::string(argv[1])=="title"){
  BbscMod::PartyCancel(); BbscMod::PartyObserve(0,false,false); BbscMod::PartyMaintain();
  if(BbscMod::PartyTitleReady()) return 8;
  std::puts("waiting");std::fflush(stdout);
  const auto end=GetTickCount64()+15000;
  while(GetTickCount64()<end){
   Sleep(50);BbscMod::PartyMaintain();
   if(BbscMod::PartyTitleReady()){
    BbscMod::PartyCancel();
    if(BbscMod::PartyTitleReady())return 9;
    std::puts("confirmed-and-old-ack-invalidated");return 0;
   }
  }
  return 10;
 }
 if(argc>1 && std::string(argv[1])=="hold"){
  BbscMod::PartyMaintain(); std::puts("ready"); std::fflush(stdout); Sleep(10000); return 0;
 }
 std::puts(BbscMod::PartyAcquire()?"granted":"denied");
}
'''
class BridgeTests(ProcessTests):
 def test_native_title_waits_for_unanimous_leave(self):
  a,b=self.group(2,compat=True)
  self.assertNotIn('error',a.op('acquire'))
  rid=a.op('room_create',room={'max_slots':5,'world':1,'bins':[],'flags':0,'member_bins':[]})['result']
  a.op('claim',target='B',claim={});b.op('room_join',room_id=rid)
  cpp=self.root/'title.cpp';exe=self.root/'title.exe';cpp.write_text(SOURCE)
  subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-DFMT_HEADER_ONLY',
    '-I',str(ROOT/'emulator/mod'),'-I',str(ROOT/'emulator/mod/shim'),'-I',str(ROOT/'emulator/externals/fmt/include'),
    str(cpp),str(ROOT/'emulator/mod/bbsc_party.cpp'),'-lwinhttp','-o',str(exe)],check=True)
  env=dict(os.environ);env.update(BBSC_PARTY='1',BBSC_PARTY_PORT=str(b.info['http']),BBSC_PARTY_TOKEN=b.info['token'],BBSC_PARTY_INSTANCE='title-'+uuid.uuid4().hex)
  proc=subprocess.Popen([str(exe),'title'],env=env,stdout=subprocess.PIPE,text=True)
  try:
   self.assertEqual(proc.stdout.readline().strip(),'waiting')
   b.call('block',peers=['A'])
   ticket=b.send('command',op={'kind':'room_leave'})
   time.sleep(.7);self.assertIsNone(proc.poll())
   self.assertIn('B',a.state()['state']['joined'])
   b.call('block',peers=[]);self.assertNotIn('error',b.get(ticket))
   out,_=proc.communicate(timeout=6)
   self.assertEqual(proc.returncode,0);self.assertIn('confirmed-and-old-ack-invalidated',out)
  finally:
   if proc.poll() is None:proc.kill();proc.wait()
   proc.stdout.close()
 def test_actual_winhttp_and_native_process_fence(self):
  a,b=self.group(2,compat=True)
  cpp=self.root/'bridge.cpp'; exe=self.root/'bridge.exe'; cpp.write_text(SOURCE)
  compiler='C:/msys64/clang64/bin/clang++.exe'
  subprocess.run([compiler,'-std=c++20','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-DFMT_HEADER_ONLY',
    '-I',str(ROOT/'emulator/mod'),'-I',str(ROOT/'emulator/mod/shim'),'-I',str(ROOT/'emulator/externals/fmt/include'),
    str(cpp),str(ROOT/'emulator/mod/bbsc_party.cpp'),'-lwinhttp','-o',str(exe)],check=True)
  def env(c):
   e=dict(os.environ); e.update(BBSC_PARTY='1',BBSC_PARTY_PORT=str(c.info['http']),BBSC_PARTY_TOKEN=c.info['token'],BBSC_PARTY_INSTANCE='fixture-'+uuid.uuid4().hex); return e
  ea,eb=env(a),env(b)
  self.assertEqual(subprocess.check_output([str(exe)],env=ea,text=True).strip(),'granted')
  self.assertEqual(subprocess.check_output([str(exe)],env=eb,text=True).strip(),'denied')
  holder=subprocess.Popen([str(exe),'hold'],env=ea,stdout=subprocess.PIPE,text=True)
  try:
   self.assertEqual(holder.stdout.readline().strip(),'ready')
   self.assertEqual(subprocess.check_output([str(exe)],env=ea,text=True).strip(),'denied')
  finally: holder.kill(); holder.wait(); holder.stdout.close()
  subprocess.run([str(exe),'idle'],env=ea,check=True)
  end=time.monotonic()+5
  while a.state()['state']['owner'] is not None and time.monotonic()<end: time.sleep(.05)
  self.assertIsNone(a.state()['state']['owner'])
if __name__=='__main__':
 suite=unittest.TestSuite([BridgeTests('test_actual_winhttp_and_native_process_fence')])
 raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
