"""Write restricted canary artifacts from live panel; no credentials in output."""
import asyncio
import copy
import json
import sqlite3
import sys
import urllib.parse
from pathlib import Path

ROOT = Path('/root/ArcVPN')
sys.path.insert(0, str(ROOT))
import subscription_api as api
from database.connection import DB_PATH
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
from scripts.provision_germany_node import items

def write(name, data):
    p = Path('/opt/arcvpn/staging') / name
    with p.open('w') as f:
        p.chmod(0o600)
        json.dump(data, f)

def config(outbound):
    return {'log': {'loglevel': 'none'}, 'inbounds': [{
        'listen': '127.0.0.1', 'port': 18084, 'protocol': 'socks',
        'settings': {'auth': 'noauth'}}], 'outbounds': [outbound]}

async def run():
    c = RemnawaveClient(remnawave_authority_config())
    try:
        ps = items(await c._request('GET', '/api/config-profiles'), 'configProfiles')
        fi = next(p for p in ps if p['name'] == 'ArcVPN Finland 1chost')
        ru = next(p for p in ps if p['name'] == 'ArcVPN Moscow Bridge')
        outward = copy.deepcopy(next(o for o in fi['config']['outbounds'] if o['tag'] == 'YOUTUBE_RU'))
        inward = copy.deepcopy(next(o for o in ru['config']['outbounds'] if o['tag'] == 'FI_BRIDGE'))
        inward['settings']['servers'][0]['address'] = '151.241.137.174'
        write('fi-to-ru-canary.json', config(outward))
        write('ru-to-fi-canary.json', config(inward))
        with sqlite3.connect(str(DB_PATH)) as db:
            rows = db.execute("SELECT sub_id FROM vpn_keys WHERE expires_at>datetime('now') AND sub_id IS NOT NULL ORDER BY last_online_at DESC LIMIT 20").fetchall()
        for (sid,) in rows:
            key = api.get_active_key_by_subscription_id(sid)
            if not key:
                continue
            links = await api._native_remnawave_links(key)
            link = next((v for v in links if urllib.parse.urlsplit(v).hostname == 'fin.arccnet.space'
                         and urllib.parse.urlsplit(v).port == 443), None)
            if link:
                out = api._json_outbound_from_share_link(link, 'proxy')
                out['settings']['vnext'][0]['address'] = '151.241.137.174'
                write('fi-reality-canary.json', config(out))
                print('Prepared reciprocal bridge and managed Reality canaries')
                return
        raise RuntimeError('No managed Finland canary link; inspect host binding')
    finally:
        await c.close()

if __name__ == '__main__':
    asyncio.run(run())
