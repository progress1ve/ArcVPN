"""Reversible owner-requested Sweden pause; run on Poland, never export secrets."""
import argparse
import asyncio
import base64
import copy
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
from database.connection import get_db
from database.db_settings import get_setting, set_setting
from monitoring.cdn_fallbacks import VARIANTS, outbound

ROOT = Path('/root/ArcVPN/.secrets')
SNAPSHOT = ROOT / 'estonia-fallback-before-20261025.json'
CANARY = ROOT / 'estonia-fallback-canary.json'
EE = '87.251.19.197'
SE = '136.148.220.228'
WARP = 'EE_WARP_REALITY'


def items(data, key):
    return data.get(key, []) if isinstance(data, dict) else data


def save(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        json.dump(value, f)


def identity_hash():
    with get_db() as conn:
        result = {}
        for table in ('vpn_keys','users'):
            columns = [r['name'] for r in conn.execute('PRAGMA table_info('+table+')') if r['name'] == 'id' or 'uuid' in r['name'] or 'token' in r['name']]
            result[table] = [tuple(r) for r in conn.execute('SELECT '+','.join(columns)+' FROM '+table+' ORDER BY id')]
    return hashlib.sha256(json.dumps(result).encode()).hexdigest()


def migrated_tag(tag):
    return tag.replace('SE_', 'EE_', 1)


def prepare_config(estonia, sweden):
    cfg = copy.deepcopy(estonia)
    known = {i['tag'] for i in cfg['inbounds']}
    wanted = []
    for variant in VARIANTS.values():
        tag = migrated_tag(variant['tag'])
        wanted.append(tag)
        if tag not in known:
            source = next(i for i in sweden['inbounds'] if i['tag'] == variant['tag'])
            new = copy.deepcopy(source)
            new.update(tag=tag, listen='127.0.0.1')
            new['settings']['clients'] = []
            cfg['inbounds'].append(new)
    if WARP not in known:
        new = copy.deepcopy(next(i for i in cfg['inbounds'] if i['tag'] == 'EE_1CHOST_VLESS_TCP'))
        new.update(tag=WARP, port=8444)
        new['settings']['clients'] = []
        cfg['inbounds'].append(new)
    for tag in ('WARP', 'WARP_DNS_TCP'):
        if not any(o['tag'] == tag for o in cfg['outbounds']):
            cfg['outbounds'].append(copy.deepcopy(next(o for o in sweden['outbounds'] if o['tag'] == tag)))
    rules = [{'type':'field', 'inboundTag':wanted, 'network':'tcp,udp', 'outboundTag':'DIRECT'}]
    for rule in sweden['routing']['rules']:
        if 'SE_HOSTUP_WARP_REALITY' in rule.get('inboundTag', []):
            new = copy.deepcopy(rule)
            new['inboundTag'] = [WARP]
            rules.append(new)
    existing = cfg['routing']['rules']
    cfg['routing']['rules'] = rules + [r for r in existing if r not in rules]
    cfg.setdefault('log', {}).update(access='/dev/shm/arcvpn-access.log', loglevel='warning')
    hy = next(i for i in cfg['inbounds'] if i['tag'] == 'EE_1CHOST_HYSTERIA2')
    hy['streamSettings']['tlsSettings']['certificates'] = [{
        'certificateFile':'/var/lib/remnawave/configs/xray/ssl/ee-public-fullchain.pem',
        'keyFile':'/var/lib/remnawave/configs/xray/ssl/ee-public-privkey.pem',
    }]
    return cfg, wanted


def moscow_on_estonia(config):
    cfg = copy.deepcopy(config)
    rules = []
    for source in cfg['routing']['rules']:
        if any(t.startswith('weighted-ru-') for t in source.get('inboundTag', [])):
            continue
        rule = copy.deepcopy(source)
        if 'balancerTag' in rule or rule.get('outboundTag') == 'SE_BRIDGE':
            rule.pop('balancerTag', None)
            rule['outboundTag'] = 'EE_BRIDGE'
        rules.append(rule)
    cfg['routing']['rules'] = rules
    cfg['routing'].pop('balancers', None)
    cfg['outbounds'] = [o for o in cfg['outbounds'] if o['tag'] != 'SE_BRIDGE' and not o['tag'].startswith('weighted-ru-')]
    cfg.pop('observatory', None)
    cfg.pop('burstObservatory', None)
    return cfg


async def state(client):
    result = {}
    for key, endpoint in (('profiles','config-profiles'), ('nodes','nodes'), ('hosts','hosts'), ('squads','internal-squads')):
        result[key] = items(await client._request('GET', '/api/' + endpoint), {'profiles':'configProfiles','squads':'internalSquads'}.get(key,key))
    return result


async def main(action):
    c = RemnawaveClient({**remnawave_authority_config(), 'panel_write_mode':'production'})
    try:
        live = await state(c)
        ee = next(p for p in live['profiles'] if p['name'] == 'ArcVPN Estonia 1chost')
        se = next(p for p in live['profiles'] if p['name'] == 'ArcVPN Sweden HostUp')
        node = next(n for n in live['nodes'] if n['address'] == EE)
        if not SNAPSHOT.exists():
            live['policy'] = get_setting('subscription_balancers_live')
            live['identity_hash'] = identity_hash()
            with get_db() as conn:
                live['overrides'] = [dict(r) for r in conn.execute('SELECT * FROM subscription_profile_overrides')]
            save(SNAPSHOT, live)
        before = json.loads(SNAPSHOT.read_text())
        if action == 'prepare':
            cfg, cdn_tags = prepare_config(ee['config'], se['config'])
            updated = await c._request('PATCH','/api/config-profiles',json={'uuid':ee['uuid'],'config':cfg})
            old = {i['tag']:i['uuid'] for i in ee['inbounds']}
            ids = {i['tag']:i['uuid'] for i in updated['inbounds']}
            assert all(ids[tag] == uid for tag,uid in old.items()), 'Existing inbound changed'
            for squad_name, tags in (('ArcVPN LTE',cdn_tags), ('ArcVPN Staging',[WARP,'EE_1CHOST_HYSTERIA2'])):
                squad = next(s for s in live['squads'] if s['name'] == squad_name)
                active = [i['uuid'] if isinstance(i,dict) else i for i in squad['inbounds']]
                await c._request('PATCH','/api/internal-squads',json={'uuid':squad['uuid'],'inbounds':list(dict.fromkeys(active+[ids[t] for t in tags]))})
            active = [i['uuid'] if isinstance(i,dict) else i for i in node['configProfile']['activeInbounds']]
            await c._request('PATCH','/api/nodes',json={'uuid':node['uuid'],'configProfile':{'activeConfigProfileUuid':ee['uuid'], 'activeInbounds':list(dict.fromkeys(active+[ids[t] for t in [*cdn_tags,WARP,'EE_1CHOST_HYSTERIA2']]))}})
            print('Estonia CDN+WARP authorized; existing inbound identities preserved')
        elif action == 'publish':
            ids = {i['tag']:i['uuid'] for i in ee['inbounds']}
            for h in live['hosts']:
                if h.get('address') not in ('se.arccnet.space',SE):
                    continue
                tag = WARP if 'Нейросети' in h['remark'] else 'EE_1CHOST_HYSTERIA2' if 'Игровой' in h['remark'] else 'EE_1CHOST_VLESS_TCP'
                await c._request('PATCH','/api/hosts',json={'uuid':h['uuid'],'address':'ee.arccnet.space','sni':'ee.arccnet.space', 'nodes':[node['uuid']], 'inbound':{'configProfileUuid':ee['uuid'],'configProfileInboundUuid':ids[tag]}})
            policy = json.loads(before['policy'])
            for p in policy:
                p['members'] = ['ee']
                p['weights'] = {'ee':100}
            set_setting('subscription_balancers_live',json.dumps(policy,ensure_ascii=False))
            with get_db() as conn:
                conn.execute("UPDATE subscription_profile_overrides SET include_in_auto=0 WHERE source_name='Швеция'")
            moscow = next(p for p in live['profiles'] if p['name'] == 'ArcVPN Moscow Bridge')
            await c._request('PATCH','/api/config-profiles',json={'uuid':moscow['uuid'],'config':moscow_on_estonia(moscow['config'])})
            sn = next(n for n in live['nodes'] if n['address'] == SE)
            if not sn.get('isDisabled'):
                await c._request('POST','/api/nodes/'+sn['uuid']+'/actions/disable')
            assert identity_hash() == before['identity_hash'], 'Customer identities changed'
            print('Sweden aliases, Games, AI, policies and Moscow bridge moved to Estonia; identities preserved')
        elif action == 'canary':
            assert not CANARY.exists(), 'Canary state already exists; clean it first'
            squad = await c._request('POST','/api/internal-squads',json={'name':'ArcVPN EE Migration Canary','inbounds':[i['uuid'] for i in ee['inbounds']]})
            user = await c._request('POST','/api/users',json={'username':'arc-ee-migration-20261025','status':'ACTIVE','trafficLimitBytes':200*1024**2,'trafficLimitStrategy':'NO_RESET','expireAt':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),'activeInternalSquads':[squad['uuid']]})
            def reality(tag, port):
                i = next(i for i in ee['config']['inbounds'] if i['tag'] == tag)
                r = i['streamSettings']['realitySettings']
                public = base64.urlsafe_b64encode(X25519PrivateKey.from_private_bytes(base64.urlsafe_b64decode(r['privateKey']+'=')).public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode().rstrip('=')
                return {'tag':'proxy','protocol':'vless','settings':{'vnext':[{'address':EE,'port':port,'users':[{'id':user['vlessUuid'],'encryption':'none','flow':'xtls-rprx-vision'}]}]},'streamSettings':{'network':'raw','security':'reality','realitySettings':{'serverName':'ee.arccnet.space','fingerprint':'firefox','publicKey':public,'shortId':r['shortIds'][0]}}}
            ordinary = reality('EE_1CHOST_VLESS_TCP',443)
            hy = {'tag':'proxy','protocol':'hysteria','settings':{'address':EE,'port':443,'version':2},'streamSettings':{'network':'hysteria','security':'tls','hysteriaSettings':{'version':2,'auth':user['vlessUuid']},'finalmask':{'quicParams':{'congestion':'bbr','debug':False}},'tlsSettings':{'serverName':'ee.arccnet.space','alpn':['h3'],'fingerprint':'firefox'}}}
            outbounds = {'ordinary':ordinary,'warp':reality(WARP,8444),'games':hy}
            for size in VARIANTS:
                edge = outbound(ordinary,size,'proxy')
                edge['streamSettings']['network'] = 'xhttp'
                edge['settings']['vnext'][0]['users'][0]['flow'] = ''
                outbounds['cdn-'+str(size)] = edge
                direct = copy.deepcopy(edge)
                direct['settings']['vnext'][0].update(address=EE,port=80)
                direct['streamSettings']['security'] = 'none'
                direct['streamSettings'].pop('tlsSettings',None)
                direct['streamSettings']['xhttpSettings']['host'] = 'origin.arccnet.space'
                outbounds['origin-'+str(size)] = direct
            save(CANARY,{'user_id':user['id'],'squad_uuid':squad['uuid'],'outbounds':outbounds})
            print('Private bounded migration canary prepared; no credentials printed')
        elif action == 'cleanup':
            v = json.loads(CANARY.read_text())
            await c._request('DELETE','/api/users/'+str(v['user_id']))
            await c._request('DELETE','/api/internal-squads/'+v['squad_uuid'])
            CANARY.rename(CANARY.with_suffix('.revoked.json'))
            print('Migration canary revoked')
    finally:
        await c.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action',choices=['prepare','publish','canary','cleanup'])
    asyncio.run(main(p.parse_args().action))
