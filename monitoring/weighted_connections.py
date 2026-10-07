"""Xray-compatible weighted tickets with two observed real peers.

Tickets are cheap loopback handlers, not duplicated network probes. Each ticket
enters a health-aware preferred-peer balancer, then the other peer, then the
caller's existing fallback. Weights describe connection probabilities, not bytes.
"""
from math import gcd
from functools import reduce


def configure(profile, balancer, peers, fallback="block", namespace="weighted"):
    """Replace one balancer in place; peers is [(outbound_tag, positive_weight)]."""
    if not 1 <= len(peers) <= 2 or any(not isinstance(w, int) or not 1 <= w <= 100 for _, w in peers):
        raise ValueError("invalid_weighted_peers")
    divisor = reduce(gcd, (weight for _, weight in peers))
    routing = profile.setdefault("routing", {})
    groups, rules, tickets = [], [], []
    for index, (tag, weight) in enumerate(peers):
        preferred = f"{namespace}-preferred-{index}"
        reserve = f"{namespace}-reserve-{index}"
        reserve_entry = f"{namespace}-reserve-entry-{index}"
        for ticket in range(weight // divisor):
            tickets.append({"tag": f"{namespace}-ticket-{index}-{ticket:03d}",
                            "protocol": "loopback", "settings": {"inboundTag": preferred}})
        other = [peer for peer, _ in peers if peer != tag]
        preferred_fallback = reserve_entry if other else fallback
        groups.append({"tag": preferred, "selector": [tag], "fallbackTag": preferred_fallback,
                       "strategy": {"type": "leastPing"}})
        rules.append({"type": "field", "inboundTag": [preferred], "balancerTag": preferred})
        if other:
            tickets.append({"tag": reserve_entry, "protocol": "loopback", "settings": {"inboundTag": reserve}})
            groups.append({"tag": reserve, "selector": other, "fallbackTag": fallback,
                           "strategy": {"type": "leastPing"}})
            rules.append({"type": "field", "inboundTag": [reserve], "balancerTag": reserve})
    profile["outbounds"].extend(tickets)
    # Prefix selectors intentionally include tickets only, not reserve entries.
    original_tag = balancer["tag"]
    balancer.clear()
    balancer.update({"tag": original_tag, "selector": [namespace + "-ticket-"],
                     "strategy": {"type": "random"}})
    routing.setdefault("balancers", []).extend(groups)
    routing["rules"] = rules + routing.get("rules", [])
    return profile
