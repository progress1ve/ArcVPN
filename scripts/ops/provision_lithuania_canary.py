"""Owner-approved LT onboarding; execute on Poland with node material on stdin.

No global squad/host/catalog edits. Owner bindings only; delivery gate is separate.
Private state stays in the control-plane .secrets directory, never stdout.
"""
import asyncio
import copy
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, '/root/ArcVPN')
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
from database.connection import get_db

ROOT = Path('/root/ArcVPN/.secrets')
STATE = ROOT / 'lithuania-canary-20261027.json'
NAME = 'ArcVPN Lithuania Cherry'
IP = '88.216.62.135'
TLS_NAME = '88-216-62-135.sslip.io'


def items(value, key):
    return value.get(key, []) if isinstance(value, dict) else value


def save(path, data):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        json.dump(data, f)


async def main():
    assert not STATE.exists(), 'Inspect existing partial state before retry'
    material = json.load(sys.stdin)
    c = RemnawaveClient({**remnawave_authority_config(), 'panel_write_mode': 'production'})
    try:
        profiles = items(await c._request('GET', '/api/config-profiles'), 'configProfiles')
        assert not any(p['name'] == NAME for p in profiles)
        ee = next(p for p in profiles if p['name'] == 'ArcVPN Estonia 1chost')
        with get_db() as db:
            owner = dict(db.execute('SELECT id,telegram_id,device_limit,lte_panel_username FROM users WHERE id=1').fetchone())
            key = dict(db.execute('SELECT panel_email,client_uuid FROM vpn_keys WHERE id=185 AND user_id=1').fetchone())
        assert owner['telegram_id'] == 2075630349 and owner['device_limit'] == 6
        main_user = await c.get_user(key['panel_email'])
        lte_user = await c.get_user(owner['lte_panel_username'])
        assert main_user['vlessUuid'] == key['client_uuid']
        save(ROOT / 'lithuania-owner-before-20261027.json', {'main': main_user, 'lte': lte_user})
        cfg = copy.deepcopy(ee['config'])
        tags = {i['tag']: i['tag'].replace('EE_', 'LT_', 1) for i in cfg['inbounds']}
        for i in cfg['inbounds']:
            i['tag'] = tags[i['tag']]
            i['settings']['clients'] = []
            s = i.get('streamSettings', {})
            if s.get('security') == 'reality':
                s['realitySettings'] = {'target': '127.0.0.1:8443', 'serverNames': [TLS_NAME],
                    'privateKey': material['private_key'], 'shortIds': [material['short_id']], 'xver': 0}
            if s.get('security') == 'tls':
                for cert in s['tlsSettings'].get('certificates', []):
                    cert['keyFile'] = '/var/lib/remnawave/configs/xray/ssl/lt-privkey.pem'
                    cert['certificateFile'] = '/var/lib/remnawave/configs/xray/ssl/lt-fullchain.pem'
            if 'xhttpSettings' in s:
                x = s['xhttpSettings']
                x['path'] = x['path'].replace('/api-se', '/api-lt').replace('/api-ee', '/api-lt').replace('/api-test', '/api-lt-test')
        for rule in cfg.get('routing', {}).get('rules', []):
            if 'inboundTag' in rule:
                rule['inboundTag'] = [tags.get(t, t) for t in rule['inboundTag']]
        next(o for o in cfg['outbounds'] if o['tag'] == 'YOUTUBE_RU')['settings']['servers'][0]['address'] = '95.182.120.237'
        profile = await c._request('POST', '/api/config-profiles', json={'name': NAME, 'config': cfg})
        ids = {i['tag']: i['uuid'] for i in profile['inbounds']}
        # Save immediately after each irreversible create for bounded recovery.
        save(STATE, {'profile_uuid': profile['uuid'], 'inbounds': ids,
            'public_key': material['public_key'], 'short_id': material['short_id'], 'tls_name': TLS_NAME})
        node = await c._request('POST', '/api/nodes', json={
            'name': NAME, 'address': IP, 'port': 22600,
            'configProfile': {'activeConfigProfileUuid': profile['uuid'], 'activeInbounds': list(ids.values())},
            'isTrafficTrackingActive': False, 'trafficLimitBytes': 0, 'notifyPercent': 0,
            'trafficResetDay': 1, 'excludedInbounds': [], 'countryCode': 'LT', 'consumptionMultiplier': 1.0})
        state = json.loads(STATE.read_text()); state['node_uuid'] = node['uuid']
        for label, user, selected in [
            ('main', main_user, [v for k, v in ids.items() if 'XHTTP' not in k and 'CDN' not in k]),
            ('lte', lte_user, [v for k, v in ids.items() if 'XHTTP' in k or 'CDN' in k]),
        ]:
            squad = await c._request('POST', '/api/internal-squads', json={'name': 'ArcVPN LT Owner ' + label, 'inbounds': selected})
            state[label + '_squad'] = squad['uuid']
            old = [x['uuid'] if isinstance(x, dict) else x for x in user['activeInternalSquads']]
            await c._request('PATCH', '/api/users', json={'id': user['id'], 'activeInternalSquads': list(dict.fromkeys(old + [squad['uuid']]))})
        state['main_uuid'] = main_user['vlessUuid']; state['lte_uuid'] = lte_user['vlessUuid']
        with STATE.open('w') as f:
            json.dump(state, f)
        print('Lithuania node/profile created; only two owner identities authorized; no global hosts edited')
    finally:
        await c.close()


if __name__ == '__main__':
    asyncio.run(main())
