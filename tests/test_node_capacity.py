from monitoring.node_capacity import summarize
from datetime import datetime, timedelta, timezone
from monitoring.node_capacity import network_user_estimate


def _samples(count, rx_mbps=20, tx_mbps=10, cpu=20):
    step = timedelta(hours=20 / max(1, count - 1)) if count >= 72 else timedelta(minutes=5)
    start = datetime.now(timezone.utc) - step * max(0, count - 1)
    return [{"sampled_at": (start + step * i).isoformat(),
             "net_rx_bps": rx_mbps * 1_000_000,
             "net_tx_bps": tx_mbps * 1_000_000,
             "cpu_pct": cpu, "mem_pct": 40} for i in range(count)]


def test_capacity_stays_unknown_without_verified_measurement_or_coverage():
    no_capacity = summarize(_samples(80), {}, "24h")
    assert no_capacity["network"]["rx"]["headroom_pct"] is None
    assert no_capacity["additional_users"] is None
    too_few = summarize(_samples(3), {"rx": 100, "tx": 100}, "24h")
    assert not too_few["coverage_ok"]
    assert too_few["network"]["rx"]["headroom_pct"] is None


def test_network_scenario_is_explicit_and_reserves_capacity():
    summary=summarize(_samples(80,tx_mbps=10),{},'24h')
    benchmark=[{'city':str(i),'valid':True,'receiver_mbps':100} for i in range(5)]
    estimate=network_user_estimate(summary,benchmark,10)
    assert estimate['additional_users']==6
    assert not estimate['verified_user_capacity']
    assert network_user_estimate(summary,benchmark[:-1],10) is None
    high=summarize(_samples(80,cpu=90),{},'24h')
    assert network_user_estimate(high,benchmark,10)['additional_users']==0


def test_sustained_high_load_warns_only_with_sufficient_long_window():
    high = summarize(_samples(80, rx_mbps=86, tx_mbps=15, cpu=88),
                     {"rx": 100, "tx": 100}, "24h")
    assert high["network"]["rx"]["headroom_pct"] == 14
    assert "rx_capacity_critical" in high["warnings"]
    assert "cpu_sustained_high" in high["warnings"]
    short = summarize(_samples(12, rx_mbps=86, cpu=88),
                      {"rx": 100, "tx": 100}, "1h")
    assert short["warnings"] == []


def test_many_samples_in_a_short_burst_do_not_claim_a_day_of_coverage():
    burst = _samples(80)
    same_time = burst[0]["sampled_at"]
    for item in burst:
        item["sampled_at"] = same_time
    summary = summarize(burst, {"rx": 100, "tx": 100}, "24h")
    assert not summary["coverage_ok"]
    assert summary["network"]["rx"]["headroom_pct"] is None
