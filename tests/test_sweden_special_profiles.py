import json, urllib.parse
import subscription_api as api
from test_remnawave_native_subscription import _key


def links():
    base='vless://test@se.arccnet.space:{port}?security=reality#'
    return [base.format(port=8444)+urllib.parse.quote('🇸🇪 '+api.SWEDEN_AI_NAME),
            'hysteria2://test@se.arccnet.space:443?sni=se.arccnet.space#'+urllib.parse.quote('🇸🇪 '+api.SWEDEN_GAMES_NAME),
            base.format(port=443)+urllib.parse.quote('🇸🇪 Швеция'),
            'vless://test@ee.arccnet.space:443?security=reality#'+urllib.parse.quote('🇪🇪 Эстония')]


def test_manual_special_names_order_and_balancer_exclusion(monkeypatch):
    monkeypatch.setattr(api,'_catalog_overrides',lambda:{})
    prepared=api._build_happ_json_subscription(_key(),'\n'.join(links()))
    profiles=json.loads(prepared);names=[p['remarks'] for p in profiles]
    i=names.index('🇳🇱 Нидерланды')
    assert names[i+1:i+3]==['🇸🇪 '+n for n in api.SWEDEN_SPECIAL_NAMES]
    special=profiles[i+1:i+3]
    assert special[0]['outbounds'][0]['settings']['vnext'][0]['port']==8444
    assert special[1]['outbounds'][0]['protocol']=='hysteria'
    assert special[1]['outbounds'][0]['streamSettings']['tlsSettings']['serverName']=='se.arccnet.space'
    for p in profiles:
        if p.get('routing',{}).get('balancers'):
            assert all(o.get('protocol')!='hysteria' for o in p['outbounds'])
            assert all(n.get('port')!=8444 for o in p['outbounds'] for n in o.get('settings',{}).get('vnext',[]))


def test_aliases_never_clone_warp_even_if_it_arrives_first(monkeypatch):
    monkeypatch.setattr(api,'_catalog_overrides',lambda:{})
    result=api._with_youtube_without_ads_alias(api._with_temporary_location_aliases(links()))
    for link in result:
        name=urllib.parse.unquote(link.rsplit('#',1)[-1])
        if name in ('🇩🇪 Германия','🇵🇱 Польша','🇳🇱 Нидерланды','🇷🇺 Ютуб без рекламы'):
            assert urllib.parse.urlsplit(link).port==443
    normalized=[api._normalize_customer_profile_label(l) for l in links()]
    assert [urllib.parse.unquote(l.rsplit('#',1)[-1]) for l in normalized[:2]]==['🇸🇪 '+n for n in api.SWEDEN_SPECIAL_NAMES]
    assert not api._allowed_customer_transport('hy2://test@other:443#'+urllib.parse.quote(api.SWEDEN_GAMES_NAME))
