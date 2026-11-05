"""Exercise production aura preparation with isolated PARAM rows, no game/save writes."""
import os
from pathlib import Path
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] /
          'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')


def function(signature):
    start = source.index(signature + ' {')
    opening = source.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


fixture = r'''
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <string_view>
using u64=uint64_t; using s64=int64_t; using s32=int32_t; using s16=int16_t;
#define LOG_INFO(...) ((void)0)
u64 image_base=1, active=0; s64 now=0; int lookups=0;
bool keep=false;
bool EnvFlagEnabled(const char*) {return keep;}
s64 SteadyNowMs() {return now;}
template<class T> T ReadValue(u64 p, size_t off) {
    T v; std::memcpy(&v,(void*)(p+off),sizeof(v)); return v;
}
template<class T> void WriteValue(u64 p, size_t off,T v) {
    std::memcpy((void*)(p+off),&v,sizeof(v));
}
u64 BbscParamRow(u64 table, uint32_t id, size_t size) {
    assert(id==272 && size==0x40); return table;
}
u64 BbscGameParamTable(std::string_view type) {
    assert(type=="SP_EFFECT_VFX_PARAM_ST"); ++lookups; return active;
}
using Row=std::array<unsigned char,64>;
Row vanilla() {
    Row r; r.fill(0xff); u64 p=(u64)r.data();
    WriteValue<s32>(p,0,211); WriteValue<s16>(p,0x24,203); return r;
}
'''
fixture += function('bool PrepareBbscGuestAppearance(u64 table)')
fixture += function('void TickBbscGuestAppearance()')
fixture += r'''
int main(int argc,char**) {
    Row homeBell=vanilla(), transition=vanilla(), r=vanilla();
    auto original=r;
    if(argc>1) {keep=true; active=(u64)r.data(); TickBbscGuestAppearance();
        assert(r==original && lookups==0); return 0;}
    assert(!PrepareBbscGuestAppearance(0));
    assert(PrepareBbscGuestAppearance((u64)r.data()));
    auto expected=original; WriteValue<s32>((u64)expected.data(),0,-1);
    assert(r==expected); // all other bytes, including start/finish, unchanged
    assert(homeBell==original && transition==original);
    assert(PrepareBbscGuestAppearance((u64)r.data()) && r==expected);
    for(int off: {0,8,16,36}) {
        r=original; r[off]^=1; auto custom=r;
        assert(!PrepareBbscGuestAppearance((u64)r.data()) && r==custom);
    }
    image_base=0; TickBbscGuestAppearance(); assert(lookups==0);
    image_base=1; active=0; TickBbscGuestAppearance(); assert(lookups==1);
    r=original; active=(u64)r.data(); now=999; TickBbscGuestAppearance();
    assert(r==original && lookups==1);
    now=1000; TickBbscGuestAppearance(); assert(r==expected && lookups==2);
    // A replaced repository/table is prepared too (load/reconnect).
    Row replacement=original; active=(u64)replacement.data();
    now=2000; TickBbscGuestAppearance(); assert(replacement==expected);
}
'''
assert 'TickBbscGuestAppearance();' in source[source.index('void PS4_SYSV_ABI TraceEntry('):]
with tempfile.TemporaryDirectory(prefix='bbsc-appearance-') as temp:
    cpp, exe = Path(temp) / 'test.cpp', Path(temp) / 'test.exe'
    cpp.write_text(fixture, encoding='utf-8')
    subprocess.run([os.environ.get('CXX', 'g++'), '-std=c++20', str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
    subprocess.run([str(exe), 'keep-aura'], check=True)
print('PASS: only persistent guest aura changed; transition fields, custom rows, reload, retry and opt-out preserved')
