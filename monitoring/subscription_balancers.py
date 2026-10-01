"""Validated client subscription policies; never contain credentials."""
import copy
import hashlib
import json

STRATEGIES = {"leastLoad", "leastPing", "roundRobin", "random", "weightedUsers"}
NODES = {"fi": {"151.241.137.174", "fin.arccnet.space", "fin.arcnet.space"},
         "ee": {"87.251.19.197", "ee.arccnet.space", "est.arccnet.space"}}


def validate(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 20:
        raise ValueError("invalid_balancers")
    result, identifiers = [], set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("invalid_balancer")
        identifier = str(item.get("id", ""))
        raw_name = str(item.get("name", ""))
        name = raw_name.strip()
        kind = item.get("kind")
        members = item.get("members")
        strategy = item.get("strategy")
        fallback = item.get("fallback")
        if (not identifier.isascii() or not identifier.replace("-", "").isalnum()
                or len(identifier) > 40 or identifier in identifiers
                or not 1 <= len(name) <= 100 or any(ord(c) < 32 for c in raw_name)
                or kind not in {"auto", "youtube", "bypass"}
                or strategy not in STRATEGIES or fallback not in {"existing", "block"}
                or not isinstance(members, list) or not members or len(members) > 2
                or any(member not in NODES for member in members) or len(set(members)) != len(members)):
            raise ValueError("invalid_balancer")
        weights = item.get("weights") or {}
        if not isinstance(weights, dict) or any(
                not isinstance(weights.get(member, 1), int) or isinstance(weights.get(member, 1), bool)
                or not 1 <= weights.get(member, 1) <= 100 for member in members):
            raise ValueError("invalid_weights")
        identifiers.add(identifier)
        result.append({"id": identifier, "name": name, "kind": kind, "members": members,
                       "strategy": strategy, "fallback": fallback,
                       "weights": {member: weights.get(member, 1) for member in members}})
    if not any(item["kind"] == "auto" for item in result):
        raise ValueError("auto_required")
    return result


def digest(policy):
    return hashlib.sha256(json.dumps(policy, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def defaults():
    return [{"id": kind, "kind": kind, "name": name, "members": ["fi", "ee"],
             "weights": {"fi": 1, "ee": 1}, "strategy": "leastLoad", "fallback": "existing"}
            for kind, name in (("auto", "Автовыбор | Самый быстрый"),
                               ("youtube", "Ютуб без рекламы"), ("bypass", "Обход глушилок"))]


def apply(profiles, policy, addresses=None, user_id=None):
    """Modify only generated balancers, preserving manual profiles and identities.

    leastLoad weights are inverse latency costs, not promises of user percentages.
    Missing selected nodes fail closed instead of silently selecting another route.
    """
    if not policy:
        return profiles
    templates = {}
    manual = []
    for profile in profiles:
        name = profile.get("remarks", "")
        if "Автовыбор" in name:
            templates["auto"] = profile
        elif "Ютуб" in name:
            templates["youtube"] = profile
        elif "Обход" in name:
            templates.setdefault("bypass", profile)
        else:
            manual.append(profile)
    output = []
    for item in policy:
        template = templates.get(item["kind"])
        if template is None:
            continue  # Product entitlement did not generate this type.
        profile = copy.deepcopy(template)
        profile["remarks"] = item["name"]
        primary = profile["routing"]["balancers"][0]
        prefix = "proxy-youtube" if item["kind"] == "youtube" else "proxy-main"
        tags = {}
        for outbound in profile["outbounds"]:
            if not outbound.get("tag", "").startswith(prefix):
                continue
            peers = outbound.get("settings", {}).get("vnext", [])
            address = str(peers[0].get("address", "")).lower() if peers else ""
            for node, known_addresses in (addresses or NODES).items():
                if address in known_addresses:
                    tags[node] = outbound["tag"]
        selected = [tags[node] for node in item["members"] if node in tags]
        primary["selector"] = selected or ["unavailable-member"]
        # Selectors match prefixes in Xray: make every selected tag unambiguous.
        if item["fallback"] == "block" or len(selected) != len(item["members"]):
            primary["fallbackTag"] = "block"
        settings = copy.deepcopy(primary.get("strategy", {}).get("settings", {}))
        if item["strategy"] == "weightedUsers" and selected:
            available = [node for node in item["members"] if node in tags]
            total = sum(item["weights"][node] for node in available)
            slot = int(hashlib.sha256(f"{user_id}:{item['id']}".encode()).hexdigest(),16) % total
            preferred = available[-1]
            for node in available:
                slot -= item["weights"][node]
                if slot < 0:
                    preferred = node
                    break
            primary["selector"] = [tags[preferred]]
            others = [tags[node] for node in available if node != preferred]
            if others:
                fallback = primary.get("fallbackTag", "block")
                profile["outbounds"].append({"tag":"policy-fallback", "protocol":"loopback",
                                            "settings":{"inboundTag":"policy-fallback"}})
                primary["fallbackTag"] = "policy-fallback"
                profile["routing"]["balancers"].append({"tag":"policy-reserve", "selector":others,
                    "fallbackTag":fallback,"strategy":{"type":"leastLoad","settings":{"expected":1}}})
                profile["routing"]["rules"].insert(0,{"type":"field","inboundTag":["policy-fallback"],"balancerTag":"policy-reserve"})
            settings = {}
        elif item["strategy"] == "leastLoad":
            settings["costs"] = [{"match": tags[node], "regexp": False,
                                  "value": 1 / item["weights"][node]}
                                 for node in item["members"] if node in tags]
            settings["expected"] = len(selected) or 1
        else:
            settings = {}
        primary["strategy"] = {"type": "leastPing" if item["strategy"] == "weightedUsers" else item["strategy"], "settings": settings}
        output.append(profile)
    return output + manual
