import copy
import json
from urllib.parse import unquote, urlsplit, parse_qs
from monitoring import restored_peers as m


def test_restore_is_scoped_and_keeps_authorization(tmp_path, monkeypatch):
    monkeypatch.setattr(m,'STATE',tmp_path/'state')
    peers={name:{'address':tag+'.example','serverName':tag+'.example','publicKey':'pub','shortId':'00'} for name,tag in m.PEERS.items()}
    m.STATE.write_text(json.dumps({'enabled':True,**peers}))
    proxy={'tag':'proxy','settings':{'vnext':[{'address':'nl.example','port':443,'users':[{'id':'same'}]}]},'streamSettings':{'realitySettings':{}}}
    lt={'remarks':'🇱🇹 Литва','outbounds':[copy.deepcopy(proxy),{**copy.deepcopy(proxy),'tag':'youtube-nl'}],'routing':{'rules':[{'domain':['youtube.com'],'outboundTag':'youtube-nl'}]}}
    se={'remarks':'🇸🇪 Швеция','outbounds':[copy.deepcopy(proxy)],'routing':{'rules':[]}}
    auto={'remarks':'Автовыбор','outbounds':[{**copy.deepcopy(proxy),'tag':'nl-primary'}],'routing':{'balancers':[{'tag':'lt-first','selector':['nl-primary'],'fallbackTag':'cdn-stage'}]},'burstObservatory':{'subjectSelector':['nl-primary','cdn-a']}}
    original=[lt,se,auto,{'remarks':'Other'}];before=copy.deepcopy(original)
    result=m.apply(original)
    assert original==before and result[-1]==before[-1]
    for p in result[:2]:
        target=p['outbounds'][0]['settings']['vnext'][0]
        assert target['address']==peers[p['remarks']]['address'] and target['users']==[{'id':'same'}]
        assert next(o for o in p['outbounds'] if o['tag']=='youtube-nl')['settings']['vnext'][0]['address']=='nl.example'
    assert result[2]['routing']['balancers'][0]=={'tag':'lt-first','selector':['nl-primary','lt-primary','se-primary'],'fallbackTag':'cdn-stage'}
    assert m.apply(result)==result
    links=['vless://same@nl.example:443?security=reality#'+__import__('urllib.parse',fromlist=['quote']).quote(n) for n in m.PEERS]
    for link,name in zip(m.apply_links(links),m.PEERS):
        p=urlsplit(link);assert p.username=='same' and p.hostname==peers[name]['address']
        assert parse_qs(p.query)['sni']==[peers[name]['serverName']]


def test_missing_state_no_change(tmp_path, monkeypatch):
    monkeypatch.setattr(m,'STATE',tmp_path/'missing');ps=[{'remarks':'Other'}]
    assert m.apply(ps) is ps
