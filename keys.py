"""
keys.py — AutoPost Pro subscriber key management
=================================================
This is your master list of all keys. Edit this file and redeploy to:
  - Add a new subscriber
  - Renew a subscription (update expiry)
  - Revoke access (set status to "revoked")
  - Grant a free trial (set status to "trial", leave expiry as None)

STATUS VALUES:
  "trial"    → 3-day free trial from first use. Expiry auto-set in KV.
  "active"   → Paid subscriber. Access until expiry date.
  "revoked"  → Immediately blocked. Key stays here for your records.

EXPIRY FORMAT: "YYYY-MM-DD" or None (None = not yet set, used for trials)

HOW TO ADD A SUBSCRIBER:
  1. Generate a key:
     python3 -c "import secrets,string; c=string.ascii_uppercase+string.digits; print('APPro-'+''.join(secrets.choice(c) for _ in range(4))+'-'+''.join(secrets.choice(c) for _ in range(4)))"
  2. Add an entry below
  3. git push / vercel --prod
  4. DM the key to your subscriber

HOW TO RENEW A SUBSCRIPTION:
  1. Find their key below
  2. Update expiry to new date e.g. "2026-04-01"
  3. Make sure status is "active"
  4. Redeploy

HOW TO REVOKE:
  1. Change status to "revoked"
  2. Redeploy — they're locked out within seconds
"""

from datetime import date, timedelta

# ─────────────────────────────────────────────────────────────────
# KEY REGISTRY
# ─────────────────────────────────────────────────────────────────
# Each entry: "KEY": {"name": str, "status": str, "expiry": str|None}
KEYS: dict = {

    # ── Example trial key (delete/replace these) ──────────────────
    "APPro-TEST-TRL1": {
        "name": "Test User (Trial)",
        "status": "trial",
        "expiry": None,           # auto-set on first use via KV
    },

    # ── Example active subscriber ─────────────────────────────────
    # "APPro-A3F7-K2M9": {
    #     "name": "John Doe",
    #     "status": "active",
    #     "expiry": "2026-03-23",  # 1 month from signup
    # },

}


# ─────────────────────────────────────────────────────────────────
# HELPERS  (used by index.py — don't edit below this line)
# ─────────────────────────────────────────────────────────────────

TRIAL_DAYS = 3


def get_key_info(key: str) -> dict | None:
    """Return the key record or None if key doesn't exist."""
    return KEYS.get(key)


def is_key_valid(key: str) -> bool:
    """True only if key exists and is not revoked."""
    info = KEYS.get(key)
    return info is not None and info.get("status") != "revoked"


def all_active_keys() -> set:
    """Set of all non-revoked keys — used for quota calculation."""
    return {k for k, v in KEYS.items() if v.get("status") != "revoked"}


def trial_expiry_date(first_use_iso: str) -> date:
    """Return the date the trial expires given first-use date string."""
    first = date.fromisoformat(first_use_iso)
    return first + timedelta(days=TRIAL_DAYS)