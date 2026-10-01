"""Owner-approved ordered CDN fallback paths, preserving per-user credentials."""
import copy
import re

HOST = 'cdn-de.arccnet.space'

def apply(profiles, reserve_names=()):
    result = copy.deepcopy(profiles)
    for profile in result:
        outbounds = profile.get('outbounds', [])
        candidates = [o for o in outbounds
                      if o.get('tag', '').startswith('proxy-back-')
                      and o.get('streamSettings', {}).get('network') == 'xhttp'
                      and o.get('settings', {}).get('vnext', [{}])[0].get('address') == HOST]
        if not candidates:
            continue  # No LTE entitlement / no existing CDN credentials.
        routing = profile.get('routing', {})
        balancers = routing.get('balancers', [])
        parents = [b for b in balancers if b.get('fallbackTag') in {o['tag'] for o in candidates}]
        if not parents:
            continue  # Respect policy fallback=block and manual profiles.
        fast = copy.deepcopy(candidates[0])
        fast['tag'] = 'cdn-fast'
        xs = fast['streamSettings']['xhttpSettings']
        xs.update(host=HOST, path='/api-ee-direct', mode='packet-up')
        extra = xs.setdefault('extra', {})
        extra.update(uplinkHTTPMethod='GET', uplinkDataPlacement='header',
                     uplinkDataKey='X-Session-Token', scMaxEachPostBytes=4096,
                     scMinPostsIntervalMs=1, xPaddingBytes='100-200')
        padding = {k:v for k,v in extra.items() if k.startswith('xPadding')}
        extra['downloadSettings'] = {
            'address':HOST, 'port':443, 'network':'xhttp', 'security':'tls',
            'tlsSettings':copy.deepcopy(fast['streamSettings']['tlsSettings']),
            'xhttpSettings':{'host':HOST,'path':'/api-ee-direct','mode':'packet-up',
                             'extra':{**padding,'xmux':{'maxConcurrency':1,'maxConnections':0}}},
        }
        name = profile.get('remarks','')
        secondary = bool(re.search(r'Обход глушилок\s*#[45](?:\s|$)',name)) or name in reserve_names
        additions = [fast, {'tag':'cdn-stage','protocol':'loopback',
                             'settings':{'inboundTag':'cdn-stage'}}]
        if secondary:
            safe = copy.deepcopy(fast)
            safe['tag']='cdn-safe'
            sx=safe['streamSettings']['xhttpSettings'];sx['path']='/api-ee-reserve'
            se=sx['extra'];se.update(uplinkDataKey='X-Request-Trace',
                                     scMaxEachPostBytes=24000,scMinPostsIntervalMs=10)
            # Preserve the chat baseline padding, with matching server support.
            se['xPaddingBytes']='100-1000'
            se.pop('downloadSettings',None)
            additions.append(safe)
        for parent in parents:
            parent['fallbackTag']='cdn-stage'
        removed={o['tag'] for o in candidates}
        profile['outbounds']=[o for o in outbounds if o['tag'] not in removed]+additions
        routing['balancers'].append({'tag':'balancer_cdn_fast','selector':['cdn-fast'],
            'strategy':{'type':'leastPing'},'fallbackTag':'cdn-safe' if secondary else 'block'})
        routing['rules'].insert(0,{'type':'field','inboundTag':['cdn-stage'],
                                   'network':'tcp,udp','balancerTag':'balancer_cdn_fast'})
        observatory=profile.setdefault('burstObservatory',{})
        selectors=observatory.setdefault('subjectSelector',[])
        if 'cdn-fast' not in selectors:selectors.append('cdn-fast')
    return result
