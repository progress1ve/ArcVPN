"""Prepare Finland with disabled delivery. Read target-generated key from stdin.

Run on the control plane, not a developer checkout. No credential output.
"""
import asyncio
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path('/root/ArcVPN')
sys.path.insert(0, str(ROOT))
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config

NAME = 'ArcVPN Finland 1chost'
DOMAIN = 'fin.arccnet.space'
TAGS = {'EE_1CHOST_VLESS_TCP': 'FI_1CHOST_VLESS_TCP',
        'EE_1CHOST_LTE_XHTTP': 'FI_1CHOST_LTE_XHTTP',
        'EE_SS_BRIDGE': 'FI_SS_BRIDGE'}

def items(payload, key):
    value = payload.get('response', payload) if isinstance(payload, dict) else payload
    return value.get(key, []) if isinstance(value, dict) else value or []

async def main():
    material = json.load(sys.stdin)
    client = RemnawaveClient({**remnawave_authority_config(), 'panel_write_mode': 'production'})
    try:
        profiles = items(await client._request('GET', '/api/config-profiles'), 'configProfiles')
        nodes = items(await client._request('GET', '/api/nodes'), 'nodes')
        if any(p['name'] == NAME for p in profiles) or any(n['name'] == NAME for n in nodes):
            raise RuntimeError('Finland already exists; inspect partial state before retry')
        ee = next(p for p in profiles if p['name'] == 'ArcVPN Estonia 1chost')
        cfg = copy.deepcopy(ee['config'])
        cfg['inbounds'] = [i for i in cfg['inbounds'] if i['tag'] in TAGS]
        for inbound in cfg['inbounds']:
            old = inbound['tag']
            inbound['tag'] = TAGS[old]
            inbound['settings']['clients'] = []
            if old == 'EE_1CHOST_VLESS_TCP':
                inbound['streamSettings']['realitySettings'] = {
                    'target': '127.0.0.1:8443', 'serverNames': [DOMAIN],
                    'privateKey': material['private_key'], 'shortIds': [material['short_id']], 'xver': 0,
                }
            elif old == 'EE_1CHOST_LTE_XHTTP':
                inbound['streamSettings']['xhttpSettings']['path'] = '/api-fin'
        for rule in cfg.get('routing', {}).get('rules', []):
            if 'inboundTag' in rule:
                rule['inboundTag'] = [TAGS.get(t, t) for t in rule['inboundTag']]
        profile = await client._request('POST', '/api/config-profiles', json={'name': NAME, 'config': cfg})
        ids = {i['tag']: i['uuid'] for i in profile['inbounds']}
        node = await client._request('POST', '/api/nodes', json={
            'name': NAME, 'address': '92.42.102.139', 'port': 22600,
            'configProfile': {'activeConfigProfileUuid': profile['uuid'], 'activeInbounds': list(ids.values())},
            'isTrafficTrackingActive': False, 'trafficLimitBytes': 0, 'notifyPercent': 0,
            'trafficResetDay': 1, 'excludedInbounds': [], 'countryCode': 'FI', 'consumptionMultiplier': 1.0,
        })
        hosts = []
        for tag, remark, address, path, sni in [
            ('FI_1CHOST_VLESS_TCP', 'Финляндия #1', DOMAIN, '', DOMAIN),
            ('FI_1CHOST_LTE_XHTTP', 'Обход глушилок Финляндия', 'cdn-de.arccnet.space', '/api-fin', 'cdn-de.arccnet.space'),
        ]:
            host = await client._request('POST', '/api/hosts', json={
                'remark': remark, 'address': address, 'port': 443, 'path': path,
                'host': address if path else '', 'sni': sni, 'alpn': 'h2,http/1.1' if path else None,
                'fingerprint': 'firefox', 'allowInsecure': False, 'isDisabled': True,
                'isHidden': False, 'securityLayer': 'TLS' if path else 'DEFAULT', 'nodes': [node['uuid']],
                'inbound': {'configProfileUuid': profile['uuid'], 'configProfileInboundUuid': ids[tag]},
            })
            hosts.append(host['uuid'])
        secret = (await client._request('GET', '/api/keygen'))['secretKey']
        folder = ROOT / '.secrets'
        folder.mkdir(exist_ok=True)
        for name, content in [('finland-node-secret.txt', str(secret)), ('finland-remnawave-state.json', json.dumps({
            'profile_uuid': profile['uuid'], 'node_uuid': node['uuid'], 'inbounds': ids,
            'hosts': hosts, 'public_key': material['public_key'], 'short_id': material['short_id'],
        }))]:
            target = folder / name
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as output: output.write(content)
        print(json.dumps({'prepared': True, 'delivery_disabled': True, 'inbounds': len(ids)}))
    finally:
        await client.close()

if __name__ == '__main__': asyncio.run(main())
