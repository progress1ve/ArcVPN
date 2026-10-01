from scripts.ops.prepare_finland_cdn_origin import prepare
import pytest

def test_origin_preserves_finland_and_adds_scoped_estonia_path():
    source='server {\n server_name fin.arccnet.space cdn-de.arccnet.space;\n location /api-fin {proxy_pass http://127.0.0.1:10001;}\n}'
    result=prepare(source)
    assert 'location /api-fin {proxy_pass http://127.0.0.1:10001;}' in result
    assert result.count('location /api-test')==1
    assert 'proxy_pass http://87.251.19.197:80;' in result
    assert prepare(result)==result

def test_unknown_config_is_not_overwritten():
    with pytest.raises(ValueError):prepare('server {location /api-fin {}}')
