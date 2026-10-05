"""Read-only, exclusive registration channels using Moscow calendar dates."""
from datetime import date

def acquisition_report(conn, start="", end=""):
    for value in (start, end):
        if value and date.fromisoformat(value).isoformat() != value:
            raise ValueError("invalid_period")
    if start and end and start > end:
        raise ValueError("invalid_period")
    conditions, params = [], []
    for operator, value in ((">=", start), ("<=", end)):
        if value:
            conditions.append("date(u.created_at,'+3 hours')" + operator + "?")
            params.append(value)
    where = " AND ".join(conditions) or "1=1"
    rows = [dict(row) for row in conn.execute("""SELECT date(u.created_at,'+3 hours') AS day,
        CASE WHEN u.referred_by IS NOT NULL OR EXISTS(SELECT 1 FROM referral_stats rs
            WHERE rs.referral_id=u.id AND rs.level=1) THEN 'referral'
        WHEN EXISTS(SELECT 1 FROM user_campaign_attribution a WHERE a.user_id=u.id) THEN 'campaign'
        ELSE 'direct' END AS channel, COUNT(*) AS count
        FROM users u WHERE """ + where + " GROUP BY day,channel ORDER BY day", params)]
    totals = {"direct": 0, "referral": 0, "campaign": 0}
    days = {}
    for row in rows:
        totals[row["channel"]] += row["count"]
        daily = days.setdefault(row["day"], {"day": row["day"], "direct": 0, "referral": 0, "campaign": 0})
        daily[row["channel"]] = row["count"]
    return {**totals, "total": sum(totals.values()), "series": list(days.values())}
