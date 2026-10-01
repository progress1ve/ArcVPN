import sqlite3
import pytest
from monitoring.benchmark_jobs import schema, enqueue, clean_output, SOURCE_SHA
from pathlib import Path
import hashlib


def test_source_is_original_reviewed_multitest_module():
    source=Path(__file__).resolve().parents[1]/'monitoring/vendor/russian-iperf3.sh'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==SOURCE_SHA


def test_jobs_are_serial_and_unknown_hosts_are_rejected():
    conn=sqlite3.connect(':memory:')
    schema(conn)
    with pytest.raises(ValueError): enqueue(conn,'127.0.0.1')
    identifier=enqueue(conn,'87.251.19.197')
    conn.commit()
    assert conn.execute('SELECT status FROM node_benchmark_jobs WHERE id=?',(identifier,)).fetchone()[0]=='queued'
    with pytest.raises(ValueError,match='node_busy'): enqueue(conn,'87.251.19.197')
    conn.rollback()


def test_terminal_output_is_bounded_and_has_no_control_sequences():
    assert clean_output('\x1b[31merror\x1b[0m\x00')=='error'
    assert len(clean_output('x'*200000))==100000


def test_agent_token_cannot_claim_another_node(tmp_path,monkeypatch):
    import subscription_api as api
    from monitoring.benchmark_jobs import token_hash
    path=tmp_path/'jobs.sqlite3'
    with sqlite3.connect(path) as conn:
        schema(conn)
        conn.execute('INSERT INTO node_benchmark_agents(host,token_hash) VALUES(?,?)',('87.251.19.197',token_hash('test-node-token')))
    def db():
        conn=sqlite3.connect(path);conn.row_factory=sqlite3.Row;return conn
    monkeypatch.setattr(api,'get_db',db)
    client=api.app.test_client()
    response=client.post('/api/internal/benchmark-agent',json={'host':'151.241.137.174','action':'claim'},headers={'Authorization':'Bearer test-node-token'})
    assert response.status_code==403
    response=client.post('/api/internal/benchmark-agent',json={'host':'87.251.19.197','action':'claim'},headers={'Authorization':'Bearer test-node-token'})
    assert response.status_code==200
    assert response.get_json()['job'] is None
