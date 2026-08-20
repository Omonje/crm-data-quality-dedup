"""
Generates a realistic dirty CRM contact dataset for the dedup/data-quality
portfolio project. Deliberately injects three kinds of records:

  1. Exact duplicates (same person re-entered, e.g. later Created Date)
  2. Near-duplicates (typo, nickname, case, phone/email formatting drift,
     or a partial re-entry missing company/job title/phone)
  3. False positives (two genuinely different people who share a common
     name, to prove the matching logic doesn't over-merge on name alone)

Output: dirty_crm_contacts_1000.csv, formatted to match HubSpot's standard
importable contact properties directly.
"""

import csv
import random

random.seed(42)

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen", "Christopher",
    "Nancy", "Daniel", "Lisa", "Matthew", "Margaret", "Anthony", "Sandra",
    "Mark", "Ashley", "Donald", "Kimberly", "Steven", "Emily", "Paul",
    "Donna", "Andrew", "Michelle", "Joshua", "Dorothy", "Kenneth", "Carol",
    "Kevin", "Amanda", "Brian", "Melissa", "George", "Deborah", "Edward",
    "Stephanie", "Ronald", "Rebecca", "Timothy", "Laura", "Jason", "Sharon",
    "Jeffrey", "Cynthia", "Ryan", "Kathleen", "Jacob", "Amy", "Gary",
    "Angela", "Nicholas", "Shirley", "Eric", "Anna", "Jonathan", "Brenda",
    "Stephen", "Pamela", "Larry", "Emma", "Justin", "Nicole", "Scott",
    "Helen", "Brandon", "Samantha", "Benjamin", "Katherine", "Samuel",
    "Christine", "Frank", "Debra", "Gregory", "Rachel", "Raymond", "Carolyn",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts",
]

# Nickname substitutions, used to create realistic near-duplicates
NICKNAMES = {
    "Robert": "Bob", "William": "Bill", "Elizabeth": "Liz",
    "Katherine": "Kathy", "Michael": "Mike", "Jennifer": "Jen",
    "Jonathan": "Jon", "Christopher": "Chris", "Nicholas": "Nick",
    "Deborah": "Debbie", "Margaret": "Maggie", "Patricia": "Pat",
    "Timothy": "Tim", "Benjamin": "Ben", "Samuel": "Sam",
    "Rebecca": "Becky", "Stephanie": "Steph", "Gregory": "Greg",
    "Anthony": "Tony", "Kimberly": "Kim",
}

COMPANIES = [
    "Northwind Traders", "Beacon Analytics", "Silverline Logistics",
    "Ferncrest Media", "Brightpath Consulting", "Ironwood Manufacturing",
    "Cobalt Digital", "Harborview Financial", "Redstone Realty",
    "Cascade Software", "Amber Grove Retail", "Steadfast Insurance",
    "Lumen Health Partners", "Granite Peak Construction", "Vantage Point Law",
    "Orchard Lane Foods", "Pinnacle Logistics Group", "Marlowe & Co.",
    "Crestline Energy", "Fieldstone Education", "Meridian Data Systems",
    "Willowbrook Nonprofit", "Quarry Hill Ventures", "Aster Marketing",
    "Coppervale Manufacturing", "Driftwood Hospitality", "Elmshade Legal",
    "Foxglove Biotech", "Greystone Capital", "Hollowridge Transport",
]

JOB_TITLES = [
    "Marketing Manager", "Sales Director", "Operations Manager",
    "Account Executive", "VP of Sales", "Customer Success Manager",
    "Finance Director", "HR Manager", "Product Manager", "IT Manager",
    "Office Manager", "Business Development Rep", "Purchasing Manager",
    "Executive Assistant", "Regional Sales Manager", "Controller",
    "Marketing Coordinator", "Operations Director", "CEO", "COO",
]

INDUSTRIES = [
    "Retail", "Manufacturing", "Financial Services", "Healthcare",
    "Logistics", "Technology", "Real Estate", "Construction", "Education",
    "Hospitality", "Legal Services", "Nonprofit", "Media", "Insurance",
    "Biotechnology",
]

CITIES_STATES = [
    ("Austin", "TX"), ("Columbus", "OH"), ("Denver", "CO"), ("Raleigh", "NC"),
    ("Portland", "OR"), ("Nashville", "TN"), ("Sacramento", "CA"),
    ("Kansas City", "MO"), ("Tampa", "FL"), ("Salt Lake City", "UT"),
    ("Richmond", "VA"), ("Milwaukee", "WI"), ("Albuquerque", "NM"),
    ("Boise", "ID"), ("Omaha", "NE"), ("Tucson", "AZ"), ("Louisville", "KY"),
    ("Providence", "RI"), ("Charleston", "SC"), ("Des Moines", "IA"),
]

LIFECYCLE_STAGES = ["subscriber", "lead", "marketingqualifiedlead",
                     "salesqualifiedlead", "opportunity", "customer"]
LEAD_STATUSES = ["New", "Open", "In Progress", "Unqualified",
                  "Attempted to Contact", "Connected", "Bad Timing"]

EMAIL_DOMAINS = ["gmail.com", "outlook.com", "yahoo.com", "company.com",
                  "business.net"]


def random_date():
    year = random.choice([2024, 2025, 2026])
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year}-{month:02d}-{day:02d}"


def random_phone():
    return f"({random.randint(200, 989)}) {random.randint(200, 989)}-{random.randint(1000, 9999)}"


def reformat_phone(phone):
    """Same number, different formatting - a common real-world duplicate signal."""
    digits = "".join(c for c in phone if c.isdigit())
    fmt = random.choice([
        lambda d: f"{d[0:3]}-{d[3:6]}-{d[6:10]}",
        lambda d: d,
        lambda d: f"+1 {d[0:3]} {d[3:6]} {d[6:10]}",
        lambda d: f"{d[0:3]}.{d[3:6]}.{d[6:10]}",
    ])
    return fmt(digits)


USED_EMAILS = set()


def make_email(first, last, domain=None):
    """Guarantees global uniqueness - HubSpot rejects rows that share an
    email with another row in the same import batch, so every row (even
    intended duplicates) needs a distinct address. The duplicate signal
    for those rows comes from name/phone/company matching instead, which
    is more realistic anyway - a common real duplicate is the same person
    entered under two different emails (personal vs. work)."""
    domain = domain or random.choice(EMAIL_DOMAINS)
    style = random.choice([
        f"{first.lower()}.{last.lower()}",
        f"{first.lower()}{last.lower()}",
        f"{first[0].lower()}{last.lower()}",
    ])
    email = f"{style}@{domain}"
    if email not in USED_EMAILS:
        USED_EMAILS.add(email)
        return email
    # collision - append a growing numeric suffix until unique
    n = 2
    while f"{style}{n}@{domain}" in USED_EMAILS:
        n += 1
    email = f"{style}{n}@{domain}"
    USED_EMAILS.add(email)
    return email


def base_contact():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    city, state = random.choice(CITIES_STATES)
    return {
        "First Name": first,
        "Last Name": last,
        "Email": make_email(first, last),
        "Phone Number": random_phone(),
        "Company Name": random.choice(COMPANIES),
        "Job Title": random.choice(JOB_TITLES),
        "Industry": random.choice(INDUSTRIES),
        "City": city,
        "State": state,
        "Country": "United States",
        "Lifecycle Stage": random.choice(LIFECYCLE_STAGES),
        "Lead Status": random.choice(LEAD_STATUSES),
        "Created Date": random_date(),
    }


def make_near_duplicate(contact):
    """Same person, entered messily a second time."""
    dupe = dict(contact)
    variant_type = random.choice(["nickname", "case", "phone_format",
                                   "partial_data", "email_variant", "typo"])

    if variant_type == "nickname" and contact["First Name"] in NICKNAMES:
        dupe["First Name"] = NICKNAMES[contact["First Name"]]
    elif variant_type == "case":
        dupe["First Name"] = dupe["First Name"].upper()
        dupe["Last Name"] = dupe["Last Name"].upper()
    elif variant_type == "phone_format":
        dupe["Phone Number"] = reformat_phone(contact["Phone Number"])
    elif variant_type == "partial_data":
        dupe["Company Name"] = ""
        dupe["Job Title"] = ""
        if random.random() < 0.5:
            dupe["Phone Number"] = ""
    elif variant_type == "typo":
        name = list(dupe["Last Name"])
        if len(name) > 3:
            i = random.randint(1, len(name) - 2)
            name[i], name[i + 1] = name[i + 1], name[i]
        dupe["Last Name"] = "".join(name)

    # Every duplicate gets its own unique email (HubSpot dedupes imports by
    # email) - a fresh style/domain roll from the same name is itself a
    # realistic "personal vs. work email" duplicate signal.
    dupe["Email"] = make_email(contact["First Name"], contact["Last Name"])
    dupe["Created Date"] = random_date()
    return dupe


def make_exact_duplicate(contact):
    dupe = dict(contact)
    dupe["Email"] = make_email(contact["First Name"], contact["Last Name"])
    dupe["Created Date"] = random_date()
    return dupe


def make_false_positive_pair():
    """Two genuinely different people who happen to share a common name -
    should NOT get merged. Different email, company, city, phone."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    people = []
    for _ in range(2):
        city, state = random.choice(CITIES_STATES)
        people.append({
            "First Name": first,
            "Last Name": last,
            "Email": make_email(first, last, domain=random.choice(EMAIL_DOMAINS)),
            "Phone Number": random_phone(),
            "Company Name": random.choice(COMPANIES),
            "Job Title": random.choice(JOB_TITLES),
            "Industry": random.choice(INDUSTRIES),
            "City": city,
            "State": state,
            "Country": "United States",
            "Lifecycle Stage": random.choice(LIFECYCLE_STAGES),
            "Lead Status": random.choice(LEAD_STATUSES),
            "Created Date": random_date(),
        })
    return people


def main():
    rows = []

    # 25 false-positive pairs (50 rows) - same name, genuinely different people
    for _ in range(25):
        rows.extend(make_false_positive_pair())

    # Base unique contacts
    base_contacts = [base_contact() for _ in range(760)]
    rows.extend(base_contacts)

    # Duplicate ~19% of base contacts as near-duplicates, ~6% as exact duplicates
    near_dupe_sample = random.sample(base_contacts, 145)
    for c in near_dupe_sample:
        rows.append(make_near_duplicate(c))

    exact_dupe_sample = random.sample(base_contacts, 45)
    for c in exact_dupe_sample:
        rows.append(make_exact_duplicate(c))

    random.shuffle(rows)
    rows = rows[:1000]

    fieldnames = [
        "First Name", "Last Name", "Email", "Phone Number", "Company Name",
        "Job Title", "Industry", "City", "State", "Country",
        "Lifecycle Stage", "Lead Status", "Created Date",
    ]

    out_path = "dirty_crm_contacts_1000.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")
    print(f"Columns ({len(fieldnames)}): {fieldnames}")


if __name__ == "__main__":
    main()
