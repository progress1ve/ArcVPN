"""Temporary owner-only comparisons on the ordinary Royale Reality endpoint."""

import copy
import json
import time
from pathlib import Path

from monitoring.royale_owner import OWNER, PUBLIC_NAME

STATE = Path(__file__).resolve().parents[1] / ".secrets/owner-reality-fingerprints.json"
VARIANTS = (
    ("🇳🇱 NL · Reality Chrome", "chrome"),
    ("🇳🇱 NL · Reality Safari", "safari"),
)


def apply(profiles, telegram_id):
    if telegram_id != OWNER:
        return profiles
    try:
        expiry = json.loads(STATE.read_text(encoding="utf-8"))["expires_at"]
    except (OSError, ValueError, TypeError, KeyError):
        return profiles
    if type(expiry) is not int or not 0 < expiry - time.time() <= 86460:
        return profiles

    source = next((p for p in profiles if p.get("remarks") == PUBLIC_NAME), None)
    if source is None:
        return profiles
    proxy_index = next((i for i, o in enumerate(source.get("outbounds", []))
                        if o.get("tag") == "proxy" and o.get("protocol") == "vless"), None)
    if proxy_index is None:
        return profiles
    stream = source["outbounds"][proxy_index].get("streamSettings", {})
    if (stream.get("security") != "reality"
            or stream.get("network") not in {"tcp", "raw"}
            or stream.get("realitySettings", {}).get("fingerprint") != "firefox"):
        return profiles

    names = {name for name, _ in VARIANTS}
    result = [p for p in profiles if p.get("remarks") not in names]
    for name, fingerprint in VARIANTS:
        profile = copy.deepcopy(source)
        profile["remarks"] = name
        profile["outbounds"][proxy_index]["streamSettings"]["realitySettings"]["fingerprint"] = fingerprint
        result.append(profile)
    return result
