"""CDN XHTTP variants preserving existing authorization and user identity."""
import copy
import re
HOST = 'cdn-de.arccnet.space'
VARIANTS = {
 4096: {'path':'/api-se-test-4096','tag':'SE_CDN_TEST_4096','port':10012,'key':'X-Session-Token','interval':7},
 24000:{'path':'/api-se-test-24000','tag':'SE_CDN_TEST_24000','port':10013,'key':'X-Request-Trace','interval':10},
 65536:{'path':'/api-se-65536','tag':'SE_CDN_BODY_65536','port':10014,'key':'','interval':'60-75'},
 32768:{'path':'/api-se-32768','tag':'SE_CDN_HEADER_32768','port':10015,'key':'X-Data','interval':10},
}
def settings(size):
 v=VARIANTS[size]
 e={'uplinkHTTPMethod':'GET','uplinkDataPlacement':'header','uplinkDataKey':v['key'],
    'scMaxEachPostBytes':size,'scMinPostsIntervalMs':v['interval'],
    'xPaddingBytes':'100-1000','xPaddingKey':'dc','xPaddingHeader':'X-Cache',
    'xPaddingMethod':'tokenish','xPaddingObfsMode':True,'xPaddingPlacement':'queryInHeader'}
 if size==4096:
  e.update(uplinkChunkSize=4096,xmux={'hKeepAlivePeriod':30,'hMaxRequestTimes':'600-900',
   'hMaxReusableSecs':'1800-3000','maxConcurrency':'16-32'})
 return e

def outbound(source,size,tag):
 o=copy.deepcopy(source);o['tag']=tag
 o['settings']['vnext'][0].update(address=HOST,port=443)
 s=o['streamSettings'];s['security']='tls';s.pop('realitySettings',None)
 s['tlsSettings']={'serverName':HOST,'fingerprint':'firefox','alpn':['h2','http/1.1']}
 variant=VARIANTS[size]
 s['xhttpSettings']={'host':HOST,'path':variant['path'],'mode':'packet-up','extra':settings(size)}
 o.pop('mux',None)
 return o

def direct(profile,source,size):
 proxy=outbound(source,size,'cdn-direct');routing=profile.setdefault('routing',{})
 loopbacks={o.get('settings',{}).get('inboundTag') for o in profile['outbounds'] if o.get('protocol')=='loopback'}
 rules=[]
 for r in routing.get('rules',[]):
  if set(r.get('inboundTag',[])) & loopbacks:continue
  r=copy.deepcopy(r)
  if 'balancerTag' in r:r.pop('balancerTag');r['outboundTag']='cdn-direct'
  if r.get('outboundTag','').startswith(('proxy-','weighted-','cdn-','policy-')):r['outboundTag']='cdn-direct'
  rules.append(r)
 rules.append({'type':'field','network':'tcp,udp','outboundTag':'cdn-direct'})
 routing.pop('balancers',None);routing['rules']=rules
 profile['outbounds']=[proxy]+[o for o in profile['outbounds'] if o.get('protocol') in ('freedom','blackhole','dns')]
 for k in ('observatory','burstObservatory'):profile.pop(k,None)
 return profile

def cdn_only(profile, source):
 """Use only authorized CDN transports; split direct/block rules stay intact."""
 routing=profile.setdefault('routing',{})
 old=profile['outbounds']
 retained=[o for o in old if o.get('protocol') in ('freedom','blackhole','dns')]
 retained_tags={o['tag'] for o in retained}
 removed_tags={o['tag'] for o in old if o['tag'] not in retained_tags}
 loopbacks={o.get('settings',{}).get('inboundTag') for o in old if o.get('protocol')=='loopback'}
 rules=[]
 for original in routing.get('rules',[]):
  rule=copy.deepcopy(original)
  if 'inboundTag' in rule:
   rule['inboundTag']=[tag for tag in rule['inboundTag'] if tag not in loopbacks]
   if not rule['inboundTag']:continue
  if 'balancerTag' in rule or rule.get('outboundTag') in removed_tags:
   rule.pop('outboundTag',None);rule['balancerTag']='balancer_cdn_only'
  rules.append(rule)
 rules.append({'type':'field','network':'tcp,udp','balancerTag':'balancer_cdn_only'})
 choices=[(32768,'cdn-medium'),(4096,'cdn-fast'),(24000,'cdn-safe')]
 variants=[outbound(source,size,tag) for size,tag in choices]
 profile['outbounds']=variants+retained
 routing['rules']=rules
 routing['balancers']=[{'tag':'balancer_cdn_only','selector':[o['tag'] for o in variants],
  'strategy':{'type':'leastLoad','settings':{'expected':2,'maxRTT':'800ms',
   'baselines':['200ms','400ms'],'tolerance':0.05}},'fallbackTag':'cdn-safe'}]
 profile.pop('observatory',None)
 observer=profile.setdefault('burstObservatory',{})
 observer['subjectSelector']=[o['tag'] for o in variants]
 observer.setdefault('pingConfig',{}).update(interval='30s',sampling=3,timeout='2s')
 return profile

def apply(profiles,reserve_names=()):
 result=copy.deepcopy(profiles)
 for profile in result:
  outbounds=profile.get('outbounds',[])
  candidates=[o for o in outbounds if o.get('tag','').startswith('proxy-back-')
   and o.get('streamSettings',{}).get('network')=='xhttp'
   and o.get('settings',{}).get('vnext',[{}])[0].get('address')==HOST]
  if not candidates:continue
  routing=profile.get('routing',{});balancers=routing.get('balancers',[])
  parents=[b for b in balancers if b.get('fallbackTag') in {o['tag'] for o in candidates}]
  if not parents:continue
  if '\u041b\u0443\u0447\u0448\u0438\u0439 \u043e\u0431\u0445\u043e\u0434' in profile.get('remarks',''):
   cdn_only(profile,candidates[0]);continue
  number=re.search(r'\u041e\u0431\u0445\u043e\u0434 \u0433\u043b\u0443\u0448\u0438\u043b\u043e\u043a\s*#(\d+)(?:\s|$)',profile.get('remarks',''))
  size={3:4096,4:24000,6:65536,7:32768}.get(int(number.group(1))) if number else None
  if size:
   direct(profile,candidates[0],size);continue
  fast=outbound(candidates[0],4096,'cdn-fast');safe=outbound(candidates[0],24000,'cdn-safe')
  for parent in parents:parent['fallbackTag']='cdn-stage'
  removed={o['tag'] for o in candidates}
  profile['outbounds']=[o for o in outbounds if o['tag'] not in removed]+[fast,safe,
   {'tag':'cdn-stage','protocol':'loopback','settings':{'inboundTag':'cdn-stage'}}]
  balancers.append({'tag':'balancer_cdn_fast','selector':['cdn-fast'],'strategy':{'type':'leastPing'},'fallbackTag':'cdn-safe'})
  routing['rules'].insert(0,{'type':'field','inboundTag':['cdn-stage'],'network':'tcp,udp','balancerTag':'balancer_cdn_fast'})
  selectors=profile.setdefault('burstObservatory',{}).setdefault('subjectSelector',[])
  if 'cdn-fast' not in selectors:selectors.append('cdn-fast')
 return result
