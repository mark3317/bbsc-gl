"""Host ritual helper binding through production callbacks and Windows trampolines.

Allocated memory only. Native constructor/decoder stand-ins check their ABI and
model different personal/host glyph, channel and layer data. The original ELF
checks establish the actual native input and capture sites separately.
"""
from pathlib import Path
import os, shutil, subprocess, tempfile
import struct
import test_world_altar_menu_hooks as hooks

prefix = hooks.prefix
source = hooks.source
main = r'''
int constructs=0,updates=0;
void PS4_SYSV_ABI Construct(void* p,const s32* slot){
 assert(*slot>=0&&*slot<7);++constructs;
 WriteValue<s32>(reinterpret_cast<u64>(p),0xC8,*slot);
}
void PS4_SYSV_ABI Update(void* p,const void* frame){
 assert(ReadValue<u64>(reinterpret_cast<u64>(frame),8)==0);++updates;
 const s32 slot=ReadValue<s32>(reinterpret_cast<u64>(p),0xC8);
 assert(altar_view_calls>0);
 const auto& a=bbsc_world_altars[slot];
 WriteValue<u64>(reinterpret_cast<u64>(p),0xD8,a.mount.key.channel);
 // Distinct native glyph/layer metadata decoded from the host record.
 WriteValue<u8>(reinterpret_cast<u64>(p),0x158,a.entry.record[220]);
 WriteValue<u8>(reinterpret_cast<u64>(p),0x178,a.entry.record[625]);
}
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 Link(0x01AA3110,reinterpret_cast<void*>(&Construct));
 Link(0x01AA6860,reinterpret_cast<void*>(&Update));
 bbsc_world_presence_local.world={11,99};bbsc_world_catalog_ready=true;
 std::array<u8,0x270> personal{};Set(personal,0xD8,u64{123});Set(personal,0x158,u8{8});Set(personal,0x178,u8{2});
 const auto before=personal;
 // Native c73 selects the altar before c79 captures its helper. Preserve the
 // original command/arguments while authorizing reads for the selected host cup.
 std::array<u8,0x30> condition{};Set(condition,0,image_base+TalkConditionVtableOffset);
 Set(condition,0x10,u32{210060});Set(condition,0x18,u64{0x40000});
 bbsc_world_altars[1].entry.occupied=true;bbsc_world_altars[1].entry.ritual=37;
 NoteBbscWorldTalkRecord(reinterpret_cast<u64>(condition.data()),0x50000);
 GuestRegisterSnapshot select;select.r14=0x50000;select.rax=73;
 BbscWorldAltarCommand(0,&select);assert(select.rax==73&&BbscWorldGuestAltarMenuActive()&&bbsc_world_guest_altar_menu.slot==1);
 for(s32 slot=0;slot<7;++slot){
  auto& a=bbsc_world_altars[slot];a.entry.occupied=true;a.entry.ritual=36+slot;
  a.mount.key.channel=900+slot;a.entry.record[220]=40+slot;a.entry.record[625]=4;
  bbsc_world_guest_altar_menu={bbsc_world_presence_local.world,1,slot,a.entry.ritual};
  GuestRegisterSnapshot r;r.rbx=slot;r.rcx=reinterpret_cast<u64>(personal.data());r.rax=r.rcx;
  BbscWorldAltarHelper(1,&r);assert(r.rcx!=reinterpret_cast<u64>(personal.data()));
  assert(ReadValue<u64>(r.rcx,0xD8)==a.mount.key.channel);
  assert(ReadValue<u8>(r.rcx,0x158)==40+slot&&ReadValue<u8>(r.rcx,0x178)==4);
  const u64 helper=r.rcx;BbscWorldAltarHelper(0,&r);assert(r.rax==helper);
  r.rsi=reinterpret_cast<u64>(personal.data());BbscWorldAltarHelper(2,&r);
  assert(r.rsi==helper); // visible panel inlines the personal helper lookup
  assert(constructs==slot+1&&updates==slot+1&&personal==before);
 }
 auto& a=bbsc_world_altars[6];GuestRegisterSnapshot r;r.rbx=6;r.rcx=reinterpret_cast<u64>(personal.data());r.rax=r.rcx;
 // Same incarnation, newer host progress/glyph: native view refreshes once.
 a.entry.record[220]=71;a.entry.record[625]=6;BbscWorldAltarHelper(1,&r);
 const u64 helper=r.rcx;assert(ReadValue<u8>(helper,0x158)==71&&ReadValue<u8>(helper,0x178)==6);
 assert(constructs==7&&updates==8);BbscWorldAltarHelper(1,&r);assert(updates==8);
 // The menu's borrowed helper must receive the original per-frame updates,
 // including the real frame input. A cached one-time decode is insufficient
 // for native asynchronous work. Other slots and the personal helper stay put.
 Set(personal,0xC8,s32{6});const auto personal_selected=personal;
 GuestRegisterSnapshot tick;tick.rdi=reinterpret_cast<u64>(personal.data());tick.rsi=0x123456;
 BbscWorldAltarUpdate(0,&tick);assert(tick.rdi==helper&&tick.rsi==0x123456);
 assert(personal==personal_selected);
 tick.rdi=reinterpret_cast<u64>(personal.data());bbsc_world_altar_view_refreshing=true;
 BbscWorldAltarUpdate(0,&tick);assert(tick.rdi==reinterpret_cast<u64>(personal.data()));bbsc_world_altar_view_refreshing=false;
 state=3;BbscWorldAltarUpdate(0,&tick);assert(tick.rdi==reinterpret_cast<u64>(personal.data()));state=6;
 Set(personal,0xC8,s32{5});BbscWorldAltarUpdate(0,&tick);assert(tick.rdi==reinterpret_cast<u64>(personal.data()));
 personal=before;
 // Execute the real Windows hook at the native update entry. The original
 // prologue/epilogue and caller return must survive changing only this (RDI).
 auto* update_entry=reinterpret_cast<u8*>(image_base+0x01AA6860);
 const u8 update_code[]={0x55,0x48,0x89,0xE5,0x41,0x57,0x48,0x89,0xF8,0x41,0x5F,0x5D,0xC3};
 std::memcpy(update_entry,update_code,sizeof(update_code));
 assert(Core::InstallGuestCodeHook(update_entry,{update_entry,6},0,BbscWorldAltarUpdate));
 using NativeUpdate=u64 PS4_SYSV_ABI (*)(void*,const void*);
 Set(personal,0xC8,s32{6});
 assert(reinterpret_cast<NativeUpdate>(update_entry)(personal.data(),nullptr)==helper);
 state=3;assert(reinterpret_cast<NativeUpdate>(update_entry)(personal.data(),nullptr)==reinterpret_cast<u64>(personal.data()));state=6;
 personal=before;
 // No borrowed pointer for host, wrong slot, missing catalog, expired scope.
 auto unchanged=[&](){GuestRegisterSnapshot n;n.rbx=6;n.rax=n.rcx=n.rsi=123;
  BbscWorldAltarHelper(0,&n);BbscWorldAltarHelper(1,&n);BbscWorldAltarHelper(2,&n);
  assert(n.rax==123&&n.rcx==123&&n.rsi==123);};
 state=3;unchanged();state=6;
 bbsc_world_catalog_ready=false;unchanged();bbsc_world_catalog_ready=true;
 ++bbsc_load_generation;unchanged();--bbsc_load_generation;
 ++bbsc_world_presence_local.world.room;unchanged();--bbsc_world_presence_local.world.room;
 ++a.entry.ritual;unchanged();--a.entry.ritual;
 a.entry.occupied=false;unchanged();a.entry.occupied=true;
 r.rbx=5;r.rcx=123;BbscWorldAltarHelper(1,&r);assert(r.rcx==123);
 // Real capture instructions run AFTER callback. RAX/vtable and frame survive.
 auto* capture=reinterpret_cast<u8*>(image_base+0x01B661CF);
 const u8 stores[]={0x48,0x89,0x45,0xA0,0x48,0x89,0x4D,0xA8,0xC3};
 std::memcpy(capture,stores,sizeof(stores));assert(Core::InstallGuestCodeHook(capture,{capture,8},1,BbscWorldAltarHelper));
 auto* caller=reinterpret_cast<u8*>(image_base+0x01B66000);
 // Save RBX/RBP, create native frame, use slot6 and PERSONAL input in RCX.
 const u8 call[]={0x55,0x53,0x48,0x83,0xEC,0x68,0x48,0x8D,0x6C,0x24,0x60,
  0xBB,6,0,0,0,0x48,0x89,0xF9,0xB8,0x78,0x56,0x34,0x12,
  0xE8,0,0,0,0,0x48,0x8B,0x45,0xA0,0x48,0x89,0x06,0x48,0x8B,0x45,0xA8,
  0x48,0x83,0xC4,0x68,0x5B,0x5D,0xC3};
 std::memcpy(caller,call,sizeof(call));s32 rel=static_cast<s32>(capture-(caller+29));std::memcpy(caller+25,&rel,4);
 using Capture=u64 PS4_SYSV_ABI (*)(void*,u64*);u64 vtable=0;
 assert(reinterpret_cast<Capture>(caller)(personal.data(),&vtable)==helper&&vtable==0x12345678);
 state=3;assert(reinterpret_cast<Capture>(caller)(personal.data(),&vtable)==reinterpret_cast<u64>(personal.data()));state=6;
 // Exact selected-helper return epilogue contains RET. No extra native frame
 // may be popped, and the original helper stays untouched.
 auto* ret=reinterpret_cast<u8*>(image_base+0x01AC3EE7);
 const u8 epilogue[]={0x5B,0x41,0x5E,0x5D,0xC3};std::memcpy(ret,epilogue,sizeof(epilogue));
 assert(Core::InstallGuestCodeHook(ret,{ret,5},0,BbscWorldAltarHelper));
 const u8 wrapper[]={0x55,0x41,0x56,0x53,0xBB,6,0,0,0,0x48,0x89,0xF8,0xE9,0,0,0,0};
 std::memcpy(caller,wrapper,sizeof(wrapper));rel=static_cast<s32>(ret-(caller+17));std::memcpy(caller+13,&rel,4);
 using Access=u64 PS4_SYSV_ABI (*)(void*);
 assert(reinterpret_cast<Access>(caller)(personal.data())==helper);
 // The visible panel never calls the selected-helper getter. Execute its
 // original inlined lookup, then the production hook at the exact next LEA.
 // Two distinct native caches in the SAME slot must render the host metadata.
 auto* panel=reinterpret_cast<u8*>(image_base+0x01B77227);
 const u8 panel_code[]={0x4C,0x8D,0xBD,0x40,0xFC,0xFF,0xFF,0x48,0x89,0xF0,0xC3};
 std::memcpy(panel,panel_code,sizeof(panel_code));
 assert(Core::InstallGuestCodeHook(panel,{panel,7},2,BbscWorldAltarHelper));
 // RDI = native singleton; RBX = selected slot; RSI = 0x108 + altar[slot].
 const u8 panel_caller[]={0x55,0x53,0x41,0x57,0x48,0x81,0xEC,0xC0,3,0,0,
  0x48,0x89,0xE5,0xBB,6,0,0,0,0x49,0x89,0xFF,
  0x49,0x8B,0x47,8,0xBE,8,1,0,0,0x48,0x03,0x34,0xD8,
  0xE8,0,0,0,0,0x48,0x81,0xC4,0xC0,3,0,0,0x41,0x5F,0x5B,0x5D,0xC3};
 std::memcpy(caller,panel_caller,sizeof(panel_caller));
 rel=static_cast<s32>(panel-(caller+40));std::memcpy(caller+36,&rel,4);
 std::array<u64,7> slots{};slots[6]=reinterpret_cast<u64>(personal.data())-0x108;
 std::array<u64,2> manager{7,reinterpret_cast<u64>(slots.data())};
 assert(reinterpret_cast<Access>(caller)(manager.data())==helper);
 assert(ReadValue<u8>(helper,0x158)==71&&ReadValue<u8>(helper,0x178)==6);
 state=3;assert(reinterpret_cast<Access>(caller)(manager.data())==reinterpret_cast<u64>(personal.data()));state=6;
 ++bbsc_load_generation;assert(reinterpret_cast<Access>(caller)(manager.data())==reinterpret_cast<u64>(personal.data()));--bbsc_load_generation;
 assert(personal==before);
 state=3;
 assert(personal==before);VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}
'''

def run():
    compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-host-altar-view-') as tmp:
        cpp=Path(tmp)/'view.cpp';exe=Path(tmp)/'view.exe';cpp.write_text(prefix+source+main,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
            '-I',str(hooks.ROOT/'emulator/src'),'-I',str(hooks.ROOT/'emulator/externals/xbyak'),
            str(cpp),str(hooks.ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env,timeout=15)
    print('PASS native host helper ABI, seven slots, glyph/layers, refresh, personal isolation, scoped getters and real capture/return trampolines')
    if os.environ.get('BBSC_TEST_EBOOT'):
        data=Path(os.environ['BBSC_TEST_EBOOT']).read_bytes()
        ph=struct.unpack_from('<Q',data,32)[0];size,n=struct.unpack_from('<HH',data,54)
        segments=[struct.unpack_from('<II6Q',data,ph+i*size) for i in range(n)]
        def read(a,n):
            s=next(s for s in segments if s[0]==1 and s[3]<=a and a+n<=s[3]+s[5])
            return data[s[2]+a-s[3]:s[2]+a-s[3]+n]
        def call(a,target):
            assert read(a,1)==b'\xe8' and a+5+struct.unpack('<i',read(a+1,4))[0]==target
        assert read(0x1B661BF,9)==bytes.fromhex('b9 08 01 00 00 48 03 0c d8')
        assert read(0x1B661CF,8)==bytes.fromhex('48 89 45 a0 48 89 4d a8')
        assert read(0x1AC3EE3,9)==bytes.fromhex('48 03 04 d9 5b 41 5e 5d c3')
        # Visible menu panel independently indexes the personal singleton;
        # getter/c79 capture hooks alone cannot affect its glyph/layer render.
        assert read(0x1B7721A,13)==bytes.fromhex('49 8b 47 08 be 08 01 00 00 48 03 34 d8')
        assert read(0x1B77227,7)==bytes.fromhex('4c 8d bd 40 fc ff ff')
        call(0x1B77231,0x1C50250);call(0x1B7725E,0x1C506C0)
        assert read(0x1C50264,3)==bytes.fromhex('49 89 f5')
        assert read(0x1C50278,7)==bytes.fromhex('41 8b 85 e0 00 00 00')
        assert read(0x1C502FA,14)==bytes.fromhex('49 8d b5 40 01 00 00 49 8d 95 50 01 00 00')
        # Promise builder copies the captured helper from its payload into RSI
        # and the layer builder keeps that helper in the menu callback itself.
        assert read(0x1B752A6,11)==bytes.fromhex('48 8b 46 08 48 89 85 68 ff ff ff')
        assert read(0x1B75404,7)==bytes.fromhex('48 8b 9d 68 ff ff ff')
        call(0x1B7540E,0x1B66330);call(0x1B6639E,0x1B66EF0)
        assert read(0x1B66F5B,7)==bytes.fromhex('4c 89 a5 20 fd ff ff')
        # Native helper constructor takes slot* in RSI; update reads host flag
        # getters for channel, seed, parts and the persisted native glyph.
        assert read(0x1AA32B3,9)==bytes.fromhex('41 8b 06 89 83 c8 00 00 00')
        assert read(0x1AB4572,7)==bytes.fromhex('48 8d bb 08 01 00 00')
        call(0x1AB457C,0x1AA3110) # original altar constructs this exact helper
        assert read(0x1AA362A,10)==bytes.fromhex('c7 83 6c 02 00 00 00 00 00 00')
        call(0x1AA68A9,0x1AB2A40);call(0x1AA68C2,0x1AB2CA0)
        assert read(0x1AA6860,6)==bytes.fromhex('55 48 89 e5 41 57')
        # Native altar update dispatches this helper's virtual update with the
        # frame pointer; it does not merely refresh when the altar record changes.
        assert read(0x1AC3F49,14)==bytes.fromhex('48 8b 83 08 01 00 00 48 8b 80 d0 00 00 00')
        assert read(0x1AC3F6D,9)==bytes.fromhex('48 8d 75 80 4c 89 f7 ff d0')
        call(0x1AA6964,0x1AB3070);call(0x1AA6B71,0x1AB3840)
        # Native update's frame parameter and delta input; no guessed ABI.
        assert read(0x1AA687B,5)==bytes.fromhex('48 89 74 24 10')
        assert read(0x1AA701A,10)==bytes.fromhex('48 8b 44 24 10 c5 fa 5c 40 08')
        print('PASS original 1.09 helper constructor/decoder inputs and native promise/layer-helper binding')

if __name__=='__main__':run()
