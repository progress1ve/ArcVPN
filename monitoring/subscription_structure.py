"""Public-safe projection of the actual customer renderer."""
def project(profiles):
    result = []
    for index, profile in enumerate(profiles):
        balancers = (profile.get('routing') or {}).get('balancers') or []
        result.append({'order':index,'name':profile.get('remarks',''),
                       'kind':'balancer' if balancers else 'location',
                       'strategy':((balancers[0].get('strategy') or {}).get('type') if balancers else None),
                       'members':len(balancers[0].get('selector') or []) if balancers else 0})
    return result
