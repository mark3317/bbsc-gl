"""Native-confirmed terminal world snapshots; never promote a replacement host."""
import copy


def scope(state):
    return (state['owner'], state['generation'], (state.get('room') or {}).get('id'))


def terminal(base):
    result = copy.deepcopy(base)
    result.update(owner=None, room=None, joined={}, pending={}, revision=base['revision']+1)
    return result


def validate(record):
    base, issuer, reason = record['base'], record['issuer'], record['reason']
    if not base['owner'] or issuer not in base['roster']:
        raise ValueError('No owned session to retire')
    if reason in ('host_empty', 'host_stopped'):
        if issuer != base['owner']:
            raise ValueError('Only the host can confirm an empty world')
    elif reason == 'host_lost':
        witness = record['witness']
        room = witness.get('room') or {}
        if (issuer == base['owner'] or witness['owner'] != base['owner'] or
                witness['generation'] != base['generation'] or
                witness['epoch'] != base['epoch'] or
                (witness.get('room') or {}).get('id') != (base.get('room') or {}).get('id') or
                issuer not in set(witness['joined']) | set(room.get('members', {}))):
            raise ValueError('Host loss requires a participant in this world')
    else:
        raise ValueError('Unknown native retirement')
    return terminal(base)
