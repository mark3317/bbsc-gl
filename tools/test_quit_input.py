"""Production pad filter: neutral input during confirmed exit, errors and cancellation."""
from pathlib import Path
import os,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
code=r'''
#include "core/bbsc_quit_input.h"
#include <array>
#include <cassert>
using namespace Core::Bbsc;
int main(){
 std::array<std::uint8_t,128> data;data.fill(255);auto original=data;
 assert(!BlockQuitPadInput(0,data.data())&&data==original);
 quit_input_blocked=true;
 assert(!BlockQuitPadInput(-1,data.data())&&data==original);
 assert(!BlockQuitPadInput(0,nullptr));
 assert(BlockQuitPadInput(0,data.data()));
 assert(data[0]==0&&data[1]==0&&data[2]==0&&data[3]==128);
 for(int i=4;i<8;++i)assert(data[i]==128);
 assert(data[8]==0&&data[9]==0);
 for(int i=10;i<128;++i)assert(data[i]==255); // timestamps, connected status, sensors intact
 quit_input_blocked=false;data=original;
 assert(!BlockQuitPadInput(0,data.data())&&data==original);
}
'''
with tempfile.TemporaryDirectory() as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe';cpp.write_text(code)
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-I'+str(root/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('Production confirmed-quit pad blocking: PASS')
