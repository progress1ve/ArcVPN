from datetime import datetime,timedelta
from monitoring.node_demand import estimate,record,schema
from monitoring.subscription_structure import project
import sqlite3

def test_average_is_user_time_weighted_and_needs_history():
    start=datetime(2026,10,1)
    rows=[{'sampled_at':str(start+timedelta(minutes=12*i)),'users':10,'tx_bps':100_000_000,'cpu_pct':5,'mem_pct':10} for i in range(12)]
    bench=[{'valid':True,'receiver_mbps':1000} for i in range(5)]
    summary={'p95':{'cpu_pct':20,'mem_pct':40}}
    assert estimate(rows,bench,summary)['additional_users']==60
    assert estimate(rows[:2],bench,summary) is None
    rows[0]['users']=20
    assert estimate(rows,bench,summary)['observed_mbps_per_user']==9.231
    summary['p95']['cpu_pct']=90
    assert estimate(rows,bench,summary)['additional_users']==0

def test_collector_converts_bytes_and_ignores_disconnected():
    c=sqlite3.connect(':memory:');schema(c)
    nodes=[{'address':'151.241.137.174','isConnected':True,'usersOnline':3,'system':{'stats':{'interface':{'txBytesPerSec':100}}}}]
    record(c,nodes)
    assert c.execute('SELECT users,tx_bps FROM node_demand_samples').fetchone()==(3,800)
    nodes[0]['isConnected']=False
    record(c,nodes)
    assert c.execute('SELECT COUNT(*) FROM node_demand_samples').fetchone()[0]==1

def test_projection_never_exposes_outbound_credentials():
    data=project([{'remarks':'Bypass','routing':{'balancers':[{'selector':['x'],'strategy':{'type':'leastLoad'}}]},'outbounds':[{'password':'private'}]},{'remarks':'FI'}])
    assert data[0]['kind']=='balancer'
    assert data[1]['kind']=='location'
    assert 'private' not in str(data)
