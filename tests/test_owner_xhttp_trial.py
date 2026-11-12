import json
import time
from urllib.parse import parse_qs, urlsplit

from monitoring import owner_xhttp_trial as trial


def test_direct_xhttp_is_owner_only_and_preserves_existing_profiles(tmp_path, monkeypatch):
    state_path = tmp_path / 'trial.json'
    monkeypatch.setattr(trial, 'STATE', state_path)
    state = {
        'enabled': True, 'expires_at': int(time.time()) + 60,
        'uuid': '57c24a09-4e21-410e-a33c-5537841d262f',
        'path': '/arc-diag-' + 'a' * 32 + '/',
    }
    state_path.write_text(json.dumps(state), encoding='utf-8')
    source = {'remarks': trial.PUBLIC_NAME, 'outbounds': [
        {'tag': 'proxy', 'protocol': 'vless'}, {'tag': 'direct', 'protocol': 'freedom'},
    ], 'routing': {'rules': [{'outboundTag': 'proxy'}]}}
    original = [source]
    parse = lambda link, tag: {'link': link, 'tag': tag}
    result = trial.apply(original, trial.OWNER, parse)
    assert result[0] is source
    assert len(result) == 3
    assert len(original) == 1
    assert trial.apply(original, trial.OWNER + 1, parse) is original
    for profile, link in zip(result[1:], trial.links_for_owner(trial.OWNER).values()):
        parsed = urlsplit(link)
        assert parsed.hostname == trial.DOMAIN and parsed.port == trial.PORT
        assert profile['routing'] == source['routing']
        assert profile['outbounds'][0] == {'link': link, 'tag': 'proxy'}
        assert parse_qs(parsed.query)['mode'] == [trial.MODES[profile['remarks']]]
        assert parse_qs(parsed.query)['sni'] == [trial.DOMAIN]
    state_path.write_text(json.dumps({**state, 'expires_at': 0}), encoding='utf-8')
    assert not trial.links_for_owner(trial.OWNER)
