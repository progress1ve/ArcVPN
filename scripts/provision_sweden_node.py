"""Prepare hidden HostUp Sweden, then promote only after real tunnel gates.

Run on Poland. Node-generated key material arrives on stdin and stays remote.
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
try:
    from monitoring.weighted_connections import configure
except ModuleNotFoundError:
    from weighted_connections import configure  # reviewed staging copy

NAME = 'ArcVPN Sweden HostUp'
DOMAIN = 'se.arccnet.space'
TAGS = {'FI_1CHOST_VLESS_TCP': 'SE_HOSTUP_VLESS_TCP', 'FI_SS_BRIDGE': 'SE_SS_BRIDGE'}
STATE = ROOT / '.secrets/sweden-remnawave-state.json'
BACKUP = ROOT / '.secrets/sweden-migration-before.json'

def items(payload, key):
    value = payload.get('response', payload) if isinstance(payload, dict) else payload
    return value.get(key, []) if isinstance(value, dict) else value or []

def save(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f: json.dump(data, f)

async def snapshot(c):
    return {ep: items(await c._request('GET', '/api/' + ep), key) for ep, key in
            [('config-profiles','configProfiles'),('nodes','nodes'),('hosts','hosts'),('internal-squads','internalSquads')]}

async def main(mode):
    c = RemnawaveClient({**remnawave_authority_config(), 'panel_write_mode': 'production'})
    try:
        snap = await snapshot(c)
        if mode == 'resume':
            if STATE.exists():raise RuntimeError('State exists; do not resume twice')
            material=json.load(sys.stdin)
            profile=next(p for p in snap['config-profiles'] if p['name']==NAME)
            node=next(p for p in snap['nodes'] if p['name']==NAME)
            host=next(h for h in snap['hosts'] if h['remark']=='Швеция #1')
            squad=next(s for s in snap['internal-squads'] if s['name']=='ArcVPN Sweden Canary')
            user=await c._request('GET','/api/users/by-username/arc-se-canary')
            save(STATE,{'profile_uuid':profile['uuid'],'node_uuid':node['uuid'],'host_uuid':host['uuid'],
                'inbounds':{i['tag']:i['uuid'] for i in profile['inbounds']},
                'public_key':material['public_key'],'short_id':material['short_id'],
                'canary_squad_uuid':squad['uuid'],'canary_user_uuid':user['vlessUuid']})
            print(json.dumps({'resumed':True,'hidden':True}))
        elif mode == 'prepare':
            if STATE.exists() or any(p['name'] == NAME for p in snap['config-profiles']):
                raise RuntimeError('Sweden exists: inspect instead of rerunning prepare')
            save(BACKUP, snap)
            material = json.load(sys.stdin)
            fi = next(p for p in snap['config-profiles'] if p['name'] == 'ArcVPN Finland 1chost')
            cfg = copy.deepcopy(fi['config'])
            cfg['inbounds'] = [i for i in cfg['inbounds'] if i['tag'] in TAGS]
            for i in cfg['inbounds']:
                old = i['tag']; i['tag'] = TAGS[old]; i['settings']['clients'] = []
                if old == 'FI_1CHOST_VLESS_TCP':
                    i['streamSettings']['realitySettings'] = {'target':'127.0.0.1:8443','serverNames':[DOMAIN],
                        'privateKey':material['private_key'],'shortIds':[material['short_id']],'xver':0}
            for rule in cfg['routing']['rules']:
                if 'inboundTag' in rule:rule['inboundTag'] = [TAGS.get(t,t) for t in rule['inboundTag']]
            cfg['routing']['rules'] = [r for r in cfg['routing']['rules'] if
                'inboundTag' not in r or any(t in TAGS.values() for t in r['inboundTag'])]
            profile = await c._request('POST','/api/config-profiles',json={'name':NAME,'config':cfg})
            ids = {i['tag']:i['uuid'] for i in profile['inbounds']}
            node = await c._request('POST','/api/nodes',json={'name':NAME,'address':'136.148.220.228','port':22600,
                'configProfile':{'activeConfigProfileUuid':profile['uuid'],'activeInbounds':list(ids.values())},
                'isTrafficTrackingActive':False,'trafficLimitBytes':0,'notifyPercent':80,
                'trafficResetDay':7,'excludedInbounds':[],'countryCode':'SE','consumptionMultiplier':1.0})
            host = await c._request('POST','/api/hosts',json={'remark':'Швеция #1','address':DOMAIN,'port':443,
                'path':'','host':'','sni':DOMAIN,'alpn':None,'fingerprint':'firefox','allowInsecure':False,
                'isDisabled':True,'isHidden':False,'securityLayer':'DEFAULT','nodes':[node['uuid']],
                'inbound':{'configProfileUuid':profile['uuid'],'configProfileInboundUuid':ids['SE_HOSTUP_VLESS_TCP']}})
            bridge = next(s for s in snap['internal-squads'] if s['name'] == 'ArcVPN Managed Bridge')
            bridge_ids = [i['uuid'] for i in bridge['inbounds']]
            await c._request('PATCH','/api/internal-squads',json={'uuid':bridge['uuid'],
                'inbounds':list(dict.fromkeys(bridge_ids+[ids['SE_SS_BRIDGE']]))})
            canary_squad = await c._request('POST','/api/internal-squads',json={'name':'ArcVPN Sweden Canary',
                'inbounds':[ids['SE_HOSTUP_VLESS_TCP']]})
            user = await c._request('POST','/api/users',json={'username':'arc-se-canary','status':'ACTIVE',
                'trafficLimitBytes':0,'trafficLimitStrategy':'NO_RESET','expireAt':'2026-10-09T00:00:00Z',
                'activeInternalSquads':[canary_squad['uuid']]})
            secret = (await c._request('GET','/api/keygen'))['secretKey']
            save(ROOT/'.secrets/sweden-node-secret.json',{'secret':secret})
            save(STATE,{'profile_uuid':profile['uuid'],'node_uuid':node['uuid'],'host_uuid':host['uuid'],
                'inbounds':ids,'public_key':material['public_key'],'short_id':material['short_id'],
                'canary_squad_uuid':canary_squad['uuid'],'canary_user_uuid':user['vlessUuid']})
            print(json.dumps({'prepared':True,'hidden':True,'inbounds':len(ids)}))
        elif mode == 'promote':
            state = json.loads(STATE.read_text())
            node = next(n for n in snap['nodes'] if n['uuid'] == state['node_uuid'])
            if not node.get('isConnected'):raise RuntimeError('Sweden not connected')
            fi = next(p for p in snap['config-profiles'] if p['name'] == 'ArcVPN Finland 1chost')
            fi_tcp = next(i['uuid'] for i in fi['inbounds'] if i['tag']=='FI_1CHOST_VLESS_TCP')
            for squad in snap['internal-squads']:
                old = [i['uuid'] for i in squad['inbounds']]
                if fi_tcp in old:
                    await c._request('PATCH','/api/internal-squads',json={'uuid':squad['uuid'],
                        'inbounds':list(dict.fromkeys(old+[state['inbounds']['SE_HOSTUP_VLESS_TCP']]))})
            # Existing Moscow SS outbound contains service authorization; clone
            # it only server-side, preserving the official managed bridge user.
            ru = next(p for p in snap['config-profiles'] if p['name']=='ArcVPN Moscow Bridge')
            cfg = copy.deepcopy(ru['config'])
            outbound = copy.deepcopy(next(o for o in cfg['outbounds'] if o['tag']=='FI_BRIDGE'))
            outbound['tag']='SE_BRIDGE';outbound['settings']['servers'][0]['address']=DOMAIN
            cfg['outbounds']=[o for o in cfg['outbounds'] if o['tag'] not in {'FI_BRIDGE','SE_BRIDGE'}]+[outbound]
            cfg['observatory']={'subjectSelector':['SE_BRIDGE','EE_BRIDGE'],
                'probeURL':'https://www.gstatic.com/generate_204','probeInterval':'10s','enableConcurrency':True}
            balancer=next(b for b in cfg['routing']['balancers'] if b['tag']=='EU_BRIDGE')
            configure(cfg,balancer,[('SE_BRIDGE',61),('EE_BRIDGE',39)],'BLOCK','weighted-ru')
            updated=await c._request('PATCH','/api/config-profiles',json={'uuid':ru['uuid'],'name':ru['name'],'config':cfg})
            if {i['tag']:i['uuid'] for i in updated['inbounds']} != {i['tag']:i['uuid'] for i in ru['inbounds']}:
                raise RuntimeError('Unexpected inbound identity change: restore saved profile')
            await c._request('PATCH','/api/hosts',json={'uuid':state['host_uuid'],'isDisabled':False})
            for host in snap['hosts']:
                if (host.get('inbound') or {}).get('configProfileUuid')==fi['uuid']:
                    await c._request('PATCH','/api/hosts',json={'uuid':host['uuid'],'isDisabled':True})
            print(json.dumps({'promoted':True,'weights':{'se':61,'ee':39},'finland_hosts_disabled':True}))
        elif mode == 'catalog':
            from database.connection import get_db
            from monitoring.subscription_balancers import defaults, validate
            import hashlib
            with get_db() as db:
                previous={'settings':[dict(r) for r in db.execute("SELECT * FROM settings WHERE key IN ('subscription_balancers_live','subscription_balancers_draft')")],
                    'catalog':[dict(r) for r in db.execute('SELECT * FROM subscription_profile_overrides')]}
                backup=ROOT/'.secrets/sweden-catalog-before.json'
                if backup.exists():raise RuntimeError('Catalog already applied: inspect before retry')
                cols=[r['name'] for r in db.execute('PRAGMA table_info(vpn_keys)')]
                identities=[col for col in ['id','user_id','sub_id','client_uuid','remnawave_uuid'] if col in cols]
                rows=[dict(r) for r in db.execute('SELECT '+','.join(identities)+' FROM vpn_keys ORDER BY id')]
                previous['identities_sha256']=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
                save(backup,previous)
                policy=validate(defaults())
                for key in ['subscription_balancers_live','subscription_balancers_draft']:
                    db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                        (key,json.dumps(policy,ensure_ascii=False)))
                for source,label,position,enabled,auto in [
                    ('Ютуб без рекламы','Ютуб без рекламы',0,1,1),('Швеция','Швеция',1,1,1),
                    ('Эстония #1','Эстония',2,1,1),('Эстония','Эстония',2,1,1),('Эстония #2','Эстония #2',20,0,0),
                    ('Германия','Германия',3,1,0),('Польша','Польша',4,1,0),('Нидерланды','Нидерланды',5,1,0),
                    ('Финляндия','Финляндия',6,1,0)]:
                    db.execute('INSERT INTO subscription_profile_overrides(source_name,display_name,sort_order,enabled,include_in_auto) VALUES(?,?,?,?,?) '
                        'ON CONFLICT(source_name) DO UPDATE SET display_name=excluded.display_name,sort_order=excluded.sort_order,enabled=excluded.enabled,include_in_auto=excluded.include_in_auto',
                        (source,label,position,enabled,auto))
                after=[dict(r) for r in db.execute('SELECT '+','.join(identities)+' FROM vpn_keys ORDER BY id')]
                assert previous['identities_sha256']==hashlib.sha256(json.dumps(after,sort_keys=True).encode()).hexdigest()
            print(json.dumps({'catalog_published':True,'balancers':len(policy),'identities_unchanged':True}))
    finally:await c.close()

if __name__=='__main__':asyncio.run(main(sys.argv[1]))
