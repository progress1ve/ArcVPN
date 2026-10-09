"""Retire returned Finland nodes without contacting the returned server."""
import asyncio,json
from scripts.ops.provision_sweden_special_profiles import RemnawaveClient,remnawave_authority_config,items,save,ROOT
async def main():
 c=RemnawaveClient({**remnawave_authority_config(),'panel_write_mode':'production'})
 try:
  nodes=items(await c._request('GET','/api/nodes'),'nodes')
  hosts=items(await c._request('GET','/api/hosts'),'hosts')
  retired=[n for n in nodes if str(n.get('address','')).lower() in {'fin.arccnet.space','151.241.137.174'}]
  removed=[h for h in hosts if str(h.get('address','')).lower() in {'fin.arccnet.space','151.241.137.174'} or 'Финляндия' in h.get('remark','')]
  assert all(h.get('isDisabled') for h in removed),'Finland still has an enabled Host; inspect dependencies'
  snapshot=ROOT/'finland-returned-panel-before.json'
  if not snapshot.exists():save(snapshot,{'nodes':retired,'hosts':removed})
  for h in removed:await c._request('DELETE','/api/hosts/'+h['uuid'])
  for n in retired:await c._request('DELETE','/api/nodes/'+n['uuid'])
  print(json.dumps({'removed_nodes':len(retired),'removed_disabled_hosts':len(removed)}))
 finally:await c.close()
if __name__=='__main__':asyncio.run(main())
