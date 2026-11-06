"""Run the production profiler and DLL sink with a deterministic clock."""
from pathlib import Path
import os, subprocess, tempfile

ROOT = Path(__file__).resolve().parents[1]
core = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
mod = (ROOT / 'emulator/mod/bbsc_mod.cpp').read_text(encoding='utf-8')

def function(source, signature):
    start = source.index(signature + ' {')
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

profiler = core[core.index('struct BbscPerfSlot {'):core.index('\nenum class TraceKind')]
profiler = profiler.replace(function(profiler, 'inline u64 BbscPerfNowNs()'),
                            'u64 fake_ns=1; inline u64 BbscPerfNowNs() { return fake_ns; }')
prefix = r'''
#include <windows.h>
#include <algorithm>
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <deque>
#include <mutex>
#include <string>
#include <utility>
#include <vector>
#include "common/logging/log.h"
using u64=unsigned long long;
std::mutex log_mutex;
FILE* log_file=stderr;
namespace BbscMod {
'''
sink = function(mod, 'void LogLine(char level, const char* category, const std::string& text)')
main = r'''
int main() {
    assert(!BbscMod::ShouldLog('I'));
    int formatted=0;
    LOG_INFO(Debug, "unrelated Info {}", ++formatted);
    assert(formatted==0);
    TickBbscPerfReport();
    {
        BBSC_PERF_SCOPE("outer");
        BBSC_PERF_NESTED("measure fixture");
        fake_ns+=20000000;
    }
    fake_ns+=10000000000;
    TickBbscPerfReport();
    if (BbscPerfEnabled()) {
        assert(bbsc_perf_slots.size()==2);
        for (const auto& slot:bbsc_perf_slots) {
            assert(slot.ns==20000000 && slot.calls==1);
            assert(slot.max_ns==0 && slot.over8==0 && slot.over16==0);
        }
    } else {
        assert(bbsc_perf_slots.empty() && bbsc_perf_frames==0);
    }
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-perf-') as temp:
    folder=Path(temp); src=folder/'probe.cpp'; exe=folder/'probe.exe'
    src.write_text(prefix+sink+'\n}\n'+profiler+main, encoding='utf-8')
    env=dict(os.environ, PATH='C:/msys64/clang64/bin;'+os.environ.get('PATH',''))
    subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++23','-O2',
                    '-DBBSC_MOD','-I'+str(ROOT/'emulator/mod/shim'),str(src),
                    '-lfmt','-o',str(exe)], env=env,check=True)
    for enabled in ('0','1'):
        result=subprocess.run([str(exe)],env=dict(env,SHADPS4_BBSC_PERF=enabled,
            BB_DIAGNOSTICS='0',BBSC_LOG='warning'),capture_output=True,text=True,
            check=True,timeout=10)
        if enabled=='1':
            assert 'BBSC perf: 1 game frames' in result.stderr
            assert 'BBSC 20000 us/frame on top' in result.stderr
            assert 'scope=measure fixture nested=true frames=1 calls=1 total_us=20000 max_us=20000' in result.stderr
            assert 'over8=1 over16=1 over50=0' in result.stderr
            assert 'unrelated Info' not in result.stderr
        else:
            assert not result.stderr
print('PASS: production PERF survives warning; off has no output/counters; nested costs not double counted')
