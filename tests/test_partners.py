import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from flask import Flask

from database import connection, db_partners as db
from partner_api import COOKIE, register_partner_api


@pytest.fixture
def partner_db(tmp_path, monkeypatch):
    path = tmp_path / "partners.sqlite"
    monkeypatch.setattr(connection, "DB_PATH", path)
    with connection.get_db() as conn:
        conn.executescript("""
            CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,first_name TEXT,referral_code TEXT,referred_by INTEGER);
            CREATE TABLE vpn_keys(id INTEGER PRIMARY KEY,user_id INTEGER,expires_at TEXT,uuid TEXT);
            CREATE TABLE trial_entitlements(vpn_key_id INTEGER,status TEXT);
            CREATE TABLE ad_campaigns(id INTEGER PRIMARY KEY,name TEXT,code TEXT,is_active INTEGER DEFAULT 1);
            CREATE TABLE user_campaign_attribution(user_id INTEGER PRIMARY KEY,campaign_id INTEGER,attributed_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE tariffs(id INTEGER PRIMARY KEY,duration_days INTEGER,name TEXT);
            CREATE TABLE payments(id INTEGER PRIMARY KEY,user_id INTEGER,tariff_id INTEGER,order_id TEXT UNIQUE,status TEXT,
                fulfillment_status TEXT,operation_type TEXT,payment_type TEXT,amount_cents INTEGER,
                yookassa_payment_id TEXT,partner_verified_cents INTEGER,paid_at TEXT,fulfilled_at TEXT,offer_code TEXT);
            INSERT INTO users VALUES(1,'one','One','refone',NULL),(2,'two','Two','reftwo',NULL),
                (3,'three','Three','refthree',1),(4,'four','Four','reffour',NULL);
            INSERT INTO ad_campaigns VALUES(1,'Campaign 1','campone',1),(2,'Campaign 2','camptwo',1);
            INSERT INTO user_campaign_attribution(user_id,campaign_id) VALUES(3,1);
        """)
        db.migrate(conn)
    p = db.create_partner("One", "partner1", "test-partner-password-1", "owner")
    q = db.create_partner("Two", "partner2", "test-partner-password-2", "owner")
    return p["id"], q["id"]


def bind(partner_id, user_id=1, target_id=1, kind="campaign"):
    source_id = db.assign_source(partner_id, kind, target_id, "owner")
    with connection.get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        assert db.bind_new_client(conn, user_id, kind, target_id)
    return source_id


def test_access_revoked_and_password_reset_revoke_sessions(partner_db):
    p, _ = partner_db
    token = db.authenticate("partner1", "test-partner-password-1", "test-ip")
    assert db.session_partner(token)["id"] == p
    db.update_partner(p, {"access_enabled": False}, "owner")
    assert db.session_partner(token) is None
    assert db.authenticate("partner1", "test-partner-password-1", "test-ip") is None
    db.update_partner(p, {"access_enabled": True}, "owner")
    token = db.authenticate("partner1", "test-partner-password-1", "test-ip")
    db.update_partner(p, {"password": "replacement-password-strong"}, "owner")
    assert db.session_partner(token) is None
    assert db.authenticate("partner1", "test-partner-password-1", "test-ip") is None


def test_login_limits_are_persistent_and_no_plaintext_secrets(partner_db):
    for _ in range(10):
        assert db.authenticate("unknown", "wrong", "same-ip") is None
    with pytest.raises(ValueError, match="login_rate_limited"):
        db.authenticate("partner1", "test-partner-password-1", "same-ip")
    with connection.get_db() as conn:
        hashes = [row[0] for row in conn.execute("SELECT password_hash FROM partners")]
        assert all("test-partner-password" not in value for value in hashes)


def test_source_assignment_has_no_automatic_import_and_frozen_terms(partner_db):
    p, q = partner_db
    source = db.assign_source(p, "campaign", 1, "owner")
    with connection.get_db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM partner_clients").fetchone()[0] == 0
    with pytest.raises(ValueError, match="source_already_assigned"):
        db.assign_source(q, "campaign", 1, "owner")
    with connection.get_db() as conn:
        assert db.bind_new_client(conn, 1, "campaign", 1)
    db.update_partner(p, {"rate_bps": 2500, "access_enabled": False}, "owner")
    with connection.get_db() as conn:
        assert db.bind_new_client(conn, 2, "campaign", 1)
        assert not db.bind_new_client(conn, 1, "campaign", 1)
        assert [(r["user_id"], r["rate_bps"]) for r in conn.execute("SELECT * FROM partner_clients ORDER BY user_id")] == [(1,3000),(2,2500)]
        with pytest.raises(sqlite3.IntegrityError, match="immutable_partner_client"):
            conn.execute("UPDATE partner_clients SET partner_id=? WHERE user_id=1", (q,))
    db.disable_source(p, source, "owner")
    db.assign_source(q, "campaign", 1, "owner")
    with connection.get_db() as conn:
        assert not db.bind_new_client(conn, 1, "campaign", 1)
        assert conn.execute("SELECT partner_id FROM partner_clients WHERE user_id=1").fetchone()[0] == p


def test_stop_recruiting_does_not_bind_new_clients(partner_db):
    p, _ = partner_db
    db.assign_source(p, "campaign", 1, "owner")
    db.update_partner(p, {"recruiting_enabled": False}, "owner")
    with connection.get_db() as conn:
        assert not db.bind_new_client(conn, 1, "campaign", 1)


def test_import_requires_reviewed_list_and_uses_snapshot_rate(partner_db):
    p, _ = partner_db
    source = db.assign_source(p, "campaign", 1, "owner")
    preview = db.preview_import(p, source, "owner")
    assert [r["id"] for r in preview["clients"]] == [3]
    db.update_partner(p, {"rate_bps": 1500}, "owner")
    assert db.confirm_import(p, preview["token"], "owner")["imported"] == 1
    assert db.confirm_import(p, preview["token"], "owner")["already_confirmed"]
    with connection.get_db() as conn:
        assert conn.execute("SELECT rate_bps FROM partner_clients WHERE user_id=3").fetchone()[0] == 3000
        assert conn.execute("SELECT COUNT(*) FROM partner_ledger").fetchone()[0] == 0


@pytest.fixture
def client(partner_db):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_partner_api(app, lambda permission: permission == "partners.manage" and __import__("flask").request.headers.get("X-Test-Owner") == "yes",
                         lambda: {"actor_id": "owner"}, lambda: "arcvpnnbot")
    return app.test_client()


def test_partner_cookie_never_authorizes_admin_and_csrf_is_required(client):
    assert client.post("/api/partners/login", json={"login":"partner1","password":"test-partner-password-1"},
                       base_url="https://partners.arccnet.space").status_code == 403
    response = client.post("/api/partners/login", json={"login":"partner1","password":"test-partner-password-1"},
                           base_url="https://partners.arccnet.space", headers={"Origin":"https://partners.arccnet.space"})
    assert response.status_code == 200
    cookie = response.headers["Set-Cookie"]
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Strict" in cookie and "Domain=" not in cookie
    assert client.get("/api/admin/partners", base_url="https://partners.arccnet.space").status_code == 403
    assert client.post("/api/partners/logout", json={}, base_url="https://partners.arccnet.space",
                       headers={"Origin":"https://attacker.example"}).status_code == 403


def test_admin_mutations_require_permission_and_origin(client):
    assert client.post("/api/admin/partners", json={}, headers={"X-Test-Owner":"yes"},
                       base_url="https://panel.arccnet.space").status_code == 403
    assert client.get("/api/admin/partners", headers={"X-Test-Owner":"yes"},
                      base_url="https://panel.arccnet.space").status_code == 200


def purchase(user=1, amount=9900, operation="new", status="paid", fulfilled="applied",
             provider="provider-1", verified=True, order="order-1", paytype="yookassa_qr"):
    with connection.get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""INSERT INTO payments(user_id,order_id,status,fulfillment_status,operation_type,payment_type,
            amount_cents,partner_verified_cents,yookassa_payment_id,paid_at,fulfilled_at)
            VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)""",
                     (user, order, status, fulfilled, operation, paytype, amount,
                      amount if verified else None, provider))
        return db.accrue_order(conn, order)


def body(kind="payout", amount=1000, key="test-operation-key-0001", related=None, accept=False):
    return {"kind": kind, "amount_cents": amount, "operation_key": key, "note": "Reviewed by owner",
            "method": "СБП вручную", "occurred_on": __import__("datetime").date.today().isoformat(),
            "related_id": related, "accept_negative": accept}


def current(partner):
    with connection.get_db() as conn:
        return db.balance(conn, partner)


def test_exact_30_percent_repeat_webhooks_and_renewals(partner_db):
    p, _ = partner_db
    bind(p)
    assert purchase()
    with connection.get_db() as conn:
        assert not db.accrue_order(conn, "order-1")
        assert conn.execute("SELECT amount_cents FROM partner_ledger").fetchone()[0] == 2970
    assert purchase(amount=19900, operation="renew", order="order-2", provider="provider-2")
    assert current(p)["accrued"] == 8940


@pytest.mark.parametrize("operation,status,fulfilled,verified,paytype", [
    ("trial_start","paid","applied",True,"yookassa_qr"),
    ("topup","paid","applied",True,"yookassa_qr"),
    ("new","pending","applied",True,"yookassa_qr"),
    ("new","canceled","applied",True,"yookassa_qr"),
    ("new","paid","applied",False,"yookassa_qr"),
    ("new","paid","applied",True,"balance"),
    ("new","paid","applied",True,"stars"),
    ("new","paid","applied",True,"crypto"),
])
def test_excludes_unconfirmed_free_trial_topup_and_unsupported_methods(partner_db, operation, status, fulfilled, verified, paytype):
    p, _ = partner_db
    bind(p)
    assert not purchase(operation=operation,status=status,fulfilled=fulfilled,verified=verified,paytype=paytype)
    assert current(p)["accrued"] == 0


@pytest.mark.parametrize("operation", ["addon_device","addon_lte","addon_combined","upgrade"])
def test_addons_and_upgrade_are_eligible(partner_db, operation):
    p, _ = partner_db
    bind(p)
    assert purchase(amount=2500,operation=operation)
    assert current(p)["accrued"] == 750


@pytest.mark.parametrize("fulfillment",["pending","manual_review","failed"])
def test_confirmed_payment_appears_like_admin_even_when_delivery_needs_retry(partner_db,fulfillment):
    p, _ = partner_db
    bind(p)
    assert purchase(fulfilled=fulfillment)
    assert current(p)["accrued"] == 2970


def test_frozen_rate_after_access_and_link_disabled(partner_db):
    p, _ = partner_db
    source = bind(p)
    db.update_partner(p, {"rate_bps": 2000, "recruiting_enabled":False, "access_enabled":False}, "owner")
    db.disable_source(p, source, "owner")
    assert purchase()
    assert current(p)["accrued"] == 2970


def test_provider_payment_cannot_accrue_twice(partner_db):
    p, _ = partner_db
    bind(p)
    assert purchase()
    assert not purchase(order="duplicate-order",provider="provider-1")
    assert current(p)["accrued"] == 2970


def test_historical_paid_orders_not_backfilled_even_same_second(partner_db):
    p, _ = partner_db
    assert not purchase(user=3)
    source = db.assign_source(p,"campaign",1,"owner")
    preview = db.preview_import(p,source,"owner")
    db.confirm_import(p,preview["token"],"owner")
    with connection.get_db() as conn:
        assert not db.accrue_order(conn,"order-1")
    assert purchase(user=3,order="future-renewal",provider="provider-2",operation="renew")
    assert current(p)["accrued"] == 2970


def test_partial_payout_is_idempotent_and_prevents_overdraft(partner_db):
    p, _ = partner_db
    bind(p); purchase()
    entry = db.post_entry(p,body(), "owner")
    assert db.post_entry(p,body(), "owner")["id"] == entry["id"]
    assert current(p)["available"] == 1970
    with pytest.raises(ValueError,match="operation_conflict"):
        db.post_entry(p,body(amount=1001), "owner")
    with pytest.raises(ValueError,match="insufficient_balance"):
        db.post_entry(p,body(amount=1971,key="second-operation-key"), "owner")
    db.post_entry(p,body(amount=1970,key="second-operation-key"), "owner")
    assert current(p)["available"] == 0
    assert current(p)["paid"] == 2970


def test_concurrent_payouts_and_duplicate_saves_are_serialized(partner_db):
    p, _ = partner_db
    bind(p); purchase()
    def save(key):
        try:
            return db.post_entry(p,body(amount=2000,key=key), "owner")["id"]
        except ValueError as exc:
            return str(exc)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, ["concurrent-key-0001","concurrent-key-0002"]))
    assert sum(isinstance(item,int) for item in results) == 1
    assert "insufficient_balance" in results
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: db.post_entry(p,body(amount=900,key="same-key-00000001"),"owner")["id"], range(2)))
    assert results[0] == results[1]
    assert current(p)["paid"] == 2900


def test_manual_refund_corrections_before_and_after_payout_preserve_history(partner_db):
    p, _ = partner_db
    bind(p); purchase()
    # Owner explicitly determines the correction: partial then full remainder.
    db.post_entry(p,body(kind="adjustment",amount=-300,related=1), "owner")
    paid = db.post_entry(p,body(amount=2670,key="manual-payout-00001"), "owner")
    with pytest.raises(ValueError,match="negative_balance_confirmation_required"):
        db.post_entry(p,body(kind="adjustment",amount=-2670,related=1,key="manual-refund-00001"), "owner")
    correction = db.post_entry(p,body(kind="adjustment",amount=-2670,related=1,key="manual-refund-00001",accept=True), "owner")
    assert current(p) == {"accrued":2970,"adjustments":-2970,"paid":2670,"available":0,"debt":2670}
    assert purchase(amount=10000,operation="renew",order="order-2",provider="provider-2")
    assert current(p)["available"] == 330
    reversal = db.post_entry(p,body(kind="reversal",related=correction["id"],key="cancel-refund-00001"), "owner")
    assert reversal["id"] > correction["id"]
    assert current(p)["available"] == 3000
    with pytest.raises(ValueError,match="already_reversed"):
        db.post_entry(p,body(kind="reversal",related=correction["id"],key="cancel-refund-00002"), "owner")
    db.post_entry(p,body(kind="reversal",related=paid["id"],key="cancel-payout-00001"), "owner")
    assert current(p)["paid"] == 0
    with connection.get_db() as conn:
        with pytest.raises(sqlite3.IntegrityError,match="immutable_partner_ledger"):
            conn.execute("DELETE FROM partner_ledger")


def test_no_cross_partner_records_or_sensitive_customer_fields(partner_db, client):
    p, q = partner_db
    source = bind(p)
    bind(q,user_id=2,target_id=2)
    purchase(); purchase(user=2,provider="provider-2",order="order-2")
    with pytest.raises(ValueError,match="source_not_found"):
        db.report(q,"arcvpnnbot",{"source":str(source)})
    with pytest.raises(ValueError,match="entry_not_found"):
        db.post_entry(q,body(kind="adjustment",related=1),"owner")
    result = db.report(p,"arcvpnnbot",{})
    encoded = json.dumps(result)
    for forbidden in ("user_id","username","telegram_id","password","provider-1","order-1","uuid","sub_id"):
        assert forbidden not in encoded
    assert result["stats"]["paying_clients"] == 1
    client.post("/api/partners/login",json={"login":"partner1","password":"test-partner-password-1"},
                base_url="https://partners.arccnet.space",headers={"Origin":"https://partners.arccnet.space"})
    response = client.get("/api/partners/cabinet?partner_id=" + str(q),base_url="https://partners.arccnet.space")
    assert response.status_code == 200
    assert response.json["partner"]["name"] == "One"
    assert len(response.json["purchases"]) == 1
    assert client.get("/api/partners/cabinet?source=999",base_url="https://partners.arccnet.space").status_code == 400


def test_purchase_and_date_filters_keep_lifetime_balance(partner_db):
    p, _ = partner_db
    source = bind(p); purchase()
    result = db.report(p,"arcvpnnbot",{"source":str(source),"from":"2000-01-01","to":"2001-01-01"})
    assert result["stats"]["purchases"] == 0
    assert result["purchases"] == []
    assert result["balance"]["available"] == 2970
    with pytest.raises(ValueError,match="invalid_period"):
        db.report(p,"arcvpnnbot",{"from":"bad-date"})


def test_decimal_half_kopeck_rounding_is_server_side(partner_db):
    p, _ = partner_db
    db.update_partner(p,{"rate_bps":5000},"owner")
    bind(p)
    purchase(amount=1)
    assert current(p)["accrued"] == 1


@pytest.mark.parametrize("value",[True,1.5,"100",0,-1])
def test_payout_rejects_non_integer_and_invalid_amounts(partner_db,value):
    p, _ = partner_db
    with pytest.raises(ValueError,match="invalid_amount"):
        db.post_entry(p,body(amount=value),"owner")


def test_bot_confirmation_records_actual_provider_amount_without_webhook(partner_db, monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock
    from bot.services import billing
    p, _ = partner_db
    bind(p)
    assert not purchase(amount=99,verified=False)  # Old advertised RUB units.
    monkeypatch.setattr(billing,"get_yookassa_payment_details",AsyncMock(return_value={
        "status":"succeeded","amount":{"value":"99.00","currency":"RUB"}}))
    monkeypatch.setattr(billing,"process_referral_reward",AsyncMock())
    success, _, _ = asyncio.run(billing.apply_paid_order("order-1"))
    assert success
    assert current(p)["accrued"] == 2970
    asyncio.run(billing.apply_paid_order("order-1"))
    assert current(p)["accrued"] == 2970


@pytest.mark.parametrize("status,amount", [
    ("pending",{"value":"99.00","currency":"RUB"}),
    ("succeeded",{"value":"99.00","currency":"USD"}),
    ("succeeded",{"value":"NaN","currency":"RUB"}),
    ("succeeded",{"value":"0","currency":"RUB"}),
])
def test_bot_confirmation_rejects_unverified_provider_money(partner_db,monkeypatch,status,amount):
    import asyncio
    from unittest.mock import AsyncMock
    from bot.services import billing
    p, _ = partner_db
    bind(p); purchase(verified=False)
    monkeypatch.setattr(billing,"get_yookassa_payment_details",AsyncMock(return_value={"status":status,"amount":amount}))
    success, _, _ = asyncio.run(billing.apply_paid_order("order-1"))
    assert not success
    assert current(p)["accrued"] == 0


def test_schema_migration_idempotent_preserves_existing_data(partner_db):
    p, _ = partner_db
    bind(p); purchase()
    with connection.get_db() as conn:
        db.migrate(conn)
        db.migrate(conn)
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 4
        assert conn.execute("SELECT COUNT(*) FROM partner_clients").fetchone()[0] == 1
        assert conn.execute("SELECT amount_cents FROM partner_ledger").fetchone()[0] == 2970


def test_more_than_500_clients_are_accessible_without_data_leak(partner_db):
    p, q = partner_db
    db.assign_source(p,"campaign",1,"owner")
    with connection.get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        for user_id in range(1000,1501):
            conn.execute("INSERT INTO users(id,username) VALUES(?,?)",(user_id,"large-cohort"))
            db.bind_new_client(conn,user_id,"campaign",1)
    first = db.report(p,"arcvpnnbot",{})
    second = db.report(p,"arcvpnnbot",{"page":"2"})
    assert len(first["clients"]) == 500 and first["has_more"]["clients"]
    assert len(second["clients"]) == 1 and not second["has_more"]["clients"]
    assert first["stats"]["clients"] == second["stats"]["clients"] == 501
    assert not set(r["client"] for r in first["clients"]) & set(r["client"] for r in second["clients"])
    assert not db.report(q,"arcvpnnbot",{"page":"2"})["clients"]
    with pytest.raises(ValueError,match="invalid_page"):
        db.report(p,"arcvpnnbot",{"page":"0"})


def test_partner_purchase_description_uses_recorded_period_and_addon_quantities(partner_db):
    p, _ = partner_db
    bind(p)
    with connection.get_db() as conn:
        for column in ("period_days INTEGER", "addon_device_units INTEGER", "addon_lte_gb INTEGER"):
            conn.execute("ALTER TABLE payments ADD COLUMN " + column)
        conn.execute("INSERT INTO tariffs(id,duration_days,name) VALUES(1,90,'Личный')")
    purchase()
    purchase(operation="addon_combined", order="addon", provider="addon-provider", amount=20000)
    with connection.get_db() as conn:
        conn.execute("UPDATE payments SET tariff_id=1,period_days=30 WHERE order_id='order-1'")
        conn.execute("UPDATE payments SET addon_device_units=2,addon_lte_gb=15 WHERE order_id='addon'")
    report = db.report(p,"fixture",{})
    descriptions = {row["purchase_kind"]: row["purchase_description"] for row in report["purchases"]}
    assert descriptions["new"] == "Личный · 30 дней"  # persisted order term, not today's 90-day tariff
    assert descriptions["addon_combined"] == "Устройства: +2 · Трафик: +15 ГБ"
    assert report["stats"]["revenue_cents"] == 29900
    assert report["stats"]["avg_purchase_cents"] == 14950
    assert report["stats"]["repeat_clients"] == 1
    assert sum(row["revenue_cents"] for row in report["series"]) == 29900


def test_conversion_uses_registration_cohort_not_unrelated_payment_period(partner_db):
    p, _ = partner_db
    source = db.assign_source(p,"campaign",1,"owner")
    with connection.get_db() as conn:
        for user_id, bound_at in ((1,"2026-01-05 10:00:00"),(2,"2026-02-05 10:00:00")):
            conn.execute("""INSERT INTO partner_clients(user_id,partner_id,source_id,public_id,rate_bps,binding_kind,bound_at)
                VALUES(?,?,?, ?,3000,'new',?)""", (user_id,p,source,"C-test-"+str(user_id),bound_at))
    purchase()
    january = db.report(p,"fixture",{"from":"2026-01-01","to":"2026-01-31"})
    assert january["stats"]["purchases"] == 0
    assert january["stats"]["clients"] == january["stats"]["cohort_paying_clients"] == 1
    assert january["stats"]["conversion_percent"] == 100
    february = db.report(p,"fixture",{"from":"2026-02-01","to":"2026-02-28"})
    assert february["stats"]["conversion_percent"] == 0


def test_network_only_owned_nodes_and_owned_referrer_edges_and_net_earned(partner_db):
    p, q = partner_db
    bind(p)
    bind(q,4,2)
    with connection.get_db() as conn:
        db.bind_new_client(conn,2,"campaign",1)
        db.bind_new_client(conn,3,"campaign",1)
        conn.execute("UPDATE users SET referred_by=4 WHERE id=2")
    purchase()
    db.post_entry(p,body(kind="adjustment",amount=-500),"owner")
    report = db.report(p,"fixture",{})
    with connection.get_db() as conn:
        by_id = {row["user_id"]:row["public_id"] for row in conn.execute("SELECT * FROM partner_clients")}
    nodes = {row["client"]:row for row in report["network"]}
    assert by_id[4] not in nodes
    assert nodes[by_id[2]]["parent"] is None
    assert nodes[by_id[3]]["parent"] == by_id[1]
    assert not any("user_id" in row or "referrer_id" in row or "username" in row for row in nodes.values())
    assert report["balance"]["earned"] == 2470
    assert report["balance"]["paid"] == 0


def test_network_limit_disclosed_without_truncating_totals(partner_db):
    p, _ = partner_db
    db.assign_source(p,"campaign",1,"owner")
    with connection.get_db() as conn:
        for user_id in range(1000,3001):
            conn.execute("INSERT INTO users(id) VALUES(?)", (user_id,))
            db.bind_new_client(conn,user_id,"campaign",1)
    report = db.report(p,"fixture",{})
    assert len(report["network"]) == 2000 and report["network_truncated"]
    assert report["stats"]["clients"] == 2001


def test_network_subscription_colors_are_owned_and_never_expose_keys(partner_db):
    p, q = partner_db
    bind(p, 1)
    bind(q, 2, 2)
    with connection.get_db() as conn:
        conn.execute("INSERT INTO vpn_keys VALUES(1,1,'2099-01-01 00:00:00','private-own-key')")
        conn.execute("INSERT INTO vpn_keys VALUES(2,2,'2099-01-01 00:00:00','private-foreign-key')")
        conn.execute("INSERT INTO trial_entitlements VALUES(1,'active')")
    report = db.report(p, "fixture", {})
    assert len(report["network"]) == 1
    assert report["network"][0]["subscription_status"] == "trial_active"
    assert "private-" not in json.dumps(report)
    assert "subscription_end" not in report["network"][0]
    with connection.get_db() as conn:
        conn.execute("DELETE FROM trial_entitlements")
        conn.execute("UPDATE vpn_keys SET expires_at='2000-01-01 00:00:00' WHERE user_id=1")
    assert db.report(p, "fixture", {})["network"][0]["subscription_status"] == "paid_expired"


def test_trial_paid_counts_are_cohort_scoped_not_graph_capped(partner_db):
    p,q=partner_db
    bind(p,1);bind(q,2,2)
    with connection.get_db() as conn:
        conn.execute("INSERT INTO vpn_keys VALUES(1,1,'2099-01-01 00:00:00','private-own')")
        conn.execute("INSERT INTO vpn_keys VALUES(2,2,'2099-01-01 00:00:00','private-other')")
        conn.execute("INSERT INTO trial_entitlements VALUES(1,'active')")
    report=db.report(p,'fixture',{})
    assert report['stats']['trials']==1 and report['stats']['paid']==0
    assert sum(row['clients'] for row in report['client_series'])==1
    assert db.report(p,'fixture',{'from':'2099-01-01'})['stats']['trials']==0
    with connection.get_db() as conn:conn.execute("DELETE FROM trial_entitlements")
    assert db.report(p,'fixture',{})['stats']['paid']==1


def test_purchase_search_and_kind_are_scoped_and_validated(partner_db):
    p,_=partner_db
    bind(p,1)
    with pytest.raises(ValueError,match='invalid_kind'):db.report(p,'fixture',{'kind':'bogus'})
    with pytest.raises(ValueError,match='invalid_search'):db.report(p,'fixture',{'search':'x'*65})
    assert db.report(p,'fixture',{'search':"' OR 1=1 --"})['purchases']==[]


def test_payout_totals_are_period_scoped_and_independent_of_pages(partner_db):
    p,q=partner_db
    with connection.get_db() as conn:
        for i in range(501):
            conn.execute("INSERT INTO partner_ledger(partner_id,kind,amount_cents,operation_key,request_hash,actor,occurred_at) VALUES(?,'payout',-100,?,'fixture','owner','2026-10-01 00:00:00')",(p,'page-payout-'+str(i)))
        first=conn.execute("SELECT MIN(id) FROM partner_ledger WHERE partner_id=?",(p,)).fetchone()[0]
        conn.execute("INSERT INTO partner_ledger(partner_id,kind,amount_cents,related_id,operation_key,request_hash,actor,occurred_at) VALUES(?,'reversal',100,?,'page-cancel','fixture','owner','2026-10-02 00:00:00')",(p,first))
        conn.execute("INSERT INTO partner_ledger(partner_id,kind,amount_cents,operation_key,request_hash,actor,occurred_at) VALUES(?,'payout',-900,'foreign-payout','fixture','owner','2026-10-01 00:00:00')",(q,))
    filters={'from':'2026-10-01','to':'2026-10-31'}
    report=db.report(p,'fixture',filters)
    assert len(report['payouts'])==500 and report['has_more']['payouts']
    assert report['payout_stats']=={'count':501,'paid_cents':50000}
    assert db.report(p,'fixture',{**filters,'page':'2'})['payout_stats']==report['payout_stats']
    assert db.report(p,'fixture',{'from':'2026-11-01'})['payout_stats']=={'count':0,'paid_cents':0}
