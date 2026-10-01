import copy
from monitoring.cdn_fallbacks import apply

def template(name):
    return {'remarks':name,'outbounds':[
        {'tag':'proxy-main-1','protocol':'vless','settings':{'vnext':[{'address':'ee.arccnet.space','users':[{'id':'test-id'}]}]}},
        {'tag':'proxy-back-1','protocol':'vless','settings':{'vnext':[{'address':'cdn-de.arccnet.space','users':[{'id':'test-id'}]}]},
         'streamSettings':{'network':'xhttp','security':'tls','tlsSettings':{'serverName':'cdn-de.arccnet.space'},
                           'xhttpSettings':{'extra':{'xPaddingObfsMode':True,'xPaddingKey':'dc'}}}},
        {'tag':'block','protocol':'blackhole'}],
        'routing':{'balancers':[{'tag':'main','selector':['proxy-main'],'fallbackTag':'proxy-back-1'}],
                   'rules':[{'type':'field','balancerTag':'main'}]},
        'burstObservatory':{'subjectSelector':['proxy-main'],'pingConfig':{'destination':'https://www.google.com/generate_204'}}}

def test_ordered_paths_preserve_identity_and_manual_profiles():
    source=[template('Автовыбор'),template('🇪🇺 Лучший обход'),template('🇪🇺 Обход глушилок #2'),template('🇪🇺 Обход глушилок #3'),template('🇪🇺 Обход глушилок #4'),template('🇪🇺 Обход глушилок #5'),{'remarks':'manual','outbounds':[]}]
    saved=copy.deepcopy(source);result=apply(source)
    assert source==saved
    for index,p in enumerate(result[:-1]):
        bytag={o['tag']:o for o in p['outbounds']}
        assert bytag['cdn-fast']['settings']['vnext'][0]['users'][0]['id']=='test-id'
        extra=bytag['cdn-fast']['streamSettings']['xhttpSettings']['extra']
        assert extra['scMaxEachPostBytes']==4096 and extra['scMinPostsIntervalMs']==1
        assert extra['downloadSettings']['address']=='cdn-de.arccnet.space'
        assert p['routing']['balancers'][0]['fallbackTag']=='cdn-stage'
        assert p['routing']['rules'][0]['balancerTag']=='balancer_cdn_fast'
        assert p['routing']['balancers'][-1]['fallbackTag']==('cdn-safe' if index>=4 else 'block')
        assert ('cdn-safe' in bytag)==(index>=4)
        if index>=4:
            e=bytag['cdn-safe']['streamSettings']['xhttpSettings']['extra']
            assert e['uplinkDataKey']=='X-Request-Trace' and e['scMaxEachPostBytes']==24000
    assert result[-1]==source[-1]

def test_policy_block_and_no_entitlement_remain_closed():
    p=template('Автовыбор');p['routing']['balancers'][0]['fallbackTag']='block'
    assert apply([p])==[p]
    p=template('Автовыбор');p['outbounds'].pop(1)
    assert apply([p])==[p]

def test_custom_policy_names_keep_reserve():
    p=apply([template('Custom reserve')],['Custom reserve'])[0]
    assert p['routing']['balancers'][-1]['fallbackTag']=='cdn-safe'
