"""Control-plane replacement; key material arrives on stdin, never logs."""
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


async def run(material):
    c = RemnawaveClient({**remnawave_authority_config(), 'panel_write_mode': 'production'})
    try:
        profiles = items(await c._request('GET', '/api/config-profiles'), 'configProfiles')
        nodes = items(await c._request('GET', '/api/nodes'), 'nodes')
        hosts = items(await c._request('GET', '/api/hosts'), 'hosts')
        squads = items(await c._request('GET', '/api/internal-squads'), 'internalSquads')
        p = next(x for x in profiles if x['name'] == 'ArcVPN Finland 1chost')
        n = next(x for x in nodes if x['name'] == p['name'])
        if n['address'] != '92.42.102.139':
            raise RuntimeError('Replacement already started; inspect before retry')
        old = {i['uuid']: i['tag'] for i in p['inbounds']}
        path = ROOT / 'backups/finland-replacement-before.json'
        with path.open('x', encoding='utf-8') as f:
            path.chmod(0o600)
            json.dump({'profile': p, 'node': n, 'hosts': hosts, 'squads': squads}, f)
        cfg = copy.deepcopy(p['config'])
        for i in cfg['inbounds']:
            if i['tag'] == 'FI_1CHOST_VLESS_TCP':
                r = i['streamSettings']['realitySettings']
                r['privateKey'] = material['private_key']
                r['shortIds'] = [material['short_id']]
        fi_hosts = [h for h in hosts if (h.get('inbound') or {}).get('configProfileUuid') == p['uuid']]
        for h in fi_hosts:
            await c._request('PATCH', '/api/hosts', json={'uuid': h['uuid'], 'isDisabled': True})
        updated = await c._request('PATCH', '/api/config-profiles', json={'uuid': p['uuid'], 'name': p['name'], 'config': cfg})
        new = {i['tag']: i['uuid'] for i in updated['inbounds']}
        await c._request('PATCH', '/api/nodes', json={'uuid': n['uuid'], 'address': '151.241.137.174', 'configProfile': {'activeConfigProfileUuid': p['uuid'], 'activeInbounds': list(new.values())}})
        for s in squads:
            before = [i['uuid'] for i in s.get('inbounds', [])]
            after = [new[old[v]] if v in old else v for v in before]
            if before != after:
                await c._request('PATCH', '/api/internal-squads', json={'uuid': s['uuid'], 'inbounds': after})
        for h in fi_hosts:
            await c._request('PATCH', '/api/hosts', json={'uuid': h['uuid'], 'inbound': {'configProfileUuid': p['uuid'], 'configProfileInboundUuid': new[old[h['inbound']['configProfileInboundUuid']]]}})
        state = ROOT / '.secrets/finland-remnawave-state.json'
        data = json.loads(state.read_text())
        data.update({'inbounds': new, 'public_key': material['public_key'], 'short_id': material['short_id'], 'address': '151.241.137.174'})
        state.write_text(json.dumps(data), encoding='utf-8')
        state.chmod(0o600)
        print(json.dumps({'replaced': True, 'delivery_disabled': True, 'public_key': material['public_key']}))
    finally:
        await c.close()


if __name__ == '__main__':
    asyncio.run(run(json.load(sys.stdin)))
