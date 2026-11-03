"""Exercise the production final-pad filter without game input or saves."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'emulator/mod/bbsc_mod.cpp').read_text(encoding='utf-8')
pad = source[source.index('int PS4_SYSV_ABI PadReadState('):source.index('void InstallPadWrapper() {')]
assert pad.index('original_pad_read(handle, data)') < pad.index('result != 0 || data == nullptr')
assert pad.index('result != 0 || data == nullptr') < pad.index('BbscQuitInputBlocked()')
assert pad.index('FilterBbscQuitPad(data);') < pad.index('if (!cine_state.enabled)')
fixture = r'''
#include <array>
#include <cassert>
#include "bbsc_quit_input.h"
int main() {
    for (bool connected : {false,true}) {
        std::array<std::uint8_t,128> data;
        data.fill(0xA5);
        const std::uint32_t buttons=connected ? 0xFFFFFFFFu : 0x7FFFFFFFu;
        std::memcpy(data.data(), &buttons,4);
        const auto original=data;
        FilterBbscQuitPad(data.data());
        std::uint32_t filtered;
        std::memcpy(&filtered,data.data(),4);
        assert(filtered==(connected ? 0x80000000u : 0));
        assert(data[4]==128 && data[5]==128);
        assert(data[8]==0 && data[9]==0);
        for (int i=6;i<128;++i) if(i!=8 && i!=9) assert(data[i]==original[i]);
        const auto once=data;
        FilterBbscQuitPad(data.data()); assert(data==once);
    }
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-quit-pad-') as temporary:
    cpp, exe = Path(temporary)/'test.cpp', Path(temporary)/'test.exe'
    cpp.write_text(fixture, encoding='utf-8')
    subprocess.run([os.environ.get('CXX','g++'), '-std=c++20', '-I',str(ROOT/'emulator/mod'),
                    str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=10)
print('Production quit pad filter (camera/connection/metadata preserved): PASS')
