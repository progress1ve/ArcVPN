"""Load the audited M3T RU-Direct policy for customer Xray profiles."""

import hashlib
import json
import logging
from pathlib import Path

STATE = Path(__file__).resolve().parents[1] / ".secrets/m3t-ru-direct.json"
# NNN706/M3T 98daeede14d5f88fc9c1c350ede83f9f1f0e9e75, routing object only.
POLICY_SHA256 = "60c5c4f9441129a0380331301d1010e965e967aab07eb01d7a4d80d5dce7b0bf"


def load_rules():
    """Return the pinned rules or let the renderer use its existing defaults."""
    try:
        raw = STATE.read_bytes()
    except FileNotFoundError:
        return []
    except OSError:
        logging.getLogger(__name__).warning("Could not read M3T routing policy")
        return []
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA256:
        logging.getLogger(__name__).warning("M3T routing policy digest mismatch")
        return []
    return json.loads(raw)["rules"]
