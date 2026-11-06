"""Provision the owner-only Royale node on the controller. Key material via stdin."""
import asyncio
import json
import os
from pathlib import Path
import sys

import subscription_api as api
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config

NAME = 'ArcVPN Netherlands Royale'
DOMAIN = 'nl.arccnet.space'
TAG = 'NL_ROYALE_OWNER'
SQUAD = 'ArcVPN Royale owner only'
STATE = Path('.secrets/royale-owner-nl.json')


def protected_write(path, data):
    temp = path.with_suffix('.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream)
    temp.replace(path)


async def provision(material, identity):
    client = RemnawaveClient(remnawave_authority_config())
    try:
        user = await client.get_user_by_vless_uuid(identity)
        if not user or user.get('status') != 'ACTIVE':
            raise RuntimeError('Active owner identity unavailable')
        config = {
            'log': {'loglevel': 'warning'},
            'dns': {'servers': ['1.1.1.1', '1.0.0.1']},
            'inbounds': [{'tag': TAG, 'port': 443, 'listen': '0.0.0.0', 'protocol': 'vless',
                'settings': {'clients': [], 'decryption': 'none'},
                'sniffing': {'enabled': True, 'destOverride': ['http', 'tls', 'quic']},
                'streamSettings': {'network': 'raw', 'security': 'reality', 'realitySettings': {
                    'xver': 0, 'target': '127.0.0.1:8443', 'serverNames': [DOMAIN],
                    'privateKey': material['private_key'], 'shortIds': [material['short_id']]}}}],
            'outbounds': [{'tag': 'DIRECT', 'protocol': 'freedom'}, {'tag': 'BLOCK', 'protocol': 'blackhole'}],
            'routing': {'rules': [{'type': 'field', 'ip': ['geoip:private'], 'outboundTag': 'BLOCK'},
                {'type': 'field', 'domain': ['geosite:private'], 'outboundTag': 'BLOCK'},
                {'type': 'field', 'protocol': ['bittorrent'], 'outboundTag': 'BLOCK'}]},
        }
        profiles = (await client._request('GET', '/api/config-profiles'))['configProfiles']
        profile = next((p for p in profiles if p['name'] == NAME), None)
        if profile is None:
            profile = await client._request('POST', '/api/config-profiles', json={'name': NAME, 'config': config})
        else:
            reality = profile['config']['inbounds'][0]['streamSettings']['realitySettings']
            if reality['privateKey'] != material['private_key']:
                raise RuntimeError('Existing profile has different key material')
        inbound = next(i['uuid'] for i in profile['inbounds'] if i['tag'] == TAG)
        nodes = await client._request('GET', '/api/nodes')
        if isinstance(nodes, dict):
            nodes = nodes['nodes']
        node = next((n for n in nodes if n['name'] == NAME), None)
        if node is None:
            node = await client._request('POST', '/api/nodes', json={
                'name': NAME, 'address': '45.141.202.248', 'port': 22600, 'countryCode': 'NL',
                'consumptionMultiplier': 1, 'configProfile': {
                    'activeConfigProfileUuid': profile['uuid'], 'activeInbounds': [inbound]}})
        hosts = await client._request('GET', '/api/hosts')
        if isinstance(hosts, dict):
            hosts = hosts['hosts']
        if not any(h.get('remark') == NAME for h in hosts):
            await client._request('POST', '/api/hosts', json={
                'remark': NAME, 'address': DOMAIN, 'port': 443, 'sni': DOMAIN,
                'fingerprint': 'firefox', 'allowInsecure': False, 'securityLayer': 'DEFAULT',
                'isDisabled': True, 'isHidden': True, 'nodes': [node['uuid']], 'inbound': {
                    'configProfileUuid': profile['uuid'], 'configProfileInboundUuid': inbound}})
        squads = (await client._request('GET', '/api/internal-squads'))['internalSquads']
        squad = next((s for s in squads if s['name'] == SQUAD), None)
        if squad is None:
            squad = await client._request('POST', '/api/internal-squads', json={'name': SQUAD, 'inbounds': [inbound]})
        memberships = [s['uuid'] if isinstance(s, dict) else s for s in user.get('activeInternalSquads', [])]
        if squad['uuid'] not in memberships:
            protected_write(STATE.with_name('royale-owner-before.json'), {'user_id': user['id'], 'squads': memberships})
            await client._request('PATCH', '/api/users', json={'id': user['id'],
                'activeInternalSquads': [*memberships, squad['uuid']]})
        verified = await client.get_user_by_vless_uuid(identity)
        actual = {s['uuid'] if isinstance(s, dict) else s for s in verified.get('activeInternalSquads', [])}
        assert set(memberships) | {squad['uuid']} == actual
        assert verified['vlessUuid'] == identity
        protected_write(STATE, {'enabled': False, 'public_key': material['public_key'],
            'short_id': material['short_id'], 'node_uuid': node['uuid'], 'squad_uuid': squad['uuid'],
            'client_uuid': identity})
        keygen = await client._request('GET', '/api/keygen')
        protected_write(STATE.with_name('royale-node-secret.json'), {'secret': keygen['secretKey']})
        print('Royale profile, node and exclusive owner assignment prepared')
    finally:
        await client.close()


if __name__ == '__main__':
    profiles = api._effective_customer_profiles()
    sweden = next(p for p in profiles if p['remarks'] == '🇸🇪 Швеция')
    proxy = next(o for o in sweden['outbounds'] if o['protocol'] == 'vless')
    asyncio.run(provision(json.load(sys.stdin), proxy['settings']['vnext'][0]['users'][0]['id']))
