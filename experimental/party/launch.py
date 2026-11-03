"""Executed by the existing frozen BBGL --script role; stays alive around run.py."""
import __main__ as bbgl
import os,runpy,sys
from pathlib import Path
port=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[4]
profile=Path(os.environ['BBGL_PROFILE_DIR'])
settings=bbgl.app_settings({})
settings.update(game_dir=os.environ['BB_PARTY_GAME'],user_dir=str(profile/'user'),
                player_name=os.environ['BB_PARTY_MEMBER'],mods_enabled=True)
env=bbgl.game_environment(settings)
env.update(BB_PARTY_CONFIG=os.environ['BB_PARTY_CONFIG'],BB_PARTY_MEMBER=os.environ['BB_PARTY_MEMBER'],
           BBGL_PROFILE_DIR=str(profile),BB_DATA_DIR=str(profile),BBSC_SAVE_DIR=str(profile/'seed/SPRJ0005'))
os.environ.update(env)
sys.argv=[str(port/'run.py')]
runpy.run_path(str(port/'run.py'),run_name='__main__')
