"""Publish Sweden as a Royale alias and retire Lithuanian profiles."""
import copy
from urllib.parse import quote, unquote, urlsplit

from monitoring.lithuania_evacuation import HOSTS
from monitoring.royale_owner import PUBLIC_NAME

SWEDEN = '🇸🇪 Швеция'


def retired(name):
    return 'литва' in name.casefold()


def apply(profiles):
    result = [p for p in profiles if not retired(p.get('remarks', ''))
              and p.get('remarks') != SWEDEN]
    nl = next((p for p in result if p.get('remarks') == PUBLIC_NAME), None)
    if nl:
        alias = copy.deepcopy(nl)
        alias['remarks'] = SWEDEN
        result.insert(result.index(nl) + 1, alias)
    return result


def apply_links(links):
    result = []
    for link in links:
        parsed = urlsplit(link)
        name = unquote(parsed.fragment)
        if retired(name) or name == SWEDEN or parsed.hostname in HOSTS:
            continue
        result.append(link)
        if name == PUBLIC_NAME:
            result.append(parsed._replace(fragment=quote(SWEDEN)).geturl())
    return result
