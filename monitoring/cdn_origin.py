"""Attribution for the verified origin of the existing public CDN."""
from monitoring.royale_owner import _read_state

LITHUANIA = '88.216.62.135'
ROYALE = '45.141.202.248'


def active_origin():
    state = _read_state() or {}
    return ROYALE if state.get('cdn_origin_confirmed') else LITHUANIA
