from urllib.parse import quote, unquote, urlsplit

from monitoring import restored_peers as m
from monitoring.royale_owner import PUBLIC_NAME


def test_retirement_and_sweden_alias():
    nl = {'remarks': PUBLIC_NAME, 'outbounds': [{'tag': 'proxy'}]}
    auto = {'remarks': 'Автовыбор'}
    profiles = [nl, auto, {'remarks': 'Литва XHTTP'}, {'remarks': m.SWEDEN}]
    result = m.apply(profiles)
    assert result == [nl, {**nl, 'remarks': m.SWEDEN}, auto]
    assert result[1]['outbounds'] is not nl['outbounds']
    assert m.apply(result) == result

    link = 'vless://same@nl.example:443?security=reality#' + quote(PUBLIC_NAME)
    links = m.apply_links([link, 'vless://same@88.216.62.135:443#legacy'])
    assert len(links) == 2
    alias = urlsplit(links[1])
    assert alias.username == 'same' and alias.hostname == 'nl.example'
    assert unquote(alias.fragment) == m.SWEDEN
