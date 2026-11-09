"""Real production Windows WinHTTP bridge against independent party clients, no game."""
import os,subprocess,tempfile,time,unittest,uuid,threading,json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from test_processes import Tests as ProcessTests
ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
#include <windows.h>
#include <cstdio>
#include <string>
#include <future>
#include "bbsc_party.h"
namespace BbscMod {
void LogLine(char,const char*,const std::string&){}
std::string AimedPlacementAcknowledgment(){return {};}
}
int main(int argc,char** argv){
 if(argc>1 && std::string(argv[1])=="roles"){
  for(unsigned expected:{1u,2u,0u,0u}){
   if(expected==2) BbscMod::PartyBellRang();
   BbscMod::PartyObserve(0,false,false,1,true,true);
   BbscMod::PartyMaintain();
   if(BbscMod::PartyHostHint()!=expected)return 40;
   Sleep(260);
  }
  return 0;
 }
 if(argc>1 && std::string(argv[1])=="notices"){
  const unsigned long long expected[][3]={{7,0,0},{0,7,0},{0,0,0},{8,0,0},{0,0,0},{0,0,0},{9,8,1},{0,0,0}};
  for(const auto& pair:expected){
   BbscMod::PartyMaintain();
   bool counted=false;
   if(BbscMod::PartyBellGeneration(counted)!=pair[0] || BbscMod::PartyBellReleasedGeneration()!=pair[1] || counted!=pair[2])return 30;
   Sleep(260);
  }
  return 0;
 }

 if(argc>1 && std::string(argv[1])=="async-cancel"){
  const auto ticket=BbscMod::PartyRequestAcquire();
  if(!ticket)return 20;
  auto network=std::async(std::launch::async,[]{BbscMod::PartyMaintain();});
  std::puts("frame-thread-ready");std::fflush(stdout);
  if(std::getchar()==EOF)return 21;
  BbscMod::PartyCancel();
  std::puts("cancelled-with-network-blocked");std::fflush(stdout);
  network.get();
  if(BbscMod::PartyAcquireResult(ticket)!=BbscMod::PartyAcquireMailbox::Stale)return 22;
  std::puts("late-grant-discarded");return 0;
 }
 if(argc>1 && std::string(argv[1])=="idle"){
  BbscMod::PartyObserve(3,false,true,1,true); BbscMod::PartyMaintain(); Sleep(300);
  BbscMod::PartyCancel(); BbscMod::PartyObserve(0,false,false,1,true); BbscMod::PartyMaintain(); return 0;
 }
 if(argc>1 && std::string(argv[1])=="title"){
  BbscMod::PartyCancel(); BbscMod::PartyObserve(0,false,false,1,true); BbscMod::PartyMaintain();
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
 const auto ticket=BbscMod::PartyRequestAcquire();
 const auto end=GetTickCount64()+12000;
 auto result=BbscMod::PartyAcquireMailbox::Stale;
 do {
  BbscMod::PartyMaintain();result=BbscMod::PartyAcquireResult(ticket);
  if(result!=BbscMod::PartyAcquireMailbox::Queued && result!=BbscMod::PartyAcquireMailbox::Working)break;
  Sleep(10);
 } while(GetTickCount64()<end);
 std::puts(result==BbscMod::PartyAcquireMailbox::Granted?"granted":"denied");
}
'''
class BridgeTests(ProcessTests):
 def setUp(self):
  super().setUp()
  from unittest.mock import patch
  self.enterContext(patch.dict(os.environ,PATH='C:/msys64/clang64/bin;'+os.environ.get('PATH','')))
 def test_host_hint_and_responder_snapshot(self):
  replies=iter([b'0 0 0 7 1',b'0 0 0 0 2',b'1 0 0 0 3',b'1 0'])
  seen=[]
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_POST(self):
    seen.append(json.loads(self.rfile.read(int(self.headers.get('Content-Length',0)))))
    body=next(replies);self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  cpp=self.root/'roles.cpp';exe=self.root/'roles.exe';cpp.write_text(SOURCE)
  subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-DFMT_HEADER_ONLY',
   '-I',str(ROOT/'emulator/mod'),'-I',str(ROOT/'emulator/mod/shim'),'-I',str(ROOT/'emulator/externals/fmt/include'),
   str(cpp),str(ROOT/'emulator/mod/bbsc_party.cpp'),'-lwinhttp','-o',str(exe)],check=True)
  env=dict(os.environ,BBSC_PARTY='1',BBSC_PARTY_PORT=str(server.server_port),BBSC_PARTY_TOKEN='fixture',BBSC_PARTY_INSTANCE=uuid.uuid4().hex)
  try:
   subprocess.run([str(exe),'roles'],env=env,check=True,timeout=10)
   self.assertEqual(len(seen),4)
   self.assertEqual([body['bell_ring_seq'] for body in seen],[0,1,1,1])
   for body in seen:
    self.assertTrue(body['host_check']);self.assertTrue(body['responder']);self.assertTrue(body['fresh'])
    self.assertTrue(body['placement_ticket'])
    self.assertEqual(body['members'],1);self.assertFalse(body['bell'])
  finally:server.shutdown();server.server_close();thread.join()
 def test_notice_reply_versions_and_malformed_release(self):
  replies=iter([b'0 0 7 0',b'1 0 0 7',b'1 0',b'0 0 8',b'1 0 0 invalid',b'garbage',b'0 0 9 8 1 1',b'0 0 10 8 1 2'])
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_POST(self):
    self.rfile.read(int(self.headers.get('Content-Length',0)))
    body=next(replies);self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  cpp=self.root/'notice.cpp';exe=self.root/'notice.exe';cpp.write_text(SOURCE)
  subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-DFMT_HEADER_ONLY',
   '-I',str(ROOT/'emulator/mod'),'-I',str(ROOT/'emulator/mod/shim'),'-I',str(ROOT/'emulator/externals/fmt/include'),
   str(cpp),str(ROOT/'emulator/mod/bbsc_party.cpp'),'-lwinhttp','-o',str(exe)],check=True)
  env=dict(os.environ,BBSC_PARTY='1',BBSC_PARTY_PORT=str(server.server_port),BBSC_PARTY_TOKEN='fixture',BBSC_PARTY_INSTANCE=uuid.uuid4().hex)
  try:subprocess.run([str(exe),'notices'],env=env,check=True,timeout=10)
  finally:server.shutdown();server.server_close();thread.join()
 def test_blocked_http_does_not_block_cancel_or_revive_grant(self):
  entered,release=threading.Event(),threading.Event()
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_POST(self):
    self.rfile.read(int(self.headers.get('Content-Length',0)))
    if self.path=='/party/acquire':entered.set();release.wait(8);body=b'1'
    else:body=b'1 0'
    self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  cpp=self.root/'async.cpp';exe=self.root/'async.exe';cpp.write_text(SOURCE)
  subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-DFMT_HEADER_ONLY',
   '-I',str(ROOT/'emulator/mod'),'-I',str(ROOT/'emulator/mod/shim'),'-I',str(ROOT/'emulator/externals/fmt/include'),
   str(cpp),str(ROOT/'emulator/mod/bbsc_party.cpp'),'-lwinhttp','-o',str(exe)],check=True)
  env=dict(os.environ,BBSC_PARTY='1',BBSC_PARTY_PORT=str(server.server_port),BBSC_PARTY_TOKEN='fixture',BBSC_PARTY_INSTANCE=uuid.uuid4().hex)
  proc=subprocess.Popen([str(exe),'async-cancel'],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
  try:
   self.assertEqual(proc.stdout.readline().strip(),'frame-thread-ready')
   self.assertTrue(entered.wait(3))
   proc.stdin.write('\n');proc.stdin.flush()
   # A blocked production WinHTTP call is still outstanding at this point.
   self.assertEqual(proc.stdout.readline().strip(),'cancelled-with-network-blocked')
   self.assertIsNone(proc.poll());release.set()
   out,_=proc.communicate(timeout=5)
   self.assertEqual(proc.returncode,0);self.assertIn('late-grant-discarded',out)
  finally:
   release.set()
   if proc.poll() is None:proc.kill();proc.wait()
   proc.stdin.close();proc.stdout.close();server.shutdown();server.server_close();thread.join()
 def test_native_title_with_offline_peer_preserves_group_fence(self):
  a,b=self.group(2,compat=True)
  self.assertNotIn('error',a.op('acquire'))
  rid=a.op('room_create',room={'max_slots':5,'world':1,'bins':[],'flags':0,'member_bins':[]})['result']
  a.op('claim',target='B',claim={});b.op('room_join',room_id=rid)
  cpp=self.root/'title.cpp';exe=self.root/'title.exe';cpp.write_text(SOURCE)
  subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-DFMT_HEADER_ONLY',
    '-I',str(ROOT/'emulator/mod'),'-I',str(ROOT/'emulator/mod/shim'),'-I',str(ROOT/'emulator/externals/fmt/include'),
    str(cpp),str(ROOT/'emulator/mod/bbsc_party.cpp'),'-lwinhttp','-o',str(exe)],check=True)
  env=dict(os.environ);env.update(BBSC_PARTY='1',BBSC_PARTY_PORT=str(b.info['http']),BBSC_PARTY_TOKEN=b.info['token'],BBSC_PARTY_INSTANCE='title-'+uuid.uuid4().hex)
  a.kill() # stale joined participation, as in the reported Player 1 run
  proc=subprocess.Popen([str(exe),'title'],env=env,stdout=subprocess.PIPE,text=True)
  try:
   self.assertEqual(proc.stdout.readline().strip(),'waiting')
   out,_=proc.communicate(timeout=6)
   self.assertEqual(proc.returncode,0);self.assertIn('confirmed-and-old-ack-invalidated',out)
   snap=b.state()['state'];self.assertEqual(snap['owner'],'A');self.assertIn('B',snap['joined'])
   self.assertEqual(snap['owner'],'A') # unresolved ownership still fences admission
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
