"""Production gift visibility patch; fake memory and optional read-only original-data audit."""
from pathlib import Path
import os
import struct
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
s = (root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
a = s.index('void HideBbscNativeKitGift(u64 instance) {')
b = s.index('// EndIfClient blocks', a)
code = r'''
#include <cstdint>
#include <cstring>
#include <cassert>
#include <initializer_list>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define LOG_INFO(...)
enum class MemoryProt{CpuWrite};
u32 map=0x15000000;s64 event=12101024;bool writable=true;
u32 GetCurrentPackedMap(){return map;}s64 BbscEventIdOf(u64){return event;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
bool HasMemoryAccess(u64,size_t,MemoryProt){return writable;}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t o,T v){memcpy((void*)(p+o),&v,sizeof(v));}
''' + s[a:b] + r'''
int main(){
 u8 instance[0xC0]{},ref[0x10]{},file[0x100]{},instruction[0x20]{};
 const u64 inst=(u64)instance,cmd=(u64)instruction;
 auto reset=[&]{
  memset(instance,0,sizeof instance);memset(file,0,sizeof file);memset(instruction,0,sizeof instruction);
  map=0x15000000;event=12101024;writable=true;
  WriteValue<u64>(inst,0xA8,(u64)ref);WriteValue<u64>((u64)ref,8,(u64)file);
  WriteValue<u64>(inst,0xB0,cmd);WriteValue<u64>((u64)file,0x78,0x90);
  WriteValue<s32>(cmd,0,1003);WriteValue<s32>(cmd,4,101);WriteValue<u64>(cmd,8,8);
  WriteValue<u32>((u64)file,0x90,256);WriteValue<u32>((u64)file,0x94,6622);
 };
 auto unchanged=[&]{HideBbscNativeKitGift(inst);assert(ReadValue<s32>(cmd,0)==1003);assert(ReadValue<u32>((u64)file,0x90)==256);};
 HideBbscNativeKitGift(0);
 for(s64 other:{12101020LL,12101021LL,12101022LL,12101026LL,12101028LL}){reset();event=other;unchanged();}
 reset();map=0x18000000;unchanged();reset();writable=false;unchanged();
 reset();WriteValue<u64>(inst,0xB8,1);unchanged();
 reset();WriteValue<u32>((u64)file,0x94,6620);unchanged();
 reset();WriteValue<u64>(cmd,8,4);unchanged();
 reset();HideBbscNativeKitGift(inst);
 assert(ReadValue<s32>(cmd,0)==1000&&ReadValue<s32>(cmd,4)==4);
 assert(ReadValue<u64>(cmd,8)==4&&ReadValue<u32>((u64)file,0x90)==0);
 assert(ReadValue<u32>((u64)file,0x94)==6622);
 HideBbscNativeKitGift(inst);assert(ReadValue<s32>(cmd,0)==1000);
 reset();HideBbscNativeKitGift(inst);assert(ReadValue<s32>(cmd,0)==1000); // fresh load
}
'''
build = root/'build'
build.mkdir(exist_ok=True)
cpp = build/'test_native_kit_gift.cpp'
exe = cpp.with_suffix('.exe')
cpp.write_text(code, encoding='utf-8')
subprocess.run(['C:/msys64/clang64/bin/clang++.exe', '-std=c++20', str(cpp), '-o', str(exe)], check=True)
env = dict(os.environ)
env['PATH'] = 'C:/msys64/clang64/bin;' + env.get('PATH', '')
subprocess.run([str(exe)], env=env, check=True)
start = s.index('void PS4_SYSV_ABI BbscNpcPassHook(')
assert s.index('HideBbscNativeKitGift(registers->rdi)', start) < s.index('if (!bbsc_npc_pass_due', start)
if os.environ.get('BB_GAME'):
    sys.path.insert(0, str(root/'tools/gamedata'))
    from emevd import Emevd
    import bbfiles
    import param
    game = Path(os.environ['BB_GAME'])
    bbfiles.GAME = str(game)
    e = Emevd(game/'event/m21_00_00_00.emevd.dcx')
    events = dict(e.events)
    assert events[12101024][0] == (1003, 101, struct.pack('<II', 256, 6622))
    assert (2003, 2, struct.pack('<II', 12105054, 1)) in events[12101024]
    assert (2003, 4, struct.pack('<I', 10010)) in events[12101024]
    assert any((b, i, a) == (1000, 4, bytes(4)) for _, ins in e.events for b, i, a in ins)
    # No other instruction shares the argument bytes we rewrite.
    d = e.data
    n, off = struct.unpack_from('<qq', d, 0x20)
    records = [struct.unpack_from('<iiqq', d, off+j*0x20) for j in range(n)]
    arg = next(ao for b, i, alen, ao in records if (b, i, alen) == (1003, 101, 8)
               and d[e.args_off+ao:e.args_off+ao+8] == struct.pack('<II', 256, 6622))
    assert sum(alen > 0 and ao < arg+4 and arg < ao+alen for _, _, alen, ao in records) == 1
    lay, _, data, rows = param.load('ItemLotParam')
    for lot, goods in [(10010, 200), (10011, 111)]:
        v = param.row_values(lay, data, rows[lot])
        assert v['lotItemId01'] == goods and v['getItemFlagId'] == 6622
    for event, lot in [(12101022, 10000), (12101026, 10050), (12101028, 10040)]:
        assert (2003, 4, struct.pack('<I', lot)) in events[event]
    print('PASS: original gift event, Bell/Blank chain, argument ownership and other gifts (read-only)')
print('PASS: production patch, role-independent dispatch, reload/idempotence and invalid/unrelated guards')
