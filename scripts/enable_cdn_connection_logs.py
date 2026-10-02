"""Scoped access metadata in container tmpfs; private panel rollback preserved."""
import asyncio
import copy
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from bot.services.friend_subscriptions import authority_server
from bot.services.panels.factory import create_panel_client


async def run():
    client = create_panel_client(authority_server())
    try:
        payload = await client._request('GET', '/api/config-profiles')
        profiles = [p for p in payload.get('configProfiles', [])
                    if any(i.get('tag') == 'EE_OWNER_DIRECT_XHTTP' for i in p.get('config', {}).get('inbounds', []))]
        if len(profiles) != 1:
            raise RuntimeError('Expected one Estonia profile')
        profile = profiles[0]
        backup = Path('.secrets') / ('cdn-access-before-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '.json')
        backup.parent.mkdir(exist_ok=True)
        backup.write_text(json.dumps(profile), encoding='utf-8'); backup.chmod(0o600)
        config = copy.deepcopy(profile['config'])
        config.setdefault('log', {}).update(access='/dev/shm/arcvpn-access.log', loglevel='error', error='none')
        await client._request('PATCH', '/api/config-profiles', json={'uuid': profile['uuid'], 'config': config})
        verified = await client._request('GET', '/api/config-profiles')
        same = next(p for p in verified['configProfiles'] if p['uuid'] == profile['uuid'])
        assert same['config']['log']['access'] == '/dev/shm/arcvpn-access.log'
        assert same['config']['inbounds'] == profile['config']['inbounds']
        assert same['config']['routing'] == profile['config']['routing']
        print('Access metadata configured; inbounds/routing unchanged; private rollback saved')
    finally:
        await client.close()


if __name__ == '__main__':
    logging.disable(logging.CRITICAL)
    asyncio.run(run())
