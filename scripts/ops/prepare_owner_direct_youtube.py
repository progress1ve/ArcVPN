"""Run on control plane: private owner XHTTP canary with direct YouTube egress."""
import asyncio
import copy
import json
import os
import urllib.parse
from pathlib import Path
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
import subscription_api as a
from database.connection import get_db

TAG = 'FI_OWNER_DIRECT_XHTTP'
SQUAD = 'ArcVPN Owner Direct Canary'
def items(p,k):
    r=p.get('response',p) if isinstance(p,dict) else p
    return r.get(k,[]) if isinstance(r,dict) else r

async def main():
    c=RemnawaveClient({**remnawave_authority_config(),'panel_write_mode':'production'})
    try:
        with get_db() as db:
            row=db.execute("SELECT k.sub_id FROM vpn_keys k JOIN users u ON u.id=k.user_id WHERE lower(u.username)='progressive_dev' AND k.expires_at>datetime('now') ORDER BY k.expires_at DESC LIMIT 1").fetchone()
        key=a.get_active_key_by_subscription_id(row['sub_id'])
        links=await a._native_remnawave_links(key)
        link=next(v for v in links if urllib.parse.urlsplit(v).hostname=='cdn-de.arccnet.space' and urllib.parse.parse_qs(urllib.parse.urlsplit(v).query).get('path')==['/api-fin'])
        owner=await c.get_user_by_vless_uuid(urllib.parse.urlsplit(link).username)
        if not owner: raise RuntimeError('Owner panel identity not found')
        ps=items(await c._request('GET','/api/config-profiles'),'configProfiles')
        ns=items(await c._request('GET','/api/nodes'),'nodes')
        ss=items(await c._request('GET','/api/internal-squads'),'internalSquads')
        p=next(x for x in ps if x['name']=='ArcVPN Finland 1chost')
        n=next(x for x in ns if x['name']=='ArcVPN Finland 1chost')
        cfg=copy.deepcopy(p['config'])
        if any(i['tag']==TAG for i in cfg['inbounds']): raise RuntimeError('Canary already exists; inspect before retry')
        source=next(i for i in cfg['inbounds'] if i['tag']=='FI_1CHOST_LTE_XHTTP')
        new=copy.deepcopy(source);new.update(tag=TAG,listen='127.0.0.1',port=10002)
        new['settings']['clients']=[]
        new['streamSettings']['xhttpSettings']['path']='/api-fin-direct'
        cfg['inbounds'].append(new)
        rules=cfg['routing']['rules']
        pos=next(i for i,r in enumerate(rules) if r.get('outboundTag')=='YOUTUBE_RU')
        rules.insert(pos,{'type':'field','inboundTag':[TAG],'domain':['geosite:youtube'],'network':'tcp,udp','outboundTag':'DIRECT'})
        backup=Path('/root/ArcVPN/.secrets/owner-direct-youtube-before.json')
        fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:json.dump({'profile':p,'node':n,'owner':owner},f)
        await c._request('PATCH','/api/config-profiles',json={'uuid':p['uuid'],'config':cfg})
        refreshed=items(await c._request('GET','/api/config-profiles'),'configProfiles')
        pp=next(x for x in refreshed if x['uuid']==p['uuid'])
        iid=next(i['uuid'] for i in pp['inbounds'] if i['tag']==TAG)
        squad=await c._request('POST','/api/internal-squads',json={'name':SQUAD,'inbounds':[iid]})
        squad=squad.get('response',squad)
        active=[i['uuid'] if isinstance(i,dict) else i for i in owner.get('activeInternalSquads',[])]
        await c._request('PATCH','/api/users',json={'id':owner['id'],'activeInternalSquads':active+[squad['uuid']]})
        ids=[i['uuid'] if isinstance(i,dict) else i for i in n['configProfile']['activeInbounds']]
        await c._request('PATCH','/api/nodes',json={'uuid':n['uuid'],'configProfile':{'activeConfigProfileUuid':p['uuid'],'activeInbounds':ids+[iid]}})
        print('Private owner canary authorized and activated; no published Host created. Existing YouTube rule preserved.')
    finally: await c.close()

if __name__=='__main__':asyncio.run(main())
