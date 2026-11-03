"""Run production menu/save fixture with the actual party title gate compiled in."""
from pathlib import Path
root=Path(__file__).resolve().parent
source=(root/'test_menu_quit.py').read_text(encoding='utf-8')
source=source.replace('#define PS4_SYSV_ABI',"""#define BBSC_MOD
namespace BbscMod {
bool party_ready=true;
void PartyCancel() {}
void PartyEndTitleWait() {}
bool PartyTitleReady() {return party_ready;}
}
#define PS4_SYSV_ABI""")
source=source.replace('int main() {',"""int main() {
    reset(); BbscMod::party_ready=false; confirm(); TickBbscPendingQuit();
    result(0); memory[world+0x1554]=0; TickBbscPendingQuit();
    session=0; TickBbscPendingQuit();
    assert(BbscQuitInProgress() && memory[request_address]==0);
    assert(memory[menu+0x2DC]==1 && memory[0xb00111]==1);
    now+=60000; TickBbscPendingQuit();
    assert(memory[request_address]==0); // timeout is never a group confirmation
    BbscMod::party_ready=true; TickBbscPendingQuit();
    assert(memory[request_address]==2); // only now may title loading start
""")
exec(compile(source,str(root/'test_menu_quit.py'),'exec'),{'__file__':str(root/'test_menu_quit.py'),'__name__':'__main__'})
print('Party menu: native idle is insufficient; final party ACK required before title, no timeout bypass PASS')
