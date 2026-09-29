"""Apply owner-approved GET/header repair without changing client identities."""
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

PATCH = {'uplinkHTTPMethod': 'GET', 'uplinkDataPlacement': 'header',
         'uplinkDataKey': 'X-Session-Token'}

async def run():
    c = RemnawaveClient({**remnawave_authority_config(), 'panel_write_mode': 'production'})
    try:
        profiles = items(await c._request('GET', '/api/config-profiles'), 'configProfiles')
        hosts = items(await c._request('GET', '/api/hosts'), 'hosts')
        affected = [h for h in hosts if h.get('address') == 'cdn-de.arccnet.space'
                    and h.get('path') in ('/api-test', '/api-fin')]
        profile_ids = {h['inbound']['configProfileUuid'] for h in affected}
        selected = [p for p in profiles if p['uuid'] in profile_ids]
        backup = ROOT / 'backups/cdn-get-before.json'
        with backup.open('x', encoding='utf-8') as f:
            backup.chmod(0o600)
            json.dump({'profiles': selected, 'hosts': affected}, f)
        for p in selected:
            cfg = copy.deepcopy(p['config'])
            count = 0
            for inbound in cfg['inbounds']:
                xs = inbound.get('streamSettings', {}).get('xhttpSettings')
                if xs and xs.get('path') in ('/api-test', '/api-fin'):
                    xs.update(PATCH)
                    count += 1
            if count:
                await c._request('PATCH', '/api/config-profiles', json={
                    'uuid': p['uuid'], 'name': p['name'], 'config': cfg})
        for h in affected:
            extra = h.get('xhttpExtraParams') or {}
            if isinstance(extra, str):
                extra = json.loads(extra)
            extra.update(PATCH)
            await c._request('PATCH', '/api/hosts', json={
                'uuid': h['uuid'], 'xhttpExtraParams': extra})
        print(json.dumps({'profiles_updated': len(selected), 'hosts_updated': len(affected),
                          'paths_preserved': True, 'identities_preserved': True}))
    finally:
        await c.close()

if __name__ == '__main__':
    asyncio.run(run())
