# Upwork Portfolio Entry (copy-paste ready, edit before posting)

**Title:** CRM Duplicate Detection & Data Quality System (n8n + Postgres + GitHub Actions + Lovable)

**Cover image:** the Lovable review screen showing a side-by-side duplicate
pair with the confidence badge — more convincing than a workflow
screenshot, it shows the actual decision a client's team would use.

**Links to include in the listing:** [ARCHITECTURE.md](ARCHITECTURE.md),
[BUSINESS-CASE.md](BUSINESS-CASE.md), [DEPLOYMENT.md](DEPLOYMENT.md) —
same reasoning as every other project here: these show you can reason
about a system, not just assemble nodes.

**Description:**

Built a duplicate detection and data-quality system for CRM records,
converting real past experience (cleaning up 33,000 and later 65,000
duplicate-riddled CRM records for a client) into a documented, working
system. Most CRMs and no-code dedup tools only catch exact-match
duplicates — an analysis of 12 billion real Salesforce records found 45%
were duplicates overall, rising to 80% for records created via API
integrations, and none of that gets caught by matching on identical
emails alone.

The system scores every candidate duplicate pair by confidence: phone or
email exact match scores highest, name similarity (with nickname handling
— Bob/Robert, Liz/Elizabeth) combined with a company match scores high but
not automatic, and name similarity alone lands in a review queue instead
of getting merged or ignored. High-confidence pairs merge automatically.
Everything else goes to a real review screen (built in Lovable) where a
person sees both records side by side and approves or rejects — the fix
for the one thing every auto-merge tool risks: destroying real data by
merging two different people who happen to share a name.

Two production details most builds skip: an immutable snapshot of the
data is written before anything touches it, so there's a real answer to
"what did this look like before," not just a promise. And the heavy,
one-time bulk pull from the CRM's API runs through GitHub Actions using
batch endpoints, completely separate from the day-to-day matching logic
in n8n — a row-by-row sync hits API rate limits fast at real scale (tens
of thousands of records), so the two are split by design, not as an
afterthought.

**Skills tags:** n8n, PostgreSQL, HubSpot API, GitHub Actions, Python,
Data Deduplication, CRM Integration, Fuzzy Matching, API Integration,
Workflow Automation

**Before posting, confirm:**
- [ ] The demo HubSpot account and territory/rep data in the case study
      language are clearly framed as demo data, not implied to be a real
      client's
- [ ] Loom recorded, walking through all four pieces: the bulk pull, the
      matching/scoring logic, the review queue in Lovable (both an
      approve and a reject), and the owner assignment
- [ ] Repo is public and the latest commit includes ARCHITECTURE.md,
      BUSINESS-CASE.md, and DEPLOYMENT.md
- [ ] Case study description above has no leftover placeholder text
      before copy-pasting into the Upwork listing
