"""Independent partner accounts, immutable client terms and append-only money journal."""
import hashlib
import json
import re
import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone

from werkzeug.security import check_password_hash, generate_password_hash
from .connection import get_db


def migrate(conn):
    schema = """
        CREATE TABLE IF NOT EXISTS partners(
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, login TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL, access_enabled INTEGER NOT NULL DEFAULT 1,
            recruiting_enabled INTEGER NOT NULL DEFAULT 1, rate_bps INTEGER NOT NULL DEFAULT 3000
                CHECK(rate_bps BETWEEN 0 AND 10000),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS partner_sessions(
            token_hash TEXT PRIMARY KEY, partner_id INTEGER NOT NULL REFERENCES partners(id),
            expires_at TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS partner_login_attempts(
            scope TEXT PRIMARY KEY, window_at TEXT NOT NULL, attempts INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS partner_sources(
            id INTEGER PRIMARY KEY, partner_id INTEGER NOT NULL REFERENCES partners(id),
            kind TEXT NOT NULL CHECK(kind IN ('campaign','referral')), target_id INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1, assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            disabled_at TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_partner_source_active
            ON partner_sources(kind,target_id) WHERE active=1;
        CREATE TABLE IF NOT EXISTS partner_clients(
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE RESTRICT,
            partner_id INTEGER NOT NULL REFERENCES partners(id),
            source_id INTEGER NOT NULL REFERENCES partner_sources(id), public_id TEXT UNIQUE NOT NULL,
            rate_bps INTEGER NOT NULL CHECK(rate_bps BETWEEN 0 AND 10000),
            bound_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, binding_kind TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_partner_clients ON partner_clients(partner_id,source_id);
        CREATE TABLE IF NOT EXISTS partner_historical_payments(
            user_id INTEGER NOT NULL REFERENCES partner_clients(user_id),
            payment_id INTEGER NOT NULL REFERENCES payments(id), PRIMARY KEY(user_id,payment_id)
        );
        CREATE TABLE IF NOT EXISTS partner_events(
            id INTEGER PRIMARY KEY, partner_id INTEGER NOT NULL REFERENCES partners(id),
            action TEXT NOT NULL, actor TEXT NOT NULL, payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS partner_import_previews(
            token_hash TEXT PRIMARY KEY, partner_id INTEGER NOT NULL REFERENCES partners(id),
            source_id INTEGER NOT NULL REFERENCES partner_sources(id), user_ids TEXT NOT NULL,
            rate_bps INTEGER NOT NULL, actor TEXT NOT NULL,
            expires_at TEXT NOT NULL, confirmed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS partner_ledger(
            id INTEGER PRIMARY KEY, partner_id INTEGER NOT NULL REFERENCES partners(id),
            kind TEXT NOT NULL CHECK(kind IN ('accrual','adjustment','refund','payout','reversal')),
            amount_cents INTEGER NOT NULL, operation_key TEXT NOT NULL UNIQUE,
            request_hash TEXT NOT NULL, payment_id INTEGER REFERENCES payments(id) ON DELETE RESTRICT,
            provider_payment_hash TEXT, user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
            source_id INTEGER REFERENCES partner_sources(id), rate_bps INTEGER,
            purchase_cents INTEGER, purchase_kind TEXT, purchase_at TEXT,
            refund_cents INTEGER, related_id INTEGER REFERENCES partner_ledger(id),
            occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            method TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '', actor TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_partner_accrual_payment
            ON partner_ledger(payment_id) WHERE kind='accrual';
        CREATE UNIQUE INDEX IF NOT EXISTS idx_partner_accrual_provider
            ON partner_ledger(provider_payment_hash) WHERE kind='accrual' AND provider_payment_hash IS NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_partner_reversal
            ON partner_ledger(related_id) WHERE kind='reversal';
        CREATE INDEX IF NOT EXISTS idx_partner_ledger ON partner_ledger(partner_id,created_at);
        CREATE TRIGGER IF NOT EXISTS partner_ledger_no_update BEFORE UPDATE ON partner_ledger
            BEGIN SELECT RAISE(ABORT,'immutable_partner_ledger'); END;
        CREATE TRIGGER IF NOT EXISTS partner_ledger_no_delete BEFORE DELETE ON partner_ledger
            BEGIN SELECT RAISE(ABORT,'immutable_partner_ledger'); END;
        CREATE TRIGGER IF NOT EXISTS partner_clients_no_update BEFORE UPDATE ON partner_clients
            BEGIN SELECT RAISE(ABORT,'immutable_partner_client'); END;
        CREATE TRIGGER IF NOT EXISTS partner_clients_no_delete BEFORE DELETE ON partner_clients
            BEGIN SELECT RAISE(ABORT,'immutable_partner_client'); END;
        CREATE TRIGGER IF NOT EXISTS partner_events_no_update BEFORE UPDATE ON partner_events
            BEGIN SELECT RAISE(ABORT,'immutable_partner_event'); END;
        CREATE TRIGGER IF NOT EXISTS partner_events_no_delete BEFORE DELETE ON partner_events
            BEGIN SELECT RAISE(ABORT,'immutable_partner_event'); END;
    """
    # executescript implicitly commits existing transactions; execute complete
    # statements instead so the schema/version checkpoint stays atomic.
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")
    statement = ""
    for line in schema.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            conn.execute(statement)
            statement = ""


def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _event(conn, partner_id, action, actor, payload):
    conn.execute("INSERT INTO partner_events(partner_id,action,actor,payload) VALUES(?,?,?,?)",
                 (partner_id, action, str(actor), json.dumps(payload, ensure_ascii=False, sort_keys=True)))


def _partner(conn, partner_id):
    row = conn.execute("SELECT id,name,login,access_enabled,recruiting_enabled,rate_bps,created_at FROM partners WHERE id=?",
                       (partner_id,)).fetchone()
    if not row:
        raise ValueError("partner_not_found")
    return dict(row)


def _password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 256:
        raise ValueError("password_min_12")
    return generate_password_hash(value)


def create_partner(name, login, password, actor):
    name, login = str(name or "").strip(), str(login or "").strip().lower()
    if not 1 <= len(name) <= 100 or not re.fullmatch(r"[a-z0-9_.-]{3,64}", login):
        raise ValueError("invalid_partner_name_or_login")
    password_hash = _password(password)
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute("INSERT INTO partners(name,login,password_hash) VALUES(?,?,?)", (name, login, password_hash))
        _event(conn, cursor.lastrowid, "partner.create", actor, {"rate_bps": 3000})
        return _partner(conn, cursor.lastrowid)


def update_partner(partner_id, changes, actor):
    allowed = {"name", "access_enabled", "recruiting_enabled", "rate_bps", "password"}
    if set(changes) - allowed or not changes:
        raise ValueError("invalid_partner_changes")
    values = dict(changes)
    if "name" in values:
        values["name"] = str(values["name"]).strip()
        if not 1 <= len(values["name"]) <= 100:
            raise ValueError("invalid_name")
    for key in ("access_enabled", "recruiting_enabled"):
        if key in values:
            if not isinstance(values[key], bool):
                raise ValueError("invalid_boolean")
            values[key] = int(values[key])
    if "rate_bps" in values:
        if type(values["rate_bps"]) is not int or not 0 <= values["rate_bps"] <= 10000:
            raise ValueError("invalid_rate")
    if "password" in values:
        values["password_hash"] = _password(values.pop("password"))
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        before = _partner(conn, partner_id)
        conn.execute("UPDATE partners SET " + ",".join(key + "=?" for key in values) + " WHERE id=?",
                     (*values.values(), partner_id))
        if "password_hash" in values or values.get("access_enabled") == 0:
            conn.execute("DELETE FROM partner_sessions WHERE partner_id=?", (partner_id,))
        after = _partner(conn, partner_id)
        _event(conn, partner_id, "partner.update", actor, {"before": before, "after": after,
                                                        "password_reset": "password_hash" in values})
        return after


def authenticate(login, password, remote):
    login = str(login or "").strip().lower()[:64]
    if not isinstance(password, str) or len(password) > 256:
        return None
    # Persist IP and account limits across process restarts; serialize reservations.
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        for scope in ("ip:" + _hash(remote), "login:" + _hash(login)):
            row = conn.execute("SELECT * FROM partner_login_attempts WHERE scope=? AND window_at>datetime('now','-15 minutes')",
                               (scope,)).fetchone()
            if row and row["attempts"] >= 10:
                raise ValueError("login_rate_limited")
        for scope in ("ip:" + _hash(remote), "login:" + _hash(login)):
            conn.execute("""INSERT INTO partner_login_attempts VALUES(?,CURRENT_TIMESTAMP,1)
                ON CONFLICT(scope) DO UPDATE SET attempts=CASE
                    WHEN window_at>datetime('now','-15 minutes') THEN attempts+1 ELSE 1 END,
                window_at=CASE WHEN window_at>datetime('now','-15 minutes') THEN window_at ELSE CURRENT_TIMESTAMP END""",
                         (scope,))
        row = conn.execute("SELECT * FROM partners WHERE login=?", (login,)).fetchone()
    # Same cost for unknown login, with a fixed valid salted hash.
    valid = check_password_hash(row["password_hash"] if row else DUMMY_HASH, password)
    if not row or not valid or not row["access_enabled"]:
        return None
    token = secrets.token_urlsafe(48)
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        current = conn.execute("SELECT access_enabled,password_hash FROM partners WHERE id=?", (row["id"],)).fetchone()
        if not current["access_enabled"] or current["password_hash"] != row["password_hash"]:
            return None
        conn.execute("INSERT INTO partner_sessions(token_hash,partner_id,expires_at) VALUES(?,?,datetime('now','+12 hours'))",
                     (_hash(token), row["id"]))
        conn.execute("DELETE FROM partner_sessions WHERE expires_at<=CURRENT_TIMESTAMP")
    return token


DUMMY_HASH = generate_password_hash("unused-partner-login-placeholder")


def session_partner(token):
    if not isinstance(token, str) or not 32 <= len(token) <= 128:
        return None
    with get_db() as conn:
        row = conn.execute("""SELECT p.id,p.name FROM partner_sessions s JOIN partners p ON p.id=s.partner_id
            WHERE s.token_hash=? AND s.expires_at>CURRENT_TIMESTAMP AND p.access_enabled=1""", (_hash(token),)).fetchone()
        return dict(row) if row else None


def logout(token):
    with get_db() as conn:
        conn.execute("DELETE FROM partner_sessions WHERE token_hash=?", (_hash(token),))


def list_partners():
    with get_db() as conn:
        return [_partner(conn, row["id"]) for row in conn.execute("SELECT id FROM partners ORDER BY id DESC")]


def assign_source(partner_id, kind, target_id, actor):
    if kind not in {"campaign", "referral"} or type(target_id) is not int:
        raise ValueError("invalid_source")
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        _partner(conn, partner_id)
        table = "ad_campaigns" if kind == "campaign" else "users"
        if not conn.execute("SELECT id FROM " + table + " WHERE id=?", (target_id,)).fetchone():
            raise ValueError("source_not_found")
        existing = conn.execute("SELECT * FROM partner_sources WHERE kind=? AND target_id=? AND active=1",
                                (kind, target_id)).fetchone()
        if existing:
            if existing["partner_id"] != partner_id:
                raise ValueError("source_already_assigned")
            return existing["id"]
        cursor = conn.execute("INSERT INTO partner_sources(partner_id,kind,target_id) VALUES(?,?,?)",
                              (partner_id, kind, target_id))
        _event(conn, partner_id, "source.assign", actor, {"source_id": cursor.lastrowid, "kind": kind, "target_id": target_id})
        return cursor.lastrowid


def disable_source(partner_id, source_id, actor):
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute("UPDATE partner_sources SET active=0,disabled_at=CURRENT_TIMESTAMP WHERE id=? AND partner_id=? AND active=1",
                              (source_id, partner_id))
        if cursor.rowcount:
            _event(conn, partner_id, "source.disable", actor, {"source_id": source_id})
        elif not conn.execute("SELECT id FROM partner_sources WHERE id=? AND partner_id=?", (source_id, partner_id)).fetchone():
            raise ValueError("source_not_found")


def _bind(conn, user_id, source, rate, actor, binding_kind):
    # A binding is permanent: assignment/access changes never transfer a client.
    cursor = conn.execute("""INSERT OR IGNORE INTO partner_clients(user_id,partner_id,source_id,public_id,rate_bps,binding_kind)
        VALUES(?,?,?,?,?,?)""", (user_id, source["partner_id"], source["id"], "C-" + secrets.token_hex(6), rate, binding_kind))
    if cursor.rowcount:
        conn.execute("""INSERT INTO partner_historical_payments(user_id,payment_id)
            SELECT user_id,id FROM payments WHERE user_id=? AND status IN ('paid','succeeded')""", (user_id,))
        _event(conn, source["partner_id"], "client.bind", actor,
               {"user_id": user_id, "source_id": source["id"], "rate_bps": rate, "binding_kind": binding_kind})
    return cursor.rowcount > 0


def bind_new_client(conn, user_id, kind, target_id):
    source = conn.execute("""SELECT s.*,p.rate_bps FROM partner_sources s JOIN partners p ON p.id=s.partner_id
        WHERE s.kind=? AND s.target_id=? AND s.active=1 AND p.recruiting_enabled=1""", (kind, target_id)).fetchone()
    if source:
        return _bind(conn, user_id, source, source["rate_bps"], "attribution", "new")
    return False


def preview_import(partner_id, source_id, actor):
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        partner = _partner(conn, partner_id)
        source = conn.execute("SELECT * FROM partner_sources WHERE id=? AND partner_id=? AND active=1",
                              (source_id, partner_id)).fetchone()
        if not source:
            raise ValueError("source_not_found")
        if source["kind"] == "campaign":
            query = "SELECT u.id,u.username,u.first_name FROM users u JOIN user_campaign_attribution a ON a.user_id=u.id WHERE a.campaign_id=?"
        else:
            query = "SELECT id,username,first_name FROM users WHERE referred_by=?"
        candidates = [dict(row) for row in conn.execute(query + " AND NOT EXISTS(SELECT 1 FROM partner_clients pc WHERE pc.user_id=" +
                      ("u.id" if source["kind"] == "campaign" else "users.id") + ") ORDER BY id", (source["target_id"],))]
        token = secrets.token_urlsafe(32)
        conn.execute("""INSERT INTO partner_import_previews(token_hash,partner_id,source_id,user_ids,rate_bps,actor,expires_at)
            VALUES(?,?,?,?,?,?,datetime('now','+30 minutes'))""",
                     (_hash(token), partner_id, source_id, json.dumps([row["id"] for row in candidates]), partner["rate_bps"], str(actor)))
        return {"token": token, "clients": candidates, "rate_bps": partner["rate_bps"],
                "historical_accruals": False}


def confirm_import(partner_id, token, actor):
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        preview = conn.execute("""SELECT * FROM partner_import_previews
            WHERE token_hash=? AND partner_id=? AND actor=? AND expires_at>CURRENT_TIMESTAMP""",
                               (_hash(token), partner_id, str(actor))).fetchone()
        if not preview:
            raise ValueError("invalid_preview")
        if preview["confirmed_at"]:
            return {"imported": 0, "already_confirmed": True}
        source = conn.execute("SELECT * FROM partner_sources WHERE id=? AND partner_id=? AND active=1",
                              (preview["source_id"], partner_id)).fetchone()
        if not source:
            raise ValueError("source_not_found")
        user_ids = json.loads(preview["user_ids"])
        # Fail all rather than silently change the reviewed list or overwrite anyone.
        for user_id in user_ids:
            if conn.execute("SELECT 1 FROM partner_clients WHERE user_id=?", (user_id,)).fetchone():
                raise ValueError("preview_changed")
            if not conn.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
                raise ValueError("preview_changed")
        for user_id in user_ids:
            _bind(conn, user_id, source, preview["rate_bps"], actor, "confirmed_import")
        conn.execute("UPDATE partner_import_previews SET confirmed_at=CURRENT_TIMESTAMP WHERE token_hash=?", (_hash(token),))
        return {"imported": len(user_ids)}


def source_options():
    with get_db() as conn:
        campaigns = [dict(row) for row in conn.execute("SELECT id,name,code,is_active FROM ad_campaigns ORDER BY id DESC")]
        referrals = [dict(row) for row in conn.execute(
            "SELECT id,username,first_name,referral_code FROM users WHERE referral_code IS NOT NULL ORDER BY id DESC")]
        assigned = [dict(row) for row in conn.execute("SELECT partner_id,kind,target_id FROM partner_sources WHERE active=1")]
        return {"campaigns": campaigns, "referrals": referrals, "assigned": assigned}


def balance(conn, partner_id):
    rows = conn.execute("""SELECT l.kind,l.amount_cents,r.kind AS related_kind FROM partner_ledger l
        LEFT JOIN partner_ledger r ON r.id=l.related_id WHERE l.partner_id=?""", (partner_id,))
    accrued, adjustments, payouts = 0, 0, 0
    for row in rows:
        if row["kind"] == "accrual":
            accrued += row["amount_cents"]
        elif row["kind"] == "payout" or row["kind"] == "reversal" and row["related_kind"] == "payout":
            payouts += row["amount_cents"]
        else:
            adjustments += row["amount_cents"]
    net = accrued + adjustments + payouts
    return {"accrued": accrued, "adjustments": adjustments, "paid": -payouts,
            "available": max(0, net), "debt": max(0, -net)}


def report(partner_id, bot_username, filters, admin=False):
    source = str(filters.get("source") or "")
    page_value = str(filters.get("page") or "1")
    if not page_value.isdigit() or not 1 <= int(page_value) <= 100000:
        raise ValueError("invalid_page")
    page = int(page_value)
    offset = (page - 1) * 500
    start, end = str(filters.get("from") or ""), str(filters.get("to") or "")
    for value in (start, end):
        if value:
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            except ValueError:
                raise ValueError("invalid_period")
    if start and end and start > end:
        raise ValueError("invalid_period")
    if source and (not source.isdigit() or len(source) > 10):
        raise ValueError("invalid_source")
    with get_db() as conn:
        partner = _partner(conn, partner_id)
        sources = []
        for row in conn.execute("""SELECT s.*,c.name AS campaign_name,c.code AS campaign_code,c.is_active,
            u.referral_code FROM partner_sources s
            LEFT JOIN ad_campaigns c ON s.kind='campaign' AND c.id=s.target_id
            LEFT JOIN users u ON s.kind='referral' AND u.id=s.target_id
            WHERE s.partner_id=? ORDER BY s.id DESC""", (partner_id,)):
            sources.append({"id": row["id"], "name": row["campaign_name"] if row["kind"] == "campaign" else "Реферальная ссылка · " + str(row["referral_code"]),
                "kind": row["kind"], "active": bool(row["active"]),
                "enabled": bool(row["is_active"]) if row["kind"] == "campaign" else True,
                "assigned_at": row["assigned_at"], "disabled_at": row["disabled_at"],
                "url": "https://t.me/" + bot_username + "?start=" +
                    ("ad_" + str(row["campaign_code"]) if row["kind"] == "campaign" else "ref_" + str(row["referral_code"]))})
        if source and int(source) not in {row["id"] for row in sources}:
            raise ValueError("source_not_found")
        def conditions(alias, stamp_field, with_source=True):
            sql, params = alias + ".partner_id=?", [partner_id]
            if source and with_source:
                sql += " AND " + alias + ".source_id=?"
                params.append(int(source))
            if start:
                sql += " AND date(" + alias + "." + stamp_field + ",'+3 hours')>=?"
                params.append(start)
            if end:
                sql += " AND date(" + alias + "." + stamp_field + ",'+3 hours')<=?"
                params.append(end)
            return sql, params
        purchase_where, purchase_params = conditions("l", "purchase_at")
        purchase_where += " AND l.kind='accrual'"
        kind, search = str(filters.get("kind") or ""), str(filters.get("search") or "").strip()
        if kind and kind not in {"new", "renew", "upgrade", "addon_device", "addon_lte", "addon_combined"}:
            raise ValueError("invalid_kind")
        if len(search) > 64:
            raise ValueError("invalid_search")
        if kind:
            purchase_where += " AND l.purchase_kind=?"
            purchase_params.append(kind)
        if search:
            purchase_where += " AND EXISTS(SELECT 1 FROM partner_clients sc WHERE sc.user_id=l.user_id AND sc.partner_id=l.partner_id AND sc.public_id LIKE ?)"
            purchase_params.append("%" + search + "%")
        count = dict(conn.execute("""SELECT COUNT(*) AS purchases,COUNT(DISTINCT l.user_id) AS paying_clients,
            COALESCE(SUM(CASE WHEN l.purchase_kind='renew' THEN 1 ELSE 0 END),0) AS renewals
            FROM partner_ledger l WHERE """ + purchase_where, purchase_params).fetchone())
        client_where, client_params = conditions("c", "bound_at")
        count["clients"] = conn.execute("SELECT COUNT(*) FROM partner_clients c WHERE " + client_where, client_params).fetchone()[0]
        cohort_paid = conn.execute("""SELECT COUNT(*) FROM partner_clients c WHERE """ + client_where + """
            AND EXISTS(SELECT 1 FROM partner_ledger l WHERE l.partner_id=c.partner_id
                AND l.user_id=c.user_id AND l.kind='accrual')""", client_params).fetchone()[0]
        count["cohort_paying_clients"] = cohort_paid
        count["conversion_percent"] = round(100 * cohort_paid / count["clients"], 2) if count["clients"] else 0
        count["revenue_cents"] = conn.execute("SELECT COALESCE(SUM(l.purchase_cents),0) FROM partner_ledger l WHERE " + purchase_where, purchase_params).fetchone()[0]
        count["reward_cents"] = conn.execute("SELECT COALESCE(SUM(l.amount_cents),0) FROM partner_ledger l WHERE " + purchase_where, purchase_params).fetchone()[0]
        count["avg_purchase_cents"] = (count["revenue_cents"] + count["purchases"] // 2) // count["purchases"] if count["purchases"] else 0
        count["repeat_clients"] = conn.execute("SELECT COUNT(*) FROM (SELECT l.user_id FROM partner_ledger l WHERE " + purchase_where + " GROUP BY l.user_id HAVING COUNT(*)>1)", purchase_params).fetchone()[0]
        status_sql = """SELECT
            SUM(CASE WHEN subscription_end>datetime('now') AND is_trial THEN 1 ELSE 0 END) AS trials,
            SUM(CASE WHEN subscription_end>datetime('now') AND NOT is_trial THEN 1 ELSE 0 END) AS paid,
            SUM(CASE WHEN subscription_end<=datetime('now') THEN 1 ELSE 0 END) AS expired,
            SUM(CASE WHEN subscription_end IS NULL THEN 1 ELSE 0 END) AS without_subscription
            FROM (SELECT (SELECT MAX(vk.expires_at) FROM vpn_keys vk WHERE vk.user_id=c.user_id) AS subscription_end,
                EXISTS(SELECT 1 FROM trial_entitlements te JOIN vpn_keys tvk ON tvk.id=te.vpn_key_id
                    WHERE tvk.user_id=c.user_id AND te.status='active' AND tvk.expires_at=(
                        SELECT MAX(vk2.expires_at) FROM vpn_keys vk2 WHERE vk2.user_id=c.user_id)) AS is_trial
                FROM partner_clients c WHERE """ + client_where + ")"
        count.update({key: value or 0 for key, value in dict(conn.execute(status_sql, client_params).fetchone()).items()})
        client_series = [dict(row) for row in conn.execute("SELECT date(c.bound_at,'+3 hours') AS day,COUNT(*) AS clients FROM partner_clients c WHERE " + client_where + " GROUP BY day ORDER BY day", client_params)]
        series = [dict(row) for row in conn.execute("""SELECT date(l.purchase_at,'+3 hours') AS day,
            COUNT(*) AS purchases,SUM(l.purchase_cents) AS revenue_cents,SUM(l.amount_cents) AS reward_cents
            FROM partner_ledger l WHERE """ + purchase_where + " GROUP BY day ORDER BY day", purchase_params)]
        clients = []
        names = {row["id"]: row["name"] for row in sources}
        for row in conn.execute("""SELECT c.public_id AS client,c.source_id,c.bound_at,c.rate_bps,
                (SELECT COUNT(*) FROM partner_ledger l WHERE l.user_id=c.user_id AND l.partner_id=c.partner_id
                    AND l.kind='accrual') AS purchases
            FROM partner_clients c WHERE """ + client_where + " ORDER BY c.bound_at DESC,c.user_id DESC LIMIT 501 OFFSET ?",
                                [*client_params, offset]):
            item = dict(row)
            item["source_name"] = names[item["source_id"]]
            clients.append(item)
        fields = """l.id,l.kind,l.amount_cents,l.source_id,l.rate_bps,l.purchase_cents,l.purchase_kind,l.purchase_at,
            l.related_id,l.occurred_at,l.method,l.note,l.created_at,c.public_id AS client"""
        if admin:
            fields += ",l.payment_id,c.user_id"
        join = " FROM partner_ledger l LEFT JOIN partner_clients c ON c.user_id=l.user_id AND c.partner_id=l.partner_id WHERE "
        purchases = [dict(row) for row in conn.execute("SELECT " + fields + join + purchase_where +
                    " ORDER BY l.purchase_at DESC,l.id DESC LIMIT 501 OFFSET ?", [*purchase_params, offset])]
        purchase_ids = [purchase["id"] for purchase in purchases]
        purchase_details = {row["ledger_id"]: dict(row) for row in conn.execute("""SELECT p.*,l.id AS ledger_id,
            t.name AS partner_tariff_name FROM partner_ledger l JOIN payments p ON p.id=l.payment_id
            LEFT JOIN tariffs t ON t.id=p.tariff_id WHERE l.partner_id=? AND l.id IN (""" +
            ",".join("?" for _ in purchase_ids) + ")", [partner_id, *purchase_ids])} if purchase_ids else {}
        for purchase in purchases:
            details = purchase_details.get(purchase["id"], {})
            kind = purchase["purchase_kind"]
            description = []
            if kind in {"new", "renew", "upgrade"}:
                if details.get("partner_tariff_name"):
                    description.append(details["partner_tariff_name"])
                if details.get("period_days"):
                    description.append(str(details["period_days"]) + " дней")
            devices = details.get("addon_device_units") or (details.get("addon_units") if details.get("addon_kind") == "device" else 0)
            traffic = details.get("addon_lte_gb") or (details.get("addon_units") if details.get("addon_kind") == "lte" else 0)
            if devices:
                description.append("Устройства: +" + str(devices))
            if traffic:
                description.append("Трафик: +" + str(traffic) + " ГБ")
            purchase["purchase_description"] = " · ".join(description) or None
        network_rows = [dict(row) for row in conn.execute("""SELECT c.user_id,c.public_id AS client,
            c.source_id,c.bound_at,u.referred_by AS referrer_id,
            (SELECT MAX(vk.expires_at) FROM vpn_keys vk WHERE vk.user_id=c.user_id) AS subscription_end,
            EXISTS(SELECT 1 FROM trial_entitlements te JOIN vpn_keys tvk ON tvk.id=te.vpn_key_id
                WHERE tvk.user_id=c.user_id AND te.status='active'
                AND tvk.expires_at=(SELECT MAX(vk2.expires_at) FROM vpn_keys vk2 WHERE vk2.user_id=c.user_id)) AS subscription_is_trial,
            (SELECT COUNT(*) FROM partner_ledger l WHERE l.partner_id=c.partner_id AND l.user_id=c.user_id AND l.kind='accrual') AS purchases,
            (SELECT COALESCE(SUM(l.purchase_cents),0) FROM partner_ledger l WHERE l.partner_id=c.partner_id AND l.user_id=c.user_id AND l.kind='accrual') AS spent_cents
            FROM partner_clients c JOIN users u ON u.id=c.user_id WHERE """ + client_where +
            " ORDER BY c.bound_at DESC,c.user_id DESC LIMIT 2001", client_params)]
        visible = {row["user_id"]: row["client"] for row in network_rows[:2000]}
        now_sql = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        network = [{"subscription_status": (("trial_" if row["subscription_is_trial"] else "paid_") +
                    ("active" if str(row["subscription_end"]) > now_sql else "expired"))
                    if row["subscription_end"] else None, "client": row["client"], "source_id": row["source_id"], "bound_at": row["bound_at"],
                    "parent": visible.get(row["referrer_id"]) if row["referrer_id"] != row["user_id"] else None,
                    "purchases": row["purchases"], "spent_cents": row["spent_cents"]} for row in network_rows[:2000]]
        journal_where, journal_params = conditions("l", "occurred_at", with_source=False)
        if source:
            journal_where += " AND (l.source_id=? OR l.source_id IS NULL)"
            journal_params.append(int(source))
        journal = [dict(row) for row in conn.execute("SELECT " + fields + join + journal_where +
                    " ORDER BY l.occurred_at DESC,l.id DESC LIMIT 501 OFFSET ?", [*journal_params, offset])]
        payout_where, payout_params = conditions("l", "occurred_at", with_source=False)
        payout_where += """ AND (l.kind='payout' OR l.kind='reversal' AND EXISTS(
            SELECT 1 FROM partner_ledger r WHERE r.id=l.related_id AND r.kind='payout'))"""
        payout_stats = dict(conn.execute("""SELECT COUNT(CASE WHEN l.kind='payout' THEN 1 END) AS count,
            -COALESCE(SUM(l.amount_cents),0) AS paid_cents FROM partner_ledger l WHERE """ +
            payout_where, payout_params).fetchone())
        payouts = [dict(row) for row in conn.execute("SELECT " + fields + join + payout_where +
            " ORDER BY l.occurred_at DESC,l.id DESC LIMIT 501 OFFSET ?", [*payout_params, offset])]
        result = {"partner": partner if admin else {"name": partner["name"]}, "sources": sources, "balance": balance(conn, partner_id),
            "stats": count, "clients": clients[:500], "purchases": purchases[:500], "journal": journal[:500],
            "payouts": payouts[:500], "payout_stats": payout_stats, "page":page,
            "has_more": {"clients":len(clients)>500,"purchases":len(purchases)>500,
                         "journal":len(journal)>500,"payouts":len(payouts)>500},
            "truncated": any(len(rows) > 500 for rows in (clients, purchases, journal, payouts))}
        result["balance"]["earned"] = result["balance"]["accrued"] + result["balance"]["adjustments"]
        result.update(series=series, client_series=client_series, network=network, network_truncated=len(network_rows)>2000)
        if admin:
            history = [dict(row) for row in conn.execute("SELECT * FROM partner_events WHERE partner_id=? ORDER BY id DESC LIMIT 501 OFFSET ?", (partner_id,offset))]
            for row in history:
                row["payload"] = json.loads(row["payload"])
            result["history"] = history[:500]
            result["has_more"]["history"] = len(history)>500
            result["truncated"] |= len(history) > 500
        return result


def accrue_order(conn, order_id):
    """Confirmed RUB merchant amount only; no historical/bonus/balance inference."""
    row = conn.execute("""SELECT p.*,c.partner_id,c.source_id,c.rate_bps,c.bound_at
        FROM payments p JOIN partner_clients c ON c.user_id=p.user_id
        WHERE p.order_id=? AND p.status='paid'
            AND p.operation_type IN ('new','renew','upgrade','addon_device','addon_lte','addon_combined')
            AND COALESCE(p.offer_code,'')!='email_paid_trial'
            AND p.payment_type IN ('yookassa','yookassa_qr','cards')
            AND p.yookassa_payment_id IS NOT NULL AND p.yookassa_payment_id!=''
            AND p.partner_verified_cents>0 AND p.paid_at>=c.bound_at
            AND NOT EXISTS(SELECT 1 FROM partner_historical_payments h WHERE h.user_id=p.user_id AND h.payment_id=p.id)
        """, (order_id,)).fetchone()
    if not row:
        return False
    amount = int(row["partner_verified_cents"])
    # Half-up to the nearest kopek; no floats in accounting.
    reward = (amount * int(row["rate_bps"]) + 5000) // 10000
    provider_hash = _hash(row["yookassa_payment_id"])
    existing = conn.execute("""SELECT * FROM partner_ledger WHERE kind='accrual'
        AND (payment_id=? OR provider_payment_hash=?)""", (row["id"], provider_hash)).fetchone()
    if existing:
        if existing["purchase_cents"] != amount or existing["user_id"] != row["user_id"]:
            raise ValueError("partner_payment_conflict")
        return False
    payload = {"payment_id": row["id"], "purchase_cents": amount, "rate_bps": row["rate_bps"]}
    conn.execute("""INSERT INTO partner_ledger(partner_id,kind,amount_cents,operation_key,request_hash,
        payment_id,provider_payment_hash,user_id,source_id,rate_bps,purchase_cents,purchase_kind,purchase_at,occurred_at,actor)
        VALUES(?,'accrual',?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        row["partner_id"], reward, "purchase:" + str(row["id"]), _hash(json.dumps(payload, sort_keys=True)),
        row["id"], provider_hash, row["user_id"], row["source_id"], row["rate_bps"], amount,
        row["operation_type"], row["paid_at"], row["paid_at"], "billing"))
    return True


def needs_verified_amount(order_id):
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='partners' AND type='table'").fetchone():
            return False
        return conn.execute("""SELECT 1 FROM payments p JOIN partner_clients c ON c.user_id=p.user_id
            WHERE p.order_id=? AND p.partner_verified_cents IS NULL
                AND p.operation_type IN ('new','renew','upgrade','addon_device','addon_lte','addon_combined')
                AND p.payment_type IN ('yookassa','yookassa_qr','cards')
                AND p.yookassa_payment_id IS NOT NULL AND p.yookassa_payment_id!=''
                AND NOT EXISTS(SELECT 1 FROM partner_historical_payments h WHERE h.user_id=p.user_id AND h.payment_id=p.id)""",
                            (order_id,)).fetchone() is not None


def post_entry(partner_id, body, actor):
    """Manual journal only. Never calls a payout/refund provider."""
    kind = body.get("kind")
    if kind not in {"payout", "adjustment", "reversal"}:
        raise ValueError("invalid_entry_kind")
    key = body.get("operation_key")
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,100}", key):
        raise ValueError("invalid_operation_key")
    note, method = body.get("note"), body.get("method", "")
    if not isinstance(note, str) or not 1 <= len(note.strip()) <= 1000:
        raise ValueError("note_required")
    if not isinstance(method, str) or len(method) > 100 or kind == "payout" and not method.strip():
        raise ValueError("method_required")
    occurred = body.get("occurred_on")
    try:
        if not isinstance(occurred, str) or date.fromisoformat(occurred).isoformat() != occurred:
            raise ValueError()
        if occurred > datetime.now(timezone(timedelta(hours=3))).date().isoformat():
            raise ValueError()
    except ValueError:
        raise ValueError("invalid_date")
    related_id = body.get("related_id")
    if related_id is not None and (type(related_id) is not int or related_id <= 0):
        raise ValueError("invalid_related_id")
    value = body.get("amount_cents")
    if kind != "reversal" and (type(value) is not int or value == 0 or abs(value) > 100_000_000_00):
        raise ValueError("invalid_amount")
    if kind == "payout" and value <= 0:
        raise ValueError("invalid_amount")
    request_payload = {"kind": kind, "amount_cents": None if kind == "reversal" else value,
        "occurred_on": occurred, "related_id": related_id, "method": method.strip(), "note": note.strip()}
    request_hash = _hash(json.dumps(request_payload, sort_keys=True, ensure_ascii=False))
    operation_key = "manual:" + str(partner_id) + ":" + key
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        _partner(conn, partner_id)
        prior = conn.execute("SELECT * FROM partner_ledger WHERE operation_key=?", (operation_key,)).fetchone()
        if prior:
            if prior["request_hash"] != request_hash:
                raise ValueError("operation_conflict")
            return {"id": prior["id"], "already_saved": True}
        related = None
        if related_id is not None:
            related = conn.execute("SELECT * FROM partner_ledger WHERE id=? AND partner_id=?", (related_id, partner_id)).fetchone()
            if not related:
                raise ValueError("entry_not_found")
        if kind == "reversal":
            if not related or related["kind"] not in {"payout", "adjustment"}:
                raise ValueError("reversal_not_allowed")
            if conn.execute("SELECT id FROM partner_ledger WHERE kind='reversal' AND related_id=?", (related_id,)).fetchone():
                raise ValueError("already_reversed")
            amount = -related["amount_cents"]
        elif kind == "payout":
            if related:
                raise ValueError("invalid_related_id")
            amount = -value
        else:
            amount = value
        current = balance(conn, partner_id)
        if kind == "payout" and value > current["available"]:
            raise ValueError("insufficient_balance")
        if current["available"] - current["debt"] + amount < 0 and body.get("accept_negative") is not True:
            raise ValueError("negative_balance_confirmation_required")
        cursor = conn.execute("""INSERT INTO partner_ledger(partner_id,kind,amount_cents,operation_key,request_hash,
            related_id,user_id,source_id,rate_bps,payment_id,occurred_at,method,note,actor)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            partner_id, kind, amount, operation_key, request_hash, related_id,
            related["user_id"] if related else None, related["source_id"] if related else None,
            related["rate_bps"] if related else None, related["payment_id"] if related else None,
            occurred + " 12:00:00", method.strip() if kind == "payout" else "", note.strip(), str(actor)))
        _event(conn, partner_id, "ledger." + kind, actor, {"entry_id": cursor.lastrowid, "amount_cents": amount,
                                                       "related_id": related_id})
        return {"id": cursor.lastrowid, "already_saved": False}
