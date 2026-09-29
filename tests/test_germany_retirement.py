import urllib.parse
from unittest.mock import patch
import subscription_api as api


def test_retired_germany_and_alias_endpoints_cannot_leak_but_cdn_remains():
    links = [
        "vless://test@de.arccnet.space:443#Poland",
        "vless://test@87.121.47.203:443#Unknown",
        "vless://test@95.85.249.187:443#Old",
        "vless://test@example.com:443#Germany",
        "vless://test@de.arccnet.space:443",
        "vless://test@ee.arccnet.space:443#Эстония",
        "vless://test@cdn-de.arccnet.space:443?type=xhttp&path=%2Fapi-test#Лучший%20обход",
    ]
    with patch.object(api, "_catalog_overrides", return_value={}):
        result = api._apply_subscription_catalog(links)
    assert {urllib.parse.urlsplit(x).hostname for x in result} == {"ee.arccnet.space", "cdn-de.arccnet.space"}
    assert all(source != "Германия" for _, source in api.TEMPORARY_LOCATION_ALIASES)
