"""Prepare hidden Sweden WARP/Hysteria2 paths, then publish after tunnel gates."""
import argparse,asyncio,base64,copy,json,os
from pathlib import Path
from datetime import datetime,timedelta,timezone
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config

ROOT=Path('/root/ArcVPN/.secrets')
STATE=ROOT/'sweden-special-state.json'
WARP='SE_HOSTUP_WARP_REALITY'
HY2='SE_HOSTUP_HYSTERIA2'
DOMAIN='se.arccnet.space'

def items(value,key):return value.get(key,[]) if isinstance(value,dict) else value

def save(path,data):
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:json.dump(data,f)

async def main(action):
    c=RemnawaveClient({**remnawave_authority_config(),'panel_write_mode':'production'})
    try:
        if action=='cleanup':
            state=json.loads(STATE.read_text())
            user=await c._request('GET','/api/users/by-username/arc-se-special-canary')
            await c._request('DELETE','/api/users/'+str(user['id']))
            print('Private Sweden special canary revoked');return
        if action=='rename':
            hosts=items(await c._request('GET','/api/hosts'),'hosts')
            state=json.loads(STATE.read_text())
            selected=[h for h in hosts if h['uuid'] in state['host_ids']]
            assert len(selected)==2
            for h in selected:
                name='🇸🇪 Нейросети 🤖' if h['port']==8444 else '🇸🇪 Игровой сервер 🎮'
                await c._request('PATCH','/api/hosts',json={'uuid':h['uuid'],'remark':name})
                print(name)
            return
        if action=='publish':
            state=json.loads(STATE.read_text())
            ss=items(await c._request('GET','/api/internal-squads'),'internalSquads')
            squad=next(s for s in ss if s['name']=='ArcVPN Staging')
            active=[i['uuid'] if isinstance(i,dict) else i for i in squad['inbounds']]
            await c._request('PATCH','/api/internal-squads',json={'uuid':squad['uuid'],'inbounds':list(dict.fromkeys(active+state['inbound_ids']))})
            for uid in state['host_ids']:
                await c._request('PATCH','/api/hosts',json={'uuid':uid,'isDisabled':False})
            print('Two Sweden special profiles published; existing authorization preserved');return
        assert not STATE.exists(),'Already prepared; review existing state'
        ps=items(await c._request('GET','/api/config-profiles'),'configProfiles')
        ns=items(await c._request('GET','/api/nodes'),'nodes')
        ss=items(await c._request('GET','/api/internal-squads'),'internalSquads')
        hs=items(await c._request('GET','/api/hosts'),'hosts')
        p=next(p for p in ps if p['name']=='ArcVPN Sweden HostUp')
        n=next(n for n in ns if n['address']=='136.148.220.228')
        ordinary=next(s for s in ss if s['name']=='ArcVPN Staging')
        if action=='recover':
            ids={i['tag']:i['uuid'] for i in p['inbounds']}
            wanted=[ids[t] for t in (WARP,HY2)]
            warp=next(i for i in p['config']['inbounds'] if i['tag']==WARP)
            host_ids=[h['uuid'] for h in hs if h.get('inbound',{}).get('configProfileInboundUuid') in wanted]
            assert len(host_ids)==2
            squad=next(s for s in ss if s['name']=='ArcVPN Sweden Special Canary')
            user=await c._request('GET','/api/users/by-username/arc-se-special-canary')
            r=warp['streamSettings']['realitySettings']
            private=base64.urlsafe_b64decode(r['privateKey']+'=')
            public=base64.urlsafe_b64encode(X25519PrivateKey.from_private_bytes(private).public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode().rstrip('=')
            warp_out={'tag':'proxy','protocol':'vless','settings':{'vnext':[{
                'address':DOMAIN,'port':8444,'users':[{'id':user['vlessUuid'],'encryption':'none','flow':'xtls-rprx-vision'}]}]},
                'streamSettings':{'network':'raw','security':'reality','realitySettings':{
                    'serverName':DOMAIN,'fingerprint':'firefox','publicKey':public,'shortId':r['shortIds'][0]}}}
            hy_out={'tag':'proxy','protocol':'hysteria','settings':{'address':DOMAIN,'port':443,'version':2},
                'streamSettings':{'network':'hysteria','security':'tls','hysteriaSettings':{'version':2,'auth':user['vlessUuid']},
                    'finalmask':{'quicParams':{'congestion':'bbr','debug':False}},
                    'tlsSettings':{'serverName':DOMAIN,'alpn':['h3'],'fingerprint':'firefox'}}}
            save(STATE,{'node_uuid':n['uuid'],'profile_uuid':p['uuid'],'inbound_ids':wanted,'host_ids':host_ids,
                'squad_uuid':squad['uuid'],'user_id':user['id'],'outbounds':[warp_out,hy_out]})
            print('Prepared objects recovered without duplicate creation');return
        save(ROOT/'sweden-special-before.json',{'profile':p,'node':n,'ordinary_squad':ordinary})
        cfg=copy.deepcopy(p['config'])
        source=next(i for i in cfg['inbounds'] if i['tag']=='SE_HOSTUP_VLESS_TCP')
        warp=copy.deepcopy(source);warp.update(tag=WARP,port=8444)
        warp['settings']['clients']=[]
        hy={'tag':HY2,'port':443,'listen':'0.0.0.0','protocol':'hysteria',
            'settings':{'clients':[],'version':2},
            'streamSettings':{'network':'hysteria','security':'tls',
                'finalmask':{'quicParams':{'debug':False,'congestion':'bbr'}},
                'tlsSettings':{'alpn':['h3'],'certificates':[{
                    'certificateFile':'/etc/letsencrypt/live/se.arccnet.space/fullchain.pem',
                    'keyFile':'/etc/letsencrypt/live/se.arccnet.space/privkey.pem'}]},
                'hysteriaSettings':{'version':2}}}
        assert all(i['tag'] not in (WARP,HY2) for i in cfg['inbounds'])
        cfg['inbounds'] += [warp,hy]
        cfg['outbounds'].append({'tag':'WARP','protocol':'socks','settings':{'servers':[{'address':'127.0.0.1','port':40000}]}})
        tags=[WARP,HY2]
        cfg['routing']['rules'][0:0]=[
            {'type':'field','inboundTag':tags,'ip':['geoip:private'],'outboundTag':'BLOCK'},
            {'type':'field','inboundTag':tags,'domain':['geosite:private'],'outboundTag':'BLOCK'},
            {'type':'field','inboundTag':tags,'protocol':['bittorrent'],'outboundTag':'BLOCK'},
            {'type':'field','inboundTag':[WARP],'network':'udp','outboundTag':'BLOCK'},
            {'type':'field','inboundTag':[WARP],'network':'tcp','outboundTag':'WARP'},
            {'type':'field','inboundTag':[HY2],'network':'tcp,udp','outboundTag':'DIRECT'}]
        updated=await c._request('PATCH','/api/config-profiles',json={'uuid':p['uuid'],'config':cfg})
        old={i['tag']:i['uuid'] for i in p['inbounds']};ids={i['tag']:i['uuid'] for i in updated['inbounds']}
        assert all(ids[t]==uid for t,uid in old.items()),'Existing inbound identity changed'
        wanted=[ids[t] for t in tags]
        active=[i['uuid'] if isinstance(i,dict) else i for i in n['configProfile']['activeInbounds']]
        await c._request('PATCH','/api/nodes',json={'uuid':n['uuid'],'configProfile':{
            'activeConfigProfileUuid':p['uuid'],'activeInbounds':list(dict.fromkeys(active+wanted))}})
        host_ids=[]
        for tag,remark,port,sni,security,alpn in [
                (WARP,'🇸🇪 Нейросети 🤖',8444,DOMAIN,'DEFAULT',None),
                (HY2,'🇸🇪 Игровой сервер 🎮',443,DOMAIN,'TLS','h3')]:
            h=await c._request('POST','/api/hosts',json={
                'address':DOMAIN,'port':port,'path':'','host':'','sni':sni,
                'fingerprint':'firefox','allowInsecure':False,'isDisabled':True,'isHidden':False,
                'nodes':[n['uuid']],'remark':remark,'securityLayer':security,'alpn':alpn,
                'inbound':{'configProfileUuid':p['uuid'],'configProfileInboundUuid':ids[tag]}})
            host_ids.append(h['uuid'])
        squad=await c._request('POST','/api/internal-squads',json={'name':'ArcVPN Sweden Special Canary','inbounds':wanted})
        user=await c._request('POST','/api/users',json={
            'username':'arc-se-special-canary','status':'ACTIVE','trafficLimitBytes':0,
            'trafficLimitStrategy':'NO_RESET','expireAt':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),
            'activeInternalSquads':[squad['uuid']]})
        r=warp['streamSettings']['realitySettings']
        private=base64.urlsafe_b64decode(r['privateKey']+'=')
        public=base64.urlsafe_b64encode(X25519PrivateKey.from_private_bytes(private).public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode().rstrip('=')
        warp_out={'tag':'proxy','protocol':'vless','settings':{'vnext':[{
            'address':DOMAIN,'port':8444,'users':[{'id':user['vlessUuid'],'encryption':'none','flow':'xtls-rprx-vision'}]}]},
            'streamSettings':{'network':'raw','security':'reality','realitySettings':{
                'serverName':DOMAIN,'fingerprint':'firefox','publicKey':public,'shortId':r['shortIds'][0]}}}
        hy_out={'tag':'proxy','protocol':'hysteria','settings':{'address':DOMAIN,'port':443,'version':2},
            'streamSettings':{'network':'hysteria','security':'tls','hysteriaSettings':{'version':2,'auth':user['vlessUuid']},
                'finalmask':{'quicParams':{'congestion':'bbr','debug':False}},
                'tlsSettings':{'serverName':DOMAIN,'alpn':['h3'],'fingerprint':'firefox'}}}
        save(STATE,{'node_uuid':n['uuid'],'profile_uuid':p['uuid'],'inbound_ids':wanted,'host_ids':host_ids,
                    'squad_uuid':squad['uuid'],'user_id':user['id'],'outbounds':[warp_out,hy_out]})
        print(json.dumps({'prepared':True,'hidden_profiles':2,'existing_inbound_ids_preserved':True}))
    finally:await c.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','recover','publish','cleanup','rename'])
    asyncio.run(main(parser.parse_args().action))
