"""Experimental BBGL entrypoint. Never creates a new group to recover a missing invite."""
import json
import os
import runpy
import shutil
import sys
import traceback
from pathlib import Path


def resolve_invitation(profile, port, configured):
    requested = Path(configured) if configured else profile / 'party/invitation.json'
    if requested.is_file():
        return requested
    bundled = port / 'coop/party/invitation.json'
    if not bundled.is_file():
        raise FileNotFoundError('Party invitation is missing. Restore the existing group invitation: ' + str(requested))
    # Validate before copying. Keep the existing group/secret; no automatic group reset.
    from engine import validate_invite
    validate_invite(json.loads(bundled.read_text(encoding='utf-8-sig')))
    target = profile / 'party/invitation.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        with target.open('x', encoding='utf-8') as f:
            f.write(bundled.read_text(encoding='utf-8-sig'))
    return target


def main(bbgl):
    port = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[4]
    profile = Path(os.environ['BBGL_PROFILE_DIR']).resolve()
    sys.path.insert(0, str(port / 'coop/party'))
    config = resolve_invitation(profile, port, os.environ.get('BB_PARTY_CONFIG'))
    from engine import validate_invite
    cfg = json.loads(config.read_text(encoding='utf-8-sig'))
    validate_invite(cfg)
    member = os.environ['BB_PARTY_MEMBER']
    if member not in {m['id'] for m in cfg['members']}:
        raise ValueError('This player is not a member of the saved invitation')
    if '--check' in sys.argv[1:]:
        result = {'ok': True, 'member': member, 'profile': str(profile), 'invitation': str(config)}
        (profile / 'party').mkdir(parents=True, exist_ok=True)
        (profile / 'party/startup-check.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print('Party startup check: PASS (game was not launched)', flush=True)
        return
    settings = bbgl.app_settings({})
    settings.update(game_dir=os.environ['BB_PARTY_GAME'], user_dir=str(profile / 'user'),
                    player_name=member, mods_enabled=True, fps_mode='60', frame_cap='60')
    env = bbgl.game_environment(settings)
    env.update(BB_FPS='60', BB_FPS_LIMIT='60')
    # Existing stock patch, selected only for this experimental launch.
    patches=[name.strip() for name in env.get('BB_PATCHES','').split(';') if name.strip()]
    if 'Skip Intro' not in patches: patches.append('Skip Intro')
    env['BB_PATCHES']=';'.join(patches)
    env.update(BB_PARTY_CONFIG=str(config), BB_PARTY_MEMBER=member,
               BBGL_PROFILE_DIR=str(profile), BB_DATA_DIR=str(profile), BB_CONFIG=str(profile / 'bbport.ini'),
               BB_MODS_CONFIG=str(profile / 'mods.json'), BB_PATCHES_CONFIG=str(profile / 'patches.json'),
               BBSC_SAVE_DIR=str(profile / 'seed/SPRJ0005'))
    os.environ.update(env)
    sys.argv = [str(port / 'run.py')]
    runpy.run_path(str(port / 'run.py'), run_name='__main__')


if 'BBGL_RUNTIME' in globals():
    try:
        main(BBGL_RUNTIME)
    except Exception:
        profile = Path(os.environ.get('BBGL_PROFILE_DIR', '.'))
        profile.mkdir(parents=True, exist_ok=True)
        (profile / 'party-launch-error.log').write_text(traceback.format_exc(), encoding='utf-8')
        raise
