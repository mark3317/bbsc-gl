"""Production seed regression: an old map lease must not trap headstone travel."""
import test_world_native_bootstrap as harness
harness.MAIN = r'''
int main(){
 World::Presence local;local.world={11,99};local.map=0x15000000;local.phase=World::Phase::Playing;local.visit=1;local.sequence=1;
 bbsc_world_presence_local=local;
 bbsc_independent_owners.Bind(local.world);bbsc_world_presence_book.Bind(local.world,11);
 World::Scope destination{local.world,0x18010000,{},0};
 World::Control lease;lease.kind=World::ControlKind::Owner;lease.scope=destination;lease.owner=22;lease.epoch=9;
 assert(bbsc_independent_owners.Take(11,lease,100));
 auto peer=local;peer.map=destination.map;peer.sequence=2;
 assert(bbsc_world_presence_book.Hear(22,local.world,peer,100));
 BbscWorldEnsureSeed(destination);assert(!bbsc_independent_states.contains(destination));
 peer.phase=World::Phase::Loading;++peer.sequence;
 assert(bbsc_world_presence_book.Hear(22,local.world,peer,150));
 BbscWorldEnsureSeed(destination);assert(!bbsc_independent_states.contains(destination));
 peer.phase=World::Phase::Playing;peer.map=local.map;++peer.sequence;++peer.visit;
 assert(bbsc_world_presence_book.Hear(22,local.world,peer,200));
 BbscWorldEnsureSeed(destination);assert(BbscWorldFlagsReady(destination));
 assert(bbsc_independent_states.at(destination).epoch==9);
 const auto sequence=bbsc_independent_states.at(destination).sequence;
 BbscWorldEnsureSeed(destination);assert(bbsc_independent_states.at(destination).sequence==sequence);
 bbsc_independent_states.clear();self=22;
 BbscWorldEnsureSeed(destination);assert(bbsc_independent_states.empty());
 self=11;bbsc_world_presence_book.Forget(22);
 BbscWorldEnsureSeed(destination);assert(BbscWorldFlagsReady(destination));
}
'''
harness.main()
