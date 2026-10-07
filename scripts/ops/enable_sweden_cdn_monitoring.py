"""Enable bounded RAM access classification on the current Sweden profile only."""
import asyncio, copy, json, os
from pathlib import Path
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config

async def main():
    c=RemnawaveClient({**remnawave_authority_config(), 'panel_write_mode':'production'})
    try:
        ps=await c._request('GET','/api/config-profiles')
        ps=ps.get('configProfiles',[]) if isinstance(ps,dict) else ps
        p=next(p for p in ps if p['name']=='ArcVPN Sweden HostUp')
        cfg=copy.deepcopy(p['config'])
        cfg.setdefault('log',{}).update(loglevel='warning', access='/dev/shm/arcvpn-access.log')
        if cfg == p['config']:
            print('Sweden RAM logging already enabled'); return
        snapshot=Path('/root/ArcVPN/.secrets/sweden-admin-monitoring-before.json')
        with os.fdopen(os.open(snapshot,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
            json.dump(p,f)
        updated=await c._request('PATCH','/api/config-profiles',json={'uuid':p['uuid'],'config':cfg})
        assert {i['tag']:i['uuid'] for i in p['inbounds']} == {i['tag']:i['uuid'] for i in updated['inbounds']}
        print('Sweden RAM logging enabled; inbound identities preserved')
    finally: await c.close()

async def retire_estonia_access_log():
    """The retired collector must not leave an unbounded RAM log behind."""
    c=RemnawaveClient({**remnawave_authority_config(), 'panel_write_mode':'production'})
    try:
        ps=await c._request('GET','/api/config-profiles')
        ps=ps.get('configProfiles',[]) if isinstance(ps,dict) else ps
        p=next(p for p in ps if p['name']=='ArcVPN Estonia 1chost')
        cfg=copy.deepcopy(p['config'])
        if cfg.get('log',{}).get('access') != '/dev/shm/arcvpn-access.log':
            print('Estonia collector log already disabled'); return
        with os.fdopen(os.open('/root/ArcVPN/.secrets/estonia-admin-monitoring-before.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
            json.dump(p,f)
        cfg['log']['access']='none'
        updated=await c._request('PATCH','/api/config-profiles',json={'uuid':p['uuid'],'config':cfg})
        assert {i['tag']:i['uuid'] for i in p['inbounds']} == {i['tag']:i['uuid'] for i in updated['inbounds']}
        print('Estonia collector log disabled; inbound identities preserved')
    finally: await c.close()

async def setup():
    await main()
    await retire_estonia_access_log()

if __name__ == '__main__': asyncio.run(setup())
