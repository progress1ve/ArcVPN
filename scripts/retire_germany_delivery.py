"""Retire returned DE delivery; rebind unchanged CDN host to managed EE."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
from scripts.provision_germany_node import items


async def run(apply=False):
    c = RemnawaveClient({**remnawave_authority_config(), "panel_write_mode": "production"})
    try:
        profiles = items(await c._request("GET", "/api/config-profiles"), "configProfiles")
        hosts = items(await c._request("GET", "/api/hosts"), "hosts")
        nodes = items(await c._request("GET", "/api/nodes"), "nodes")
        ee = next(p for p in profiles if p["name"] == "ArcVPN Estonia 1chost")
        node = next(n for n in nodes if n["name"] == "ArcVPN Estonia 1chost")
        if not node.get("isConnected"):
            raise RuntimeError("Estonia disconnected; refuse retirement cutover")
        inbound = next(i for i in ee["inbounds"] if "LTE" in i["tag"] and "XHTTP" in i["tag"])
        de = next(p for p in profiles if p["name"] == "ArcVPN Germany 1chost")
        ru = next(p for p in profiles if p["name"] == "ArcVPN Moscow Bridge")
        cdn = [h for h in hosts if h.get("address") == "cdn-de.arccnet.space" and h.get("path") == "/api-test"]
        if len(cdn) != 1:
            raise RuntimeError("Expected exactly one managed CDN /api-test host")
        retired = [h for h in hosts if (h.get("inbound", {}).get("configProfileUuid") == de["uuid"] or h.get("address") in {"de.arccnet.space", "87.121.47.203", "95.85.249.187"}) and h not in cdn]
        result = {"apply": apply, "retired_host_count": len(retired), "cdn_target": "Estonia", "identifiers_changed": False}
        if not apply:
            return result
        backup = ROOT / "backups" / "germany-retirement-before.json"
        if backup.exists():
            raise RuntimeError("Retirement backup exists; inspect before retry")
        backup.parent.mkdir(exist_ok=True)
        with backup.open("x", encoding="utf-8") as f:
            backup.chmod(0o600)
            json.dump({"hosts": hosts, "moscow": ru}, f)
        await c._request("PATCH", "/api/hosts", json={"uuid": cdn[0]["uuid"], "nodes": [node["uuid"]], "inbound": {"configProfileUuid": ee["uuid"], "configProfileInboundUuid": inbound["uuid"]}})
        for h in retired:
            await c._request("PATCH", "/api/hosts", json={"uuid": h["uuid"], "isDisabled": True})
        cfg = ru["config"]
        cfg["outbounds"] = [o for o in cfg["outbounds"] if o.get("tag") != "DE_BRIDGE"]
        for b in cfg.get("routing", {}).get("balancers", []):
            if b.get("tag") == "EU_BRIDGE":
                b["selector"] = ["EE_BRIDGE"]
        old = {i["uuid"]: i["tag"] for i in ru["inbounds"]}
        squads = items(await c._request("GET", "/api/internal-squads"), "internalSquads")
        updated = await c._request("PATCH", "/api/config-profiles", json={"uuid": ru["uuid"], "name": ru["name"], "config": cfg})
        new = {i["tag"]: i["uuid"] for i in updated["inbounds"]}
        ru_node = next(n for n in nodes if n["name"] == "ArcVPN Moscow Bridge")
        await c._request("PATCH", "/api/nodes", json={"uuid": ru_node["uuid"], "configProfile": {"activeConfigProfileUuid": ru["uuid"], "activeInbounds": list(new.values())}})
        for s in squads:
            before = [i["uuid"] for i in s.get("inbounds", [])]
            after = [new[old[i]] if i in old else i for i in before]
            if before != after:
                await c._request("PATCH", "/api/internal-squads", json={"uuid": s["uuid"], "inbounds": after})
        for h in hosts:
            ref = h.get("inbound") or {}
            previous = ref.get("configProfileInboundUuid")
            if previous in old and new[old[previous]] != previous:
                await c._request("PATCH", "/api/hosts", json={"uuid": h["uuid"], "inbound": {"configProfileUuid": ru["uuid"], "configProfileInboundUuid": new[old[previous]]}})
        return result
    finally:
        await c.close()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run("--apply" in sys.argv))))
