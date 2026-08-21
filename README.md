# CRM Data Quality & Duplicate Prevention

**Docs:** [Architecture](ARCHITECTURE.md) · [Business Case](BUSINESS-CASE.md) · [Deployment Notes](DEPLOYMENT.md)

## What this is

A production-pattern deduplication and data-quality system, not a demo
toy. It converts real past experience (cleaning up 33,000 and later 65,000
duplicate-riddled CRM records for a client) into a documented, working
artifact: confidence-scored fuzzy matching, a real human-review queue for
anything ambiguous, an immutable audit snapshot, and bulk data movement
split from matching logic specifically to survive CRM API rate limits at
real scale. Full reasoning in [ARCHITECTURE.md](ARCHITECTURE.md) and
[BUSINESS-CASE.md](BUSINESS-CASE.md).

## Why not just dedupe on exact email match?

Because most duplicates don't share an exact email. An analysis of 12
billion real Salesforce records found 45% were duplicates overall, rising
to 80% for records created via API integrations — see
[BUSINESS-CASE.md](BUSINESS-CASE.md) for the full citation. Real duplicates
come from nicknames, typos, reformatted phone numbers, and the same person
entered under two different emails entirely. Exact-match dedup, which is
what most CRMs and no-code tools ship with by default, catches almost none
of that.

## Setup

1. Run `docker compose up` from `../infra/` (shared Postgres/n8n/pgAdmin
   stack, same as project 1).
2. Run `schema.sql`, then `migration_add_review_survivor_columns.sql`
   against the `portfolio` database.
3. Run `data/generate_dirty_dataset.py` to regenerate the synthetic dirty
   dataset if needed (already generated once, committed at
   `data/dirty_crm_contacts_1000.csv`).
4. Import that CSV into a HubSpot Private App / Service Key-enabled
   account (Contacts → Import). Get an access token scoped to
   `crm.objects.contacts.read` and `crm.objects.contacts.write` only.
5. Import `workflow.json` into n8n, reselect the Postgres/Slack
   credentials on every node (drops on every import), activate the
   workflow.
6. Add `HUBSPOT_ACCESS_TOKEN` and `N8N_WEBHOOK_URL` as GitHub Actions
   secrets on this repo (the webhook URL needs a tunnel — see below).
7. Trigger **Bulk sync CRM contacts** (GitHub Actions, direction=pull) to
   seed the database, then run **Manual: Run Matching Pass** in n8n.

## Local testing constraint

Both GitHub Actions and Lovable's hosted frontend need to reach this
project's n8n webhooks from outside your machine. Locally, that means
`ngrok http 5678` (or Cloudflare Tunnel) has to be running, and every
webhook URL you hand to GitHub secrets or the Lovable prompt needs to use
that tunnel's current domain, not `localhost`. Free-tier ngrok domains can
change on restart — if webhooks start failing after a restart, this is the
first thing to check.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| HubSpot import shows "Duplicate alternate ID" errors | HubSpot dedupes an import batch by email; rows sharing an email with an earlier row in the same file get rejected, not merged | Every row needs a genuinely unique email — see `generate_dirty_dataset.py`'s `USED_EMAILS` uniqueness guarantee |
| A Postgres node downstream only ever receives 1 item, no matter how many rows the upstream node processed | `executeQuery` INSERT/UPDATE nodes without a `RETURNING` clause collapse their own output to a single summary item, regardless of input count | Don't chain a node that needs per-item data behind one of these — branch both in parallel off the real source node instead (see `Insert Raw Snapshot` / `Insert Working Copy`, both fed directly from `Split Out Contacts`) |
| Postgres error `there is no parameter $4` (or similar) despite the Query Parameters field looking correct in preview | The field needs one expression that evaluates to a real array, not a comma-separated list of individually-mustached values - the latter resolves to a single concatenated string | Use `={{ [$json.a, $json.b, $json.c] }}`, not `{{ $json.a }},{{ $json.b }},{{ $json.c }}` |
| A webhook-driven If/Switch node always takes the wrong branch, or a query parameter resolves to `null` | n8n wraps a webhook POST's actual payload one level deeper, under `.body` - `$json.review_id` is `undefined`, the real value is `$json.body.review_id` | Reference `$json.body.<field>` for anything read directly off a webhook item |
| Can't add a second Manual Trigger node | n8n only allows one Manual Trigger per workflow (tied to the single "Execute Workflow" button) | Use a Schedule Trigger for anything that needs to run independently - see `Schedule: Assign Owners Hourly` |
| Lovable throws a Zod `expected number, received string` error on `confidence_score` | Postgres `NUMERIC` columns are returned as strings by the database driver to avoid floating-point precision loss; n8n passes that string straight through | Cast in the query: `confidence_score::float8`, same pattern used for `cart_value` in project 1 |
| Review queue shows empty in Lovable right after a schema change | The table was likely truncated as part of the fix and never repopulated | Re-run **Manual: Run Matching Pass** after any schema or query change to `Insert Into Review Queue` |
