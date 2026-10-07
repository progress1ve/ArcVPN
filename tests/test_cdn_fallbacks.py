import copy
from monitoring.cdn_fallbacks import apply

def template(name):
 return {'remarks':name,'outbounds':[
  {'tag':'proxy-main-1','protocol':'vless','settings':{'vnext':[{'address':'ee.arccnet.space','users':[{'id':'test-id'}]}]}},
  {'tag':'proxy-back-1','protocol':'vless','settings':{'vnext':[{'address':'cdn-de.arccnet.space','users':[{'id':'test-id'}]}]},'streamSettings':{'network':'xhttp','security':'tls','tlsSettings':{'serverName':'cdn-de.arccnet.space'},'xhttpSettings':{'extra':{}}}},
  {'tag':'block','protocol':'blackhole'}],
  'routing':{'balancers':[{'tag':'main','selector':['proxy-main'],'fallbackTag':'proxy-back-1'}],'rules':[{'type':'field','balancerTag':'main'}]},
  'burstObservatory':{'subjectSelector':['proxy-main']}}

def test_two_ordered_fallbacks_preserve_identity():
 source=[template('Автовыбор'),template('🇪🇺 Лучший обход'),template('🇪🇺 Обход глушилок #2'),template('🇪🇺 Обход глушилок #5'),template('🇪🇺 Обход глушилок #8')];saved=copy.deepcopy(source)
 for p in apply(source):
  bytag={o['tag']:o for o in p['outbounds']}
  for tag,size,interval in [('cdn-fast',4096,7),('cdn-safe',24000,10)]:
   o=bytag[tag];assert o['settings']['vnext'][0]['users'][0]['id']=='test-id'
   e=o['streamSettings']['xhttpSettings']['extra'];assert (e['scMaxEachPostBytes'],e['scMinPostsIntervalMs'])==(size,interval)
  assert bytag['cdn-fast']['streamSettings']['xhttpSettings']['extra']['xmux']['maxConcurrency']=='16-32'
  assert p['routing']['balancers'][-1]['fallbackTag']=='cdn-safe'
 assert source==saved

def test_direct_profiles_have_no_balancers_or_loopbacks():
 from monitoring.weighted_connections import configure
 for number,size,interval in [(3,4096,7),(4,24000,10),(6,65536,'60-75'),(7,32768,10)]:
  p=template('🇪🇺 Обход глушилок #'+str(number));configure(p,p['routing']['balancers'][0],[('proxy-main-1',1)],'proxy-back-1')
  r=apply([p])[0];assert 'balancers' not in r['routing'];assert 'burstObservatory' not in r
  assert not any(o.get('protocol')=='loopback' for o in r['outbounds'])
  assert not any('balancerTag' in rule for rule in r['routing']['rules'])
  e=r['outbounds'][0]['streamSettings']['xhttpSettings']['extra'];assert (e['scMaxEachPostBytes'],e['scMinPostsIntervalMs'])==(size,interval)
  assert r['outbounds'][0]['settings']['vnext'][0]['users'][0]['id']=='test-id'

def test_policy_block_and_no_entitlement_remain_closed():
 p=template('Автовыбор');p['routing']['balancers'][0]['fallbackTag']='block';assert apply([p])==[p]
 p=template('Автовыбор');p['outbounds'].pop(1);assert apply([p])==[p]
