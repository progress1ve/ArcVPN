import sqlite3
import pytest
from monitoring.cdn_connections import classify, identity_hash, schema, ingest, states


def line(destination, tag='EE_OWNER_DIRECT_XHTTP'):
    return f'2026/10/02 12:00:00 from 127.0.0.1:1 accepted {destination} [{tag} -> DIRECT] email: test-user'


def test_probe_and_payload_are_separate_without_saving_destinations():
    assert classify(line('tcp:sub.arccnet.space:18080')) == (identity_hash('test-user'), 'probe')
    assert classify(line('tcp:example.com:443')) == (identity_hash('test-user'), 'user')
    assert classify(line('tcp:www.gstatic.com:80'))[1] == 'legacy'
    assert classify(line('tcp:example.com:443', 'EE_1CHOST_VLESS_TCP')) is None
    assert classify('malformed') is None
    assert classify(line('tcp:example.com:443').replace('accepted', 'rejected')) is None


def database():
    conn = sqlite3.connect(':memory:'); conn.row_factory = sqlite3.Row; schema(conn)
    return conn


def test_fresh_probe_only_real_legacy_and_stale_report():
    c = database(); h = identity_hash('test-user'); ids = {1: ['test-user']}; now = 1000
    ingest(c, '87.251.19.197', {'available':True,'identities':[{'hash':h,'probe_at':999}]}, now)
    assert states(c, ids, now)[1] == 'probe'
    ingest(c, '87.251.19.197', {'available':True,'identities':[{'hash':h,'user_at':999}]}, now)
    assert states(c, ids, now)[1] == 'user'
    assert states(c, ids, now+200)[1] == 'unknown'
    c.execute('DELETE FROM cdn_connection_activity')
    ingest(c, '87.251.19.197', {'available':True,'identities':[{'hash':h,'legacy_at':999,'probe_at':999}]}, now)
    assert states(c, ids, now)[1] == 'unknown'
    assert states(c, {2:['absent']}, now)[2] == 'none'
    c.execute('DELETE FROM cdn_connection_reports')
    assert states(c, ids, now)[1] == 'unknown'


def test_untrusted_reports_are_bounded_and_atomic():
    c=database()
    for payload in [{'available':1,'identities':[]}, {'available':True,'identities':[{'hash':'secret'}]},
                    {'available':True,'identities':[{'hash':'a'*64,'user_at':float('nan')}]}]:
        with pytest.raises(ValueError): ingest(c,'87.251.19.197',payload,1000)
    assert c.execute('SELECT count(*) FROM cdn_connection_reports').fetchone()[0] == 0


def test_missing_schema_is_unknown_not_false_positive():
    c=sqlite3.connect(':memory:'); c.row_factory=sqlite3.Row
    assert states(c,{1:['test']}) == {}
