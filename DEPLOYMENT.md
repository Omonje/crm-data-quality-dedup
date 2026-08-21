# Deployment Notes

This project runs locally against the same Docker Compose Postgres/n8n
stack as project 1, with GitHub Actions and Lovable as separate hosted
pieces reaching in through a dev tunnel. Moving it to a real client
engagement changes several things.

## n8n hosting

Same options as project 1: n8n Cloud is the fastest path with no
infrastructure to manage; self-hosted makes sense if the client wants data
residency control or already runs other services on the same
infrastructure. Either way, production needs a real HTTPS endpoint for the
three webhooks this project exposes (bulk-pull ingest, review-queue GET,
review-decision POST) - a dev tunnel is fine for building and testing, not
for a live client.

## What changes from this local setup

- **Secrets never live in files.** The HubSpot access token and the
  Postgres/Slack credentials belong in n8n's credential store and GitHub
  Actions' encrypted secrets, never committed to the repo. The
  `HUBSPOT_ACCESS_TOKEN` scope should stay limited to
  `crm.objects.contacts.read`/`write` only - resist the temptation to grant
  broader scopes "just in case," same reasoning as project 1's Twilio
  Auth Token vs. scoped API Key note.
- **The bulk pull moves from manual dispatch to scheduled.** Right now
  `bulk-sync.yml` only runs on `workflow_dispatch`, deliberately, because
  seeding the database once and testing against it is what this build
  needed. A real client wants this on a cadence (nightly is reasonable for
  most CRM sizes) - a one-line addition to the workflow's `on:` block.
- **The matching pass moves from manual trigger to scheduled, but only
  after the confidence thresholds have been validated against real
  approve/reject decisions from the review queue.** Auto-merging on
  unproven thresholds against a real client's data is exactly the kind of
  mistake the review queue exists to prevent - don't skip the validation
  step to save a week.
- **Owner assignment's territory map and rep list are demo data.** The
  four-region, four-rep mapping in `Code: Assign Territory` needs to be
  replaced with the client's actual sales team structure and territory
  rules before this does anything useful for them.
- **Managed Postgres instead of a local container**, same as project 1 -
  the local `app-db` container is disposable dev state, not something to
  point a real client's CRM data at.
- **GitHub Actions' bulk-pull script should move to the client's actual
  CRM's bulk/batch endpoints if it isn't HubSpot.** The pagination and
  batching pattern in `bulk_pull_hubspot.py` is the reusable part; the
  specific API calls are HubSpot's.

## Before going live for a real client

1. Confirm the confidence thresholds (0.85 auto-merge, 0.40 review floor)
   against a sample of that client's actual data, reviewed by someone on
   their team - these numbers were tuned against this project's synthetic
   dataset, not a guarantee for any real CRM's duplicate patterns.
2. Confirm the Slack channel is one the client's team actually watches.
3. Confirm the review-decision webhook is reachable at its real production
   URL before pointing Lovable's hosted frontend at it.
4. Run the bulk pull once manually and check `crm_raw_snapshot` has a
   complete, correct copy before letting the matching pass touch anything.

## Monitoring after launch

The Slack notification on new review-queue items is the only proactive
alert this project ships with. A real deployment should pair it with:
failure alerting on the GitHub Actions bulk-pull job itself (a silently
failing nightly sync is worse than no sync, since it creates false
confidence that the data is current), and n8n's own execution history
retention settings, same as project 1's monitoring note.

## A production discipline worth naming explicitly

`crm_raw_snapshot` exists so that if a client ever asks "what did our data
look like before this ran," there's a real, provable answer, not a
promise. That's a genuinely different level of trust than "we tested it
and it seemed fine" - worth explaining to a client in exactly those terms
when this project comes up in a proposal or interview.
