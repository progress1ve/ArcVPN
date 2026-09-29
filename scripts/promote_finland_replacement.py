"""Promote verified replacement, retire legacy FI display endpoint."""
import asyncio
import copy
import json
import sys
from pathlib import Path
ROOT = Path('/root/ArcVPN')
sys.path.insert(0, str(ROOT))
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
from scripts.provision_germany_node import items

async def run():
    c = RemnawaveClient({**remnawave_authority_config(), 'panel_write_mode': 'production'})
    try:
        ps = items(await c._request('GET', '/api/config-profiles'), 'configProfiles')
        hosts = items(await c._request('GET', '/api/hosts'), 'hosts')
        ru = next(p for p in ps if p['name'] == 'ArcVPN Moscow Bridge')
        legacy = next(p for p in ps if p['name'] == 'ArcVPN Finland')
        backup = ROOT / 'backups/fi-promotion-before.json'
        with backup.open('x') as f:
            backup.chmod(0o600)
            json.dump({'profile': ru, 'hosts': hosts}, f)
        cfg = copy.deepcopy(ru['config'])
        o = next(o for o in cfg['outbounds'] if o['tag'] == 'FI_BRIDGE')
        o['settings']['servers'][0]['address'] = '151.241.137.174'
        b = next(b for b in cfg['routing']['balancers'] if b['tag'] == 'EU_BRIDGE')
        b['selector'] = ['EE_BRIDGE', 'FI_BRIDGE']
        await c._request('PATCH', '/api/config-profiles', json={'uuid': ru['uuid'], 'name': ru['name'], 'config': cfg})
        for h in hosts:
            if h['inbound']['configProfileUuid'] == legacy['uuid']:
                await c._request('PATCH', '/api/hosts', json={'uuid': h['uuid'], 'isDisabled': True})
        print('Verified FI enabled in Moscow pool; legacy FI display hosts disabled')
    finally:
        await c.close()
if __name__ == '__main__':
    asyncio.run(run())
