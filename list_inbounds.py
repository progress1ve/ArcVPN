import asyncio, sys, json
sys.path.insert(0, '/root/ArcVPN')
from bot.services.panels.xui import XUIClient

async def main():
    c = XUIClient('http://127.0.0.1:2082', 'hUGKQISiDW', '2aDnyGFo9y')
    await c.connect()
    inbs = await c.list_inbounds()
    print(json.dumps(inbs, indent=2, ensure_ascii=False))
    await c.close()

asyncio.run(main())
