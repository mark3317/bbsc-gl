"""Production independent-world rules: place, expiry, ownership, channels and guest altars.

No game process, profile, save, or network needed. The live bridge still advertises
only presence; these rules do not claim native travel or enemy handover is ready.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CODE = r'''
#include <cassert>
#include <limits>
#include "core/bbsc_world_presence.h"
#include "core/bbsc_world_altars.h"
#include "core/bbsc_world_control.h"
using namespace Core::Bloodborne;
using namespace Core::Bloodborne::World;
constexpr u32 Yharnam = 0x18000000, Dream = 0x15000000, Dungeon = 0x1D0A5A00;
Presence Sample(u32 map=Yharnam, u64 seq=1) {
    Presence p;
    p.world={11,99}; p.sequence=seq; p.visit=1; p.map=map;
    p.phase=Phase::Playing; p.alive=1;
    return p;
}
int main() {
    // Exact-length parsing and finite coordinates, reserved bytes, versions.
    Presence a=Sample(); assert(Valid(a));
    auto bytes=std::span{reinterpret_cast<const u8*>(&a),sizeof(a)};
    assert(Decode(bytes)); assert(!Decode(bytes.first(bytes.size()-1)));
    auto bad=a; bad.x=std::numeric_limits<float>::infinity(); assert(!Valid(bad));
    bad=a; bad.z=std::numeric_limits<float>::quiet_NaN(); assert(!Valid(bad));
    bad=a; bad.version=1; assert(!Valid(bad));
    bad=a; bad.sequence=0; assert(!Valid(bad));
    bad=a; bad.reserved=1; assert(!Valid(bad));
    namespace Finale=Core::Bbsc::DreamFinale;
    bad=a; bad.finale.ending=1; assert(!Valid(bad));
    PresenceBook finale; finale.Bind(a.world,22);
    auto recall=a; recall.capabilities|=NativeFinaleCapability;
    recall.finale={Finale::Phase::Recall,7,0};
    assert(!finale.Hear(33,a.world,recall,100));
    assert(finale.Hear(11,a.world,recall,100));
    assert(!finale.Hear(11,a.world,recall,101)); // replay cannot recall twice
    auto ready=recall; ready.finale.phase=Finale::Phase::Ready;
    assert(!finale.Hear(11,a.world,ready,101));
    assert(finale.Hear(33,a.world,ready,101));
    auto release=recall; ++release.sequence; release.finale={Finale::Phase::Release,7,2};
    assert(!finale.Hear(33,a.world,release,102));
    assert(finale.Hear(11,a.world,release,102));
    release.sequence++; release.finale.ending=4;
    assert(!finale.Hear(11,a.world,release,103));
    bad=a; bad.phase=static_cast<Phase>(9); assert(!Valid(bad));
    bad=a; bad.map=0; assert(!Valid(bad));
    bad=a; bad.alive=2; assert(!Valid(bad));
    bad=a; bad.world.room=0; assert(!Valid(bad));

    // Borders settle; zero reads don't invent a new place. A load into the same
    // map still invalidates presence immediately and creates a new visit.
    PlaceTracker tracker;
    tracker.Observe(Yharnam,false,true,100); assert(tracker.Visit()==1);
    tracker.Observe(Dream,false,true,200); assert(tracker.Map()==Yharnam);
    tracker.Observe(Yharnam,false,true,300);
    tracker.Observe(Dream,false,true,400);
    tracker.Observe(Dream,false,true,1899); assert(tracker.Map()==Yharnam);
    tracker.Observe(Dream,false,true,1900); assert(tracker.Map()==Dream && tracker.Visit()==2);
    tracker.Observe(0,false,true,2000); assert(tracker.Map()==Dream && tracker.Visit()==2);
    tracker.Observe(Dream,true,true,2100); assert(tracker.State()==Phase::Loading);
    tracker.Observe(Dream,false,false,2200); assert(tracker.State()==Phase::Loading);
    tracker.Observe(Dream,false,true,2300); assert(tracker.Visit()==3);
    tracker.Clear(); tracker.Observe(Dream,false,true,2400); assert(tracker.Visit()==4);

    // A native movie suspends all ticks; silence must not hand this map to a later host.
    auto resident=Sample();std::map<u32,Member> paused{{22,{resident,100,100}}};
    paused[11]={resident,10000,10000};
    assert(ChooseOwner(resident,paused,22,10000)==22);
    PresenceBook movie;movie.Bind(resident.world,11);assert(movie.Hear(22,resident.world,resident,100));
    auto later=resident;later.sequence++;assert(movie.Hear(33,resident.world,later,10000));
    assert(!movie.Find(22,10000)&&movie.Resident(22));
    paused[22].presence.phase=Phase::Loading;assert(ChooseOwner(resident,paused,22,10000)==11);
    auto layout=resident;layout.map=0x1d0a5a00;layout.dungeon={55,66,88,0};layout.ritual=18;
    assert(ScopeOf(layout).map==0x1d000000&&ScopeOf(layout).dungeon==layout.dungeon);

    // A member in another place/loading/leaving is not a participant here.
    auto b=a; assert(SamePlace(a,b));
    b.map=Dream; assert(!SamePlace(a,b));
    b=a; b.world.room++; assert(!SamePlace(a,b));
    b=a; b.phase=Phase::Loading; assert(!SamePlace(a,b));
    b=a; b.phase=Phase::Leaving; assert(!SamePlace(a,b));
    b=a; a.map=b.map=Dungeon; a.dungeon=b.dungeon={55,66,16,0};
    assert(!SamePlace(a,b));
    a.ritual=b.ritual=7; assert(SamePlace(a,b));
    b.map=0x1d0b5a00;assert(SamePlace(a,b)&&ScopeOf(a)==ScopeOf(b));b=a;
    b.ritual=8; assert(!SamePlace(a,b));
    b=a; b.dungeon.channel++; assert(!SamePlace(a,b));
    b=a; b.dungeon.form_hash++; assert(!SamePlace(a,b));
    a=Sample(); b=a;

    // Reject strangers, old worlds, replay, backwards visits and a fifth peer.
    PresenceBook book; book.Bind(a.world,11);
    assert(!book.Hear(11,a.world,a,100));
    assert(!book.Hear(0,a.world,a,100));
    assert(!book.Hear(22,{11,100},a,100));
    assert(book.Hear(22,a.world,a,100));
    assert(!book.Hear(22,a.world,a,101));
    assert(book.Find(22,3099)); assert(!book.Find(22,3100));
    const auto no_deaths = [](u32,s64){return false;};
    assert(book.LivingHere(a,no_deaths)==1); // a movie is not a death or departure
    assert(book.LivingHere(a,[](u32 peer,s64 received){return peer==22 && received==100;})==0);
    b=Sample(Dream,2); assert(book.Hear(22,b.world,b,3200));
    assert(book.LivingHere(a,no_deaths)==0);
    b=Sample(Yharnam,3); b.visit=2; assert(book.Hear(22,b.world,b,3300));
    bad=Sample(Yharnam,4); assert(!book.Hear(22,bad.world,bad,3400));
    book.Forget(22); assert(!book.Find(22,3400));
    assert(!book.Hear(22,a.world,a,3500)); // timeout/leave does not erase fences
    b.sequence=5; assert(book.Hear(22,b.world,b,3500));
    for (u32 peer: {23u,24u,25u}) assert(book.Hear(peer,a.world,a,3500));
    assert(!book.Hear(26,a.world,a,3500));
    book.Bind({11,100},11); assert(book.Members().empty());
    assert(!book.Hear(22,a.world,a,3500));

    // The first bridge cannot enable travel, including in a mixed-version room.
    book.Bind(a.world,11); b=a; assert(book.Hear(22,a.world,b,4000));
    const std::array<u32,1> roster{22};
    assert(!book.AllSupportTravel(a,roster,4000));
    a.capabilities|=IndependentTravelCapability;
    assert(!book.AllSupportTravel(a,roster,4000));
    b.sequence++; b.capabilities=a.capabilities; assert(book.Hear(22,a.world,b,4001));
    assert(book.AllSupportTravel(a,roster,4001));
    assert(!book.AllSupportTravel(a,roster,7001));

    // A full reset rebuilds the same map in the same room, in any load order.
    // Every observer rejects old actor traffic until the sender is Playing again.
    constexpr std::array<u32,3> hunters{11,22,33};
    std::array<unsigned,3> order{0,1,2};
    do {
        std::array<Presence,3> players{Sample(),Sample(),Sample()};
        std::array<PresenceBook,3> books;
        for (unsigned i=0;i<3;++i) books[i].Bind(players[i].world,hunters[i]);
        const auto publish = [&](unsigned i,s64 now) {
            for (unsigned j=0;j<3;++j)
                if (i!=j) assert(books[j].Hear(hunters[i],players[i].world,players[i],now));
        };
        for (unsigned i=0;i<3;++i) {
            players[i].alive=0;publish(i,1);
            players[i].phase=Phase::Loading;++players[i].sequence;publish(i,2);
        }
        for (unsigned i:order) {
            players[i].phase=Phase::Playing;players[i].alive=1;
            ++players[i].visit;++players[i].sequence;publish(i,3);
            for (unsigned j=0;j<3;++j) if (i!=j)
                assert(Routes(0x31,players[i],players[j])==(players[j].phase==Phase::Playing));
        }
        for (unsigned i=0;i<3;++i) {
            assert(books[i].LivingHere(players[i],no_deaths)==2);
            for (unsigned j=0;j<3;++j) if (i!=j) {
                const auto* resident=books[i].Resident(hunters[j]);
                assert(resident && resident->presence.visit==2 && SamePlace(players[i],resident->presence));
                assert(!books[i].Hear(hunters[j],players[i].world,Sample(),4));
            }
        }
    } while (std::next_permutation(order.begin(),order.end()));

    // Stable owner: a returning host follows the still-present owner first.
    std::map<u32,Member> owners{{11,{a,4000,3900}},{22,{b,4000,3800}}};
    assert(ChooseOwner(a,owners,22,4000)==22);
    assert(ChooseOwner(a,owners,0,4000)==11);
    owners[11].presence.map=Dream;
    assert(ChooseOwner(a,owners,0,4000)==22);
    owners[22].presence.phase=Phase::Loading;
    assert(ChooseOwner(a,owners,22,4000)==0);

    // Session handshake crosses maps. World actions do not; personal item
    // packets and thanks-kick stay separate from the shared simulation.
    b=a; b.map=Dream;
    for(u32 channel: {7u,0x10u,0x11u,0x19u,0x42u}) assert(Routes(channel,a,b));
    for(u32 channel: {4u,5u,6u,0x15u,0x31u,0x3Eu}) {
        assert(!Routes(channel,a,b)); assert(Routes(channel,a,a));
    }
    assert(!Routes(0x2C,a,a)); assert(!Routes(0x27,a,a)); assert(!Routes(0x44,a,a));

    // Whole host altar snapshots. Loading this view never touches personal data.
    AltarCatalog catalog; catalog.world=a.world; catalog.revision=1;
    for(auto& altar:catalog.altars) altar.ritual=1;
    auto& altar=catalog.altars[0]; altar.occupied=true; altar.record[0]=29;
    altar.form=std::vector<u8>(16,9);
    altar.dungeon={55,Chalice::HashForm(altar.form),16,0}; altar.lamps[0]=true;
    assert(Valid(catalog));
    const auto personal=catalog; GuestAltars guest; guest.Bind(a.world);
    assert(!guest.Take(22,catalog)); assert(guest.Take(11,catalog));
    assert(guest.Destination(0,1,0)); assert(!guest.Destination(0,1,1));
    assert(!guest.Destination(7,1,0)); assert(!guest.Destination(0,1,4));
    assert(!guest.Take(11,catalog));
    auto corrupt=catalog; corrupt.revision=2; corrupt.altars[0].form[0]^=1;
    assert(!guest.Take(11,corrupt)); assert(guest.Destination(0,1,0));
    auto replaced=catalog; replaced.revision=2; replaced.altars[0].record[1]=99;
    assert(!guest.Take(11,replaced)); // different ritual, same incarnation rejected
    replaced.altars[0].ritual=2; assert(guest.Take(11,replaced));
    assert(!guest.Destination(0,1,0)); assert(guest.Destination(0,2,0));
    auto removed=replaced; removed.revision=3; removed.altars[0]={}; removed.altars[0].ritual=3;
    assert(guest.Take(11,removed)); assert(!guest.Destination(0,2,0));
    assert(personal.altars[0].occupied && personal.altars[0].record[1]==0);
    guest.Bind({11,100}); assert(!guest.View());
}
'''

def main():
    compiler = os.environ.get('CXX') or shutil.which('clang++')
    if not compiler:
        compiler = r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-world-') as tmp:
        source = Path(tmp)/'world.cpp'
        exe = Path(tmp)/('world.exe' if os.name=='nt' else 'world')
        source.write_text(CODE,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-Wall','-Wextra','-Werror',
                        '-I',str(ROOT/'emulator/src'),str(source),'-o',str(exe)],check=True)
        env=os.environ.copy()
        env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS production world presence, place/visit, ownership selection, routing, guest altar isolation')

if __name__=='__main__':
    main()
