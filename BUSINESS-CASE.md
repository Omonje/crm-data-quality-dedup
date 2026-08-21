# Business Case

## Problem

Duplicate and dirty CRM records are one of the most expensive, least visible
problems in a growing sales or marketing operation. Gartner's widely cited
benchmark puts the average cost of poor data quality at **$12.9 million per
year** across organizations ([Verum: The Real Cost of Bad CRM Data](https://veruminc.com/resources/cost-of-bad-crm-data.html)).
More directly relevant to how records actually get dirty: an analysis of 12
billion Salesforce records found **45% were duplicates overall, rising to
80% for records created via API integrations** ([Landbase: Duplicate Record Rate Statistics](https://www.landbase.com/blog/duplicate-record-rate-statistics)) —
exactly the ingestion path this project builds (a bulk API pull from a CRM),
which is precisely why the system separates an immutable raw snapshot from
a working copy, and never silently auto-merges anything it isn't confident
about.

The two specific failure modes:

1. **No detection beyond exact matches.** Most CRMs only catch a duplicate
   if the email is character-for-character identical. Real duplicates come
   from typos, nicknames, formatting differences, and the same person
   entered under a work email and a personal one — none of which a plain
   exact-match check catches.
2. **No safe way to act on what's found.** A tool confident enough to
   auto-merge obvious duplicates still needs a place to send the ones it
   isn't sure about, or the choice becomes "merge everything and risk
   destroying real data" or "merge nothing and the problem never gets
   smaller."

The people-cost compounds this: sales reps lose an estimated **546 hours a
year, roughly 27% of their productive time**, to data entry and chasing
inaccurate records ([this+that: CRM Data Decay Statistics](https://www.thisandthat.chat/blog/crm-data-decay-statistics/)).

## Solution

- **Confidence-scored matching, not exact-match only.** Phone or email
  exact match scores highest; name similarity (with nickname handling —
  Bob/Robert, Liz/Elizabeth) combined with a company match scores high but
  not automatic; name similarity alone scores in review-only territory.
  Rule-based on purpose, not a single blended formula, so every flag has an
  explainable reason, not a black-box score.
- **A real human-review queue, not just a described one.** Anything scoring
  0.40–0.85 goes to a review screen (built in Lovable) where a person sees
  both records side by side and approves or rejects. Below 0.40 isn't even
  flagged. This is the direct fix for the auto-merge risk above — the
  system only acts alone when it's genuinely confident.
- **An immutable audit trail.** Every pull writes into a raw snapshot table
  that's never touched again, separate from the working copy the matching
  logic actually operates on. If anything looks wrong after the fact,
  there's a real record of what the data looked like before any change.
- **Bulk data movement separated from matching logic.** The one-time/bulk
  pull and push against the CRM's API run through GitHub Actions, using
  batch endpoints, specifically to avoid the API rate-limit wall that a
  row-by-row sync hits at real scale (tens of thousands of records). The
  actual matching, scoring, and review-queue logic runs in n8n against the
  local database, with no CRM API calls during that step at all.

## Who this is for

Any team whose CRM has been fed by more than one source for more than a
year or two — API integrations, bulk imports, multiple people entering
data — and has never run a real deduplication pass. Based on the 45-80%
duplicate rates found in real Salesforce data above, that's most CRMs past
a certain age and size, not an edge case.

## Expected impact

This is a portfolio build, not a live client deployment, so there's no
production result to report. What follows is industry benchmark data, not
an achieved outcome for this specific implementation:

- Duplicate records inflate marketing costs by an estimated **43%** and
  are cited by **70% of leaders** as an active source of eroded trust in
  their own CRM data ([Coffee.ai: Hidden Costs of Bad CRM Data Quality](https://www.coffee.ai/articles/hidden-costs-bad-crm-data)).
- The same 12-billion-record Salesforce analysis found duplicate rates
  jump specifically where data enters through automation and API
  integrations — meaning a system built to run continuously alongside
  those integrations (not a one-time cleanup) is addressing the actual
  ongoing source, not just symptom.

The honest framing for a prospective client: this system finds and
resolves the duplicates a plain exact-match check misses, without the risk
of silently merging two different people. The actual reduction in
duplicate rate and time saved depends on how dirty a given CRM already is,
and should be measured against that CRM's own baseline once live.
