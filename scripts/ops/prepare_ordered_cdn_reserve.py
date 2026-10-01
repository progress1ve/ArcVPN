"""Control-plane preparation for the explicitly approved two-tier CDN fallback."""
import asyncio
import copy
import json
import os
from pathlib import Path
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config

def items(p,k):
    r=p.get('response',p) if isinstance(p,dict) else p
    return r.get(k,[]) if isinstance(r,dict) else r

async def main():
    c=RemnawaveClient({**remnawave_authority_config(),'panel_write_mode':'production'})
    try:
        ps=items(await c._request('GET','/api/config-profiles'),'configProfiles')
        ns=items(await c._request('GET','/api/nodes'),'nodes')
        ss=items(await c._request('GET','/api/internal-squads'),'internalSquads')
        p=next(x for x in ps if x['name']=='ArcVPN Estonia 1chost')
        n=next(x for x in ns if x['name']=='ArcVPN Estonia 1chost')
        squad=next(x for x in ss if x['name']=='ArcVPN LTE')
        cfg=copy.deepcopy(p['config'])
        tag='EE_CDN_RESERVE_XHTTP'
        assert not any(i['tag']==tag for i in cfg['inbounds']), 'Reserve already exists; inspect before retry'
        source=next(i for i in cfg['inbounds'] if i['tag']=='EE_OWNER_DIRECT_XHTTP')
        new=copy.deepcopy(source);new.update(tag=tag,listen='127.0.0.1',port=10003)
        new['settings']['clients']=[]
        xs=new['streamSettings']['xhttpSettings']
        xs.update(path='/api-ee-reserve',uplinkDataKey='X-Request-Trace',
                  scMaxEachPostBytes=24000,serverMaxHeaderBytes=65536)
        cfg['inbounds'].append(new)
        rules=cfg['routing']['rules'];pos=next(i for i,r in enumerate(rules) if r.get('outboundTag')=='YOUTUBE_RU')
        rules.insert(pos,{'type':'field','inboundTag':[tag],'domain':['geosite:youtube'],
                          'network':'tcp,udp','outboundTag':'DIRECT'})
        backup=Path('/root/ArcVPN/.secrets/ordered-cdn-reserve-before.json')
        fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:json.dump({'profile':p,'node':n,'squad':squad},f)
        await c._request('PATCH','/api/config-profiles',json={'uuid':p['uuid'],'config':cfg})
        pp=next(x for x in items(await c._request('GET','/api/config-profiles'),'configProfiles') if x['uuid']==p['uuid'])
        wanted=[i['uuid'] for i in pp['inbounds'] if i['tag'] in {tag,'EE_OWNER_DIRECT_XHTTP'}]
        authorized=[i['uuid'] if isinstance(i,dict) else i for i in squad.get('inbounds',[])]
        await c._request('PATCH','/api/internal-squads',json={'uuid':squad['uuid'],'inbounds':list(dict.fromkeys(authorized+wanted))})
        active=[i['uuid'] if isinstance(i,dict) else i for i in n['configProfile']['activeInbounds']]
        await c._request('PATCH','/api/nodes',json={'uuid':n['uuid'],'configProfile':{
            'activeConfigProfileUuid':p['uuid'],'activeInbounds':list(dict.fromkeys(active+wanted))}})
        print('Ordered CDN inbounds authorized for existing LTE users; no publication flag enabled')
    finally:await c.close()

if __name__=='__main__':asyncio.run(main())
