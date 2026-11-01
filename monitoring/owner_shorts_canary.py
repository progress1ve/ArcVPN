"""Time-limited owner-only Shorts A/B; never modifies ordinary profiles."""
import copy
import json
import time
from pathlib import Path

STATE = Path(__file__).resolve().parents[1] / '.secrets/shorts-canary-20261101.json'
OWNER = 2075630349


def apply(profiles, telegram_id):
    if int(telegram_id) != OWNER:
        return profiles
    try:
        state = json.loads(STATE.read_text())
        if not state.get('enabled') or time.time() >= state['expires_at']:
            return profiles
        source = next(p for p in profiles if p.get('remarks') == '🇸🇪 Швеция')
        result = list(profiles)
        for name, port, tcp_only in [
            ('🧪 Shorts · zapret', state['on_port'], False),
            ('🧪 Shorts · без zapret', state['off_port'], False),
            ('🧪 Shorts · без QUIC', state['on_port'], True),
        ]:
            p = copy.deepcopy(source)
            p['remarks'] = name
            transport = next(o for o in p['outbounds'] if o.get('protocol') == 'vless')
            bridge = {'tag': 'shorts-ru', 'protocol': 'shadowsocks',
                      'settings': {'servers': [{'address': state['host'], 'port': port,
                                  'method': state['method'], 'password': state['password']}]},
                      'streamSettings': {'network': 'tcp', 'sockopt': {'dialerProxy': transport['tag']}}}
            p['outbounds'].append(bridge)
            rules = [{'type': 'field', 'domain': ['geosite:youtube'],
                      'network': 'tcp,udp', 'outboundTag': 'shorts-ru'}]
            if tcp_only:
                p['outbounds'].append({'tag': 'shorts-reject-quic', 'protocol': 'blackhole', 'settings': {}})
                rules.insert(0, {'type': 'field', 'network': 'udp', 'port': '443',
                                 'outboundTag': 'shorts-reject-quic'})
            p.setdefault('routing', {}).setdefault('rules', [])[0:0] = rules
            result.append(p)
        return result
    except (OSError, ValueError, KeyError, StopIteration, TypeError):
        return profiles
