"""
Bulk pull: reads every contact from HubSpot using the batch-friendly
list endpoint (paginated, not one-call-per-record), then POSTs them in
chunks to an n8n webhook, which is responsible for writing them into
Postgres (crm_raw_snapshot + crm_working_copy).

This script deliberately never talks to Postgres directly - GitHub
Actions runners can't reach a local database anyway, and keeping "only
n8n talks to the DB" as a hard boundary matches how the rest of this
portfolio's projects are built.

Env vars required:
  HUBSPOT_ACCESS_TOKEN  - Private App token, read scope on contacts
  N8N_WEBHOOK_URL        - full webhook URL, e.g. https://<tunnel>/webhook/crm-bulk-pull
"""

import os
import sys
import time

import requests

HUBSPOT_API_BASE = "https://api.hubapi.com"
PAGE_SIZE = 100
CHUNK_SIZE = 50  # contacts per POST to n8n, keeps payloads reasonable

PROPERTIES = [
    "firstname", "lastname", "email", "phone", "company", "jobtitle",
    "industry", "city", "state", "country", "lifecyclestage",
    "hs_lead_status", "createdate",
]


def fetch_all_contacts(token):
    contacts = []
    after = None
    headers = {"Authorization": f"Bearer {token}"}

    while True:
        params = {
            "limit": PAGE_SIZE,
            "properties": ",".join(PROPERTIES),
        }
        if after:
            params["after"] = after

        resp = requests.get(
            f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts",
            headers=headers,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        for record in data.get("results", []):
            props = record.get("properties", {})
            contacts.append({
                "hubspot_contact_id": record["id"],
                "first_name": props.get("firstname"),
                "last_name": props.get("lastname"),
                "email": props.get("email"),
                "phone": props.get("phone"),
                "company_name": props.get("company"),
                "job_title": props.get("jobtitle"),
                "industry": props.get("industry"),
                "city": props.get("city"),
                "state": props.get("state"),
                "country": props.get("country"),
                "lifecycle_stage": props.get("lifecyclestage"),
                "lead_status": props.get("hs_lead_status"),
                "hubspot_created_date": props.get("createdate"),
            })

        paging = data.get("paging", {})
        after = paging.get("next", {}).get("after")
        print(f"Fetched {len(contacts)} contacts so far...")

        if not after:
            break

        # small pause between pages - polite to the API even though a
        # 1,000-row demo won't come close to HubSpot's real rate limits;
        # this is the pattern that matters at 33K-65K scale
        time.sleep(0.2)

    return contacts


def send_to_n8n(contacts, webhook_url):
    for i in range(0, len(contacts), CHUNK_SIZE):
        chunk = contacts[i:i + CHUNK_SIZE]
        resp = requests.post(webhook_url, json={"contacts": chunk}, timeout=30)
        resp.raise_for_status()
        print(f"Sent batch {i // CHUNK_SIZE + 1} ({len(chunk)} contacts) -> n8n")
        time.sleep(0.2)


def main():
    token = os.environ.get("HUBSPOT_ACCESS_TOKEN")
    webhook_url = os.environ.get("N8N_WEBHOOK_URL")

    if not token or not webhook_url:
        print("Missing HUBSPOT_ACCESS_TOKEN or N8N_WEBHOOK_URL env vars.", file=sys.stderr)
        sys.exit(1)

    contacts = fetch_all_contacts(token)
    print(f"Total contacts pulled from HubSpot: {len(contacts)}")

    send_to_n8n(contacts, webhook_url)
    print("Bulk pull complete.")


if __name__ == "__main__":
    main()
