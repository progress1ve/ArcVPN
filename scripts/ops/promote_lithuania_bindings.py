"""Attach LT inbounds to existing main/LTE squads without changing identities."""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, '/root/ArcVPN')
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
from scripts.ops.pause_sweden_to_estonia import identity_hash

ROOT = Path('/root/ArcVPN')
SECRET = ROOT / '.secrets'
STATE = SECRET / 'lithuania-canary-20261027.json'
BEFORE = SECRET / 'lithuania-global-bindings-before-20261027.json'
ENV = ROOT / '.env.remnawave-staging'


def items(data, key):
    return data.get(key, []) if isinstance(data, dict) else data


def ids(squad):
    return [x['uuid'] if isinstance(x, dict) else x for x in squad.get('inbounds', [])]


def write_private(path, text):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(text)


async def main():
    state = json.loads(STATE.read_text())
    assert state.get('delivery_enabled') and not state.get('global_enabled')
    assert not BEFORE.exists(), 'Inspect previous rollout state before retry'
    c = RemnawaveClient({**remnawave_authority_config(), 'panel_write_mode': 'production'})
    env_before = ENV.read_text()
    changed = []
    try:
        squads = items(await c._request('GET', '/api/internal-squads'), 'internalSquads')
        main = next(x for x in squads if x['name'] == 'ArcVPN Staging')
        lte = next(x for x in squads if x['name'] == 'ArcVPN LTE')
        lt = state['inbounds']
        wanted_main = [lt[x] for x in ('LT_1CHOST_VLESS_TCP', 'LT_WARP_REALITY', 'LT_1CHOST_HYSTERIA2')]
        wanted_lte = [v for k, v in lt.items() if 'XHTTP' in k or 'CDN' in k]
        assert len(wanted_lte) >= 4
        before_hash = identity_hash()
        write_private(BEFORE, json.dumps({'main': main, 'lte': lte, 'env': env_before, 'identity_hash': before_hash}))
        key = 'REMNAWAVE_SQUAD_INBOUND_UUIDS='
        lines = env_before.splitlines()
        matches = [i for i, line in enumerate(lines) if line.startswith(key)]
        assert len(matches) == 1, 'Expected exactly one squad inbounds setting'
        pos = matches[0]
        existing = [x.strip() for x in lines[pos][len(key):].split(',') if x.strip()]
        lines[pos] = key + ','.join(dict.fromkeys(existing + wanted_main))
        temp = ENV.with_name('.env.remnawave-staging.lt-tmp')
        write_private(temp, '\n'.join(lines) + '\n')
        os.replace(temp, ENV)
        for squad, target in ((main, wanted_main), (lte, wanted_lte)):
            await c._request('PATCH', '/api/internal-squads', json={
                'uuid': squad['uuid'], 'inbounds': list(dict.fromkeys(ids(squad) + target))})
            changed.append(squad)
        latest = items(await c._request('GET', '/api/internal-squads'), 'internalSquads')
        for squad, target in ((main, wanted_main), (lte, wanted_lte)):
            now = next(x for x in latest if x['uuid'] == squad['uuid'])
            assert set(target).issubset(ids(now)), 'Squad readback failed'
        assert identity_hash() == before_hash, 'Customer identity changed'
        print('LT main and LTE inbounds added; EE retained; customer identities unchanged')
    except Exception:
        for squad in reversed(changed):
            await c._request('PATCH', '/api/internal-squads', json={'uuid': squad['uuid'], 'inbounds': ids(squad)})
        ENV.write_text(env_before)
        raise
    finally:
        await c.close()


if __name__ == '__main__':
    asyncio.run(main())
