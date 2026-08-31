"""
Bulk push-back: writes approved merge decisions from crm_working_copy back
into HubSpot using HubSpot's native contact-merge endpoint, then marks
those rows as pushed.

This is the step that actually changes the real CRM data - matching and
review only ever updated the local `crm_working_copy` shadow table.
HubSpot has no "merge two contacts" primitive n8n can express on its own,
so this script talks to both systems directly instead of routing through
an n8n webhook: it queries Postgres for pending merges, calls HubSpot's
merge API, then writes pushed_back_at back to Postgres itself. Unlike the
pull script (which only ever talks to n8n, never Postgres), this one skips
n8n entirely - the read and the write are both simple point operations, so
a webhook round trip for each would just be an extra hop for no benefit.

Only successful HubSpot merges get marked pushed_back_at - a row that
fails (contact already merged/deleted since the matching pass ran, token
expired, etc.) stays pending and is retried on the next run instead of
silently being treated as done.

The HubSpot merge call goes through request_with_retry(), same pattern as
the pull script: a 429 or transient 5xx waits and retries (honoring
Retry-After when HubSpot sends one, exponential backoff otherwise)
instead of failing the row outright. A real 4xx like "contact already
merged" still fails fast and gets skipped for this run - retrying that
five times would just waste time on something that isn't transient.

Env vars required:
  HUBSPOT_ACCESS_TOKEN - Private App token, write scope on contacts
  DATABASE_URL          - postgresql://user:pass@host:port/dbname - must be
                           reachable from the runner (a local docker-compose
                           Postgres needs a TCP tunnel, e.g. `ngrok tcp 5432`,
                           pointed at by this URL - it won't resolve
                           `localhost` from inside GitHub Actions)
"""

import os
import sys
import time

import psycopg2
import psycopg2.extras
import requests

HUBSPOT_API_BASE = "https://api.hubapi.com"
MAX_RETRIES = 5

SELECT_PENDING = """
    SELECT
        wc.id,
        wc.hubspot_contact_id,
        survivor.hubspot_contact_id AS survivor_hubspot_contact_id
    FROM crm_working_copy wc
    JOIN crm_working_copy survivor ON survivor.id = wc.merged_into_id
    WHERE wc.status = 'merged'
      AND wc.pushed_back_at IS NULL;
"""

MARK_PUSHED = """
    UPDATE crm_working_copy
    SET pushed_back_at = NOW()
    WHERE id = ANY(%s);
"""


def request_with_retry(method, url, **kwargs):
    """requests.request wrapper that survives HubSpot rate limits (429) and
    transient 5xx errors instead of failing the row outright. Respects
    HubSpot's Retry-After header when present; falls back to exponential
    backoff (1s, 2s, 4s, 8s, 16s) otherwise. A real 4xx (e.g. contact
    already merged) still raises immediately - that's not transient."""
    for attempt in range(MAX_RETRIES):
        resp = requests.request(method, url, **kwargs)

        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == MAX_RETRIES - 1:
                resp.raise_for_status()
            wait = float(resp.headers.get("Retry-After", 2 ** attempt))
            reason = "rate limited" if resp.status_code == 429 else f"server error {resp.status_code}"
            print(f"{reason}, retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})...")
            time.sleep(wait)
            continue

        resp.raise_for_status()
        return resp

    raise RuntimeError(f"Gave up after {MAX_RETRIES} retries against {url}")


def get_pending_pushbacks(conn):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(SELECT_PENDING)
        return cur.fetchall()


def merge_in_hubspot(token, survivor_id, loser_id):
    resp = request_with_retry(
        "POST",
        f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts/merge",
        headers={"Authorization": f"Bearer {token}"},
        json={"primaryObjectId": survivor_id, "objectIdToMerge": loser_id},
        timeout=30,
    )
    return resp.json()


def mark_pushed_back(conn, working_copy_ids):
    if not working_copy_ids:
        return
    with conn.cursor() as cur:
        cur.execute(MARK_PUSHED, (working_copy_ids,))
    conn.commit()


def main():
    token = os.environ.get("HUBSPOT_ACCESS_TOKEN")
    database_url = os.environ.get("DATABASE_URL")

    if not token or not database_url:
        print("Missing HUBSPOT_ACCESS_TOKEN or DATABASE_URL env vars.", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(database_url)

    try:
        pending = get_pending_pushbacks(conn)
        print(f"Pending merges to push back to HubSpot: {len(pending)}")

        pushed_ids = []
        for row in pending:
            loser_hs_id = row["hubspot_contact_id"]
            survivor_hs_id = row["survivor_hubspot_contact_id"]
            try:
                merge_in_hubspot(token, survivor_hs_id, loser_hs_id)
                pushed_ids.append(row["id"])
                print(f"Merged HubSpot contact {loser_hs_id} -> {survivor_hs_id}")
            except requests.HTTPError as exc:
                print(f"Skipped working_copy id {row['id']}: {exc}", file=sys.stderr)
            time.sleep(0.2)

        mark_pushed_back(conn, pushed_ids)
        print(f"Push-back complete. {len(pushed_ids)}/{len(pending)} merges written to HubSpot.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
