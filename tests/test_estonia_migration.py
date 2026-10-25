import copy
from scripts.ops.pause_sweden_to_estonia import prepare_config, moscow_on_estonia, WARP
from monitoring.cdn_fallbacks import VARIANTS


def test_prepare_retains_existing_auth_and_adds_private_cdn_and_warp():
    ee = {'inbounds':[{'tag':'EE_1CHOST_VLESS_TCP','port':443,'settings':{'clients':[{'id':'existing-user'}]},'streamSettings':{'security':'reality','realitySettings':{'privateKey':'synthetic-ee-key'}}},
                      {'tag':'EE_1CHOST_HYSTERIA2','port':443,'streamSettings':{'tlsSettings':{'certificates':[{'certificateFile':'old'}]}}}],
          'outbounds':[{'tag':'DIRECT','protocol':'freedom'}], 'routing':{'rules':[{'outboundTag':'DIRECT'}]}}
    se = {'inbounds':[{'tag':v['tag'],'port':v['port'],'settings':{'clients':[]},'streamSettings':{'xhttpSettings':{'path':v['path']}}} for v in VARIANTS.values()],
          'outbounds':[{'tag':'WARP'},{'tag':'WARP_DNS_TCP'}],
          'routing':{'rules':[{'inboundTag':['SE_HOSTUP_WARP_REALITY'],'port':'53','network':'udp','outboundTag':'WARP_DNS_TCP'},
                              {'inboundTag':['SE_HOSTUP_WARP_REALITY'],'network':'udp','outboundTag':'BLOCK'},
                              {'inboundTag':['SE_HOSTUP_WARP_REALITY'],'network':'tcp','outboundTag':'WARP'}]}}
    original = copy.deepcopy(ee)
    result,tags = prepare_config(ee,se)
    assert ee == original
    assert result['inbounds'][0] == original['inbounds'][0]
    assert len(tags) == 4
    for inbound in result['inbounds']:
        if inbound['tag'] in tags:
            assert inbound['listen'] == '127.0.0.1'
    warp = next(i for i in result['inbounds'] if i['tag'] == WARP)
    assert warp['port'] == 8444 and not warp['settings']['clients']
    assert warp['streamSettings']['realitySettings']['privateKey'] == 'synthetic-ee-key'
    rules = [r for r in result['routing']['rules'] if r.get('inboundTag') == [WARP]]
    assert rules[0]['outboundTag'] == 'WARP_DNS_TCP' and rules[1]['outboundTag'] == 'BLOCK'
    assert prepare_config(result,se)[0] == result


def test_moscow_rewrite_keeps_local_youtube_and_existing_inbound_identity():
    cfg = {'inbounds':[{'tag':'existing-inbound','settings':{'clients':['preserved']}}],
           'outbounds':[{'tag':'EE_BRIDGE'},{'tag':'SE_BRIDGE'},{'tag':'weighted-ru-ticket-0'},{'tag':'DIRECT'},{'tag':'BLOCK'}],
           'routing':{'balancers':[{'tag':'main'}], 'rules':[
               {'inboundTag':['RU_SS_YOUTUBE'],'outboundTag':'DIRECT'},
               {'inboundTag':['weighted-ru-ticket-0'],'outboundTag':'SE_BRIDGE'},
               {'inboundTag':['existing-inbound'],'balancerTag':'main'}]}}
    rewritten = moscow_on_estonia(cfg)
    assert rewritten['inbounds'] == cfg['inbounds']
    assert 'balancers' not in rewritten['routing']
    assert rewritten['routing']['rules'][0] == cfg['routing']['rules'][0]
    assert rewritten['routing']['rules'][1]['outboundTag'] == 'EE_BRIDGE'
    assert {o['tag'] for o in rewritten['outbounds']} == {'EE_BRIDGE','DIRECT','BLOCK'}
