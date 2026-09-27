"""Dry-run by default; recover missing referral rewards from verified local evidence.

Run on the control plane only after deploying the atomic reward implementation.
No subscription identifiers or customer identities are printed.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.connection import get_db


def candidates(kind: str) -> list[int]:
    if kind == "purchase":
        evidence = """EXISTS (
            SELECT 1 FROM payments p WHERE p.user_id = u.id
              AND p.status = 'paid' AND p.fulfillment_status = 'applied'
              AND p.operation_type IN ('new', 'renew', 'upgrade')
              AND p.amount_cents > 0 AND p.payment_type != 'trial'
        )"""
        flag = "bonus_purchase_granted"
    elif kind == "trial":
        # Real VPN bytes, not a WebApp device import or an unused trial key.
        evidence = "EXISTS (SELECT 1 FROM vpn_keys k WHERE k.user_id=u.id AND k.traffic_used>0)"
        flag = "bonus_trial_granted"
    else:
        raise ValueError(kind)

    with get_db() as conn:
        rows = conn.execute(f"""
            SELECT u.id FROM users u
            WHERE u.referred_by IS NOT NULL AND {evidence}
              AND EXISTS (SELECT 1 FROM vpn_keys k WHERE k.user_id=u.referred_by)
              AND EXISTS (SELECT 1 FROM vpn_keys k WHERE k.user_id=u.id)
              AND NOT EXISTS (
                  SELECT 1 FROM referral_stats r
                  WHERE r.referrer_id=u.referred_by AND r.referral_id=u.id
                    AND r.level=1 AND COALESCE(r.{flag},0)=1
              )
            ORDER BY u.id
        """).fetchall()
    return [int(row[0]) for row in rows]


async def apply(purchases: list[int], entries: list[int]) -> None:
    from bot.services.billing import process_referral_reward, process_referral_trial_reward

    # Entry first mirrors the chronological product contract: +N inviter,
    # then first paid purchase +N to both. Each call is DB-idempotent.
    for user_id in entries:
        await process_referral_trial_reward(user_id)
    for user_id in purchases:
        await process_referral_reward(user_id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expect-purchase", type=int)
    parser.add_argument("--expect-entry", type=int)
    args = parser.parse_args()
    purchases = candidates("purchase")
    entries = candidates("trial")
    print(f"Missing confirmed first-purchase rewards: {len(purchases)}")
    print(f"Missing VPN-use entry rewards: {len(entries)}")
    if not args.apply:
        print("Dry run; no changes made")
        return
    if args.expect_purchase is None or args.expect_entry is None:
        parser.error("--apply requires both expected counts")
    if (len(purchases), len(entries)) != (args.expect_purchase, args.expect_entry):
        parser.error("candidate counts changed; review before applying")
    asyncio.run(apply(purchases, entries))
    remaining = (len(candidates("purchase")), len(candidates("trial")))
    print(f"Remaining purchase/entry candidates: {remaining[0]}/{remaining[1]}")
    if remaining != (0, 0):
        raise SystemExit("Some rewards remain unapplied; investigate without retrying blindly")


if __name__ == "__main__":
    main()
