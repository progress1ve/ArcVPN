"""Prepare owner-approved Sweden CDN production authorization before publication."""
import asyncio,copy,json,os,sys
from pathlib import Path
sys.path.insert(0,'/root/ArcVPN')
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
from cdn_fallbacks import VARIANTS,settings,outbound
ROOT=Path('/root/ArcVPN/.secrets')
def items(d,k):return d.get(k,[]) if isinstance(d,dict) else d
def save(p,d):
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(d,f)
async def main():
 c=RemnawaveClient({**remnawave_authority_config(),'panel_write_mode':'production'})
 try:
  ps=items(await c._request('GET','/api/config-profiles'),'configProfiles');ns=items(await c._request('GET','/api/nodes'),'nodes');ss=items(await c._request('GET','/api/internal-squads'),'internalSquads')
  p=next(x for x in ps if x['name']=='ArcVPN Sweden HostUp');n=next(x for x in ns if x['name']==p['name']);lte=next(x for x in ss if x['name']=='ArcVPN LTE');test=next(x for x in ss if x['name']=='ArcVPN Sweden CDN Private Test')
  save(ROOT/'sweden-cdn-production-before.json',{'profile':p,'node':n,'lte':lte,'test':test})
  cfg=copy.deepcopy(p['config']);source=next(i for i in cfg['inbounds'] if i['tag']=='SE_CDN_TEST_24000')
  for size,v in VARIANTS.items():
   existing=next((i for i in cfg['inbounds'] if i['tag']==v['tag']),None)
   i=existing if existing else copy.deepcopy(source)
   i.update(tag=v['tag'],port=v['port'],listen='127.0.0.1');i['settings']['clients']=[]
   e=settings(size);e.pop('xmux',None);e.pop('uplinkChunkSize',None)
   i['streamSettings']['xhttpSettings']={'host':'','path':v['path'],'mode':'packet-up',**e,'serverMaxHeaderBytes':262144}
   if not existing:cfg['inbounds'].append(i)
  tags=[v['tag'] for v in VARIANTS.values()]
  cfg['routing']['rules'].insert(0,{'type':'field','inboundTag':tags,'network':'tcp,udp','outboundTag':'DIRECT'})
  updated=await c._request('PATCH','/api/config-profiles',json={'uuid':p['uuid'],'config':cfg})
  old={i['tag']:i['uuid'] for i in p['inbounds']};ids={i['tag']:i['uuid'] for i in updated['inbounds']}
  assert all(ids[t]==uid for t,uid in old.items()),'Identity changed'
  wanted=[ids[t] for t in tags]
  for squad in [lte,test]:
   active=[i['uuid'] if isinstance(i,dict) else i for i in squad['inbounds']]
   await c._request('PATCH','/api/internal-squads',json={'uuid':squad['uuid'],'inbounds':list(dict.fromkeys(active+wanted))})
  active=[i['uuid'] if isinstance(i,dict) else i for i in n['configProfile']['activeInbounds']]
  await c._request('PATCH','/api/nodes',json={'uuid':n['uuid'],'configProfile':{'activeConfigProfileUuid':p['uuid'],'activeInbounds':list(dict.fromkeys(active+wanted))}})
  state=json.loads((ROOT/'sweden-cdn-test-state.json').read_text());base=state['outbounds'][0]
  state['variants']=[{'size':size,**v} for size,v in VARIANTS.items()];state['outbounds']=[outbound(base,size,'proxy') for size in VARIANTS]
  (ROOT/'sweden-cdn-test-state.json').write_text(json.dumps(state));print(json.dumps({'authorized_variants':len(wanted),'existing_inbound_ids_preserved':True,'public_delivery_changed':False}))
 finally:await c.close()
asyncio.run(main())
