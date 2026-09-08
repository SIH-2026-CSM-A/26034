"""Seed the demonstration. Every record it writes is labelled as seeded.

Runs inside the backend container against the live API on localhost and the database
the container is configured for. Idempotent enough for a demo: it checks for its own
vendor rows before inserting and skips the scan seed if the seeding officer already has
scans.

    docker exec 26034-backend-1 python scripts/seed_demo.py <demo-seeder password>

What it seeds, and how each is marked:
- catalogue scans, submitted as the officer ``demo-seeder`` (the frontend labels that
  officer's rows "seeded demo"); the listing platform is ``seeded-demo`` and every
  title starts with ``[Seeded demo]``;
- finalising reviews on the POTENTIAL_VIOLATION scans, then one complaint per such scan
  through the real service, with ``[Seeded demo]`` in the manufacturer name;
- complaint lifecycle rows (acknowledged / resolved / rejected) as append-only
  successors of raised complaints, because no endpoint transitions a complaint today;
- vendor rows, with ``[Seeded demo]`` in every name, because no endpoint creates one;
- anonymous reviews for two barcodes: four "safe" for 8901719100015 (published at the
  default threshold of 3) and one "safe" for 8901725113320 (held below it).

Nothing here is a verdict of ours: every verdict comes from the pipeline evaluating the
listing it is given.
"""

import asyncio
import json
import random
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import insert, select

API = "http://localhost:8000"
OFFICER = "demo-seeder"
random.seed(26034)

MAKERS = [
    ("Sri Lakshmi Foods Pvt Ltd, Plot 14, IDA Bollaram, Sangareddy 502325", "India"),
    ("Deccan Naturals, 22 Sarojini Devi Rd, Secunderabad 500003", "India"),
    ("Hyderabad Grain Mills, Kukatpally Industrial Area, Hyderabad 500072", "India"),
    ("Charminar Provisions, 8 Pathergatti, Hyderabad 500002", "India"),
]
PRODUCTS = [
    ("Wheat Flour", "1 kg", "Rs. 62.00"),
    ("Toothpaste", "100 g", "Rs. 99.00"),
    ("Refined Sunflower Oil", "1 L", "Rs. 145.00"),
    ("Glucose Biscuits", "82.5 g", "Rs. 10.00"),
    ("Detergent Powder", "500 g", "Rs. 58.00"),
    ("Basmati Rice", "5 kg", "Rs. 540.00"),
    ("Hair Oil", "200 ml", "Rs. 120.00"),
    ("Instant Noodles", "70 g", "Rs. 14.00"),
]


def call(method: str, path: str, *, body=None, token=None, form=None):
    data = None
    headers = {}
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(API + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"null")


def listing(i: int) -> dict:
    name, qty, mrp = PRODUCTS[i % len(PRODUCTS)]
    maker, origin = MAKERS[i % len(MAKERS)]
    when = datetime.now(UTC) - timedelta(days=i % 7, hours=i)
    fields = {
        "COMMON_OR_GENERIC_NAME": name,
        "NET_QUANTITY": f"Net Quantity: {qty}",
        "RETAIL_SALE_PRICE": f"MRP {mrp} (inclusive of all taxes)",
        "NAME_AND_ADDRESS": f"Manufactured by {maker}",
        "COUNTRY_OF_ORIGIN": f"Country of origin: {origin}",
        "MANUFACTURE_DATE": f"Mfd. {when:%m/%Y}",
        "BEST_BEFORE_DATE": "Best before 12 months from manufacture",
        "CONSUMER_CARE": "Consumer care: care@example.in, 1800 000 0000",
        # A catalogue record declares nothing it does not list, so a listing without these
        # two fails Rule 6(1)(f) and 6(1)(g) outright and every seeded verdict was
        # POTENTIAL_VIOLATION. With them, a complete listing reaches REVIEW.
        "DIMENSIONS": "Dimensions: 30 cm x 20 cm x 8 cm",
        "OTHER_PRESCRIBED_MATTER": f"Lot No. SD{i:04d}",
    }
    # Roughly two in five listings omit a mandatory declaration, so the seed shows every
    # verdict the pipeline can reach rather than a wall of PASS.
    if i % 5 in (1, 3):
        fields.pop(random.choice(["RETAIL_SALE_PRICE", "NET_QUANTITY", "NAME_AND_ADDRESS"]))
    return {
        "record": {
            "listing_id": f"seeded-demo-{i:03d}",
            "platform": "seeded-demo",
            "retrieved_at": when.isoformat(),
            "title": f"[Seeded demo] {name} {qty}",
            "declared_fields": fields,
        },
        "product_category": "food"
        if name
        in {
            "Wheat Flour",
            "Refined Sunflower Oil",
            "Glucose Biscuits",
            "Basmati Rice",
            "Instant Noodles",
        }
        else None,
    }


async def seed_rows(complaint_ids: list[str]) -> None:
    from app.core import get_session_factory
    from app.core.models import Base

    vendors = Base.metadata.tables["vendors"]
    complaints = Base.metadata.tables["complaints"]
    factory = get_session_factory()
    async with factory() as session, session.begin():
        existing = (
            await session.execute(select(vendors.c.id).where(vendors.c.name.like("[Seeded demo]%")))
        ).all()
        if not existing:
            rows = [
                (
                    "[Seeded demo] Sri Venkateswara Kirana",
                    "kirana",
                    "Telangana",
                    "Hyderabad",
                    "Hyderabad",
                ),
                (
                    "[Seeded demo] Ratnadeep Supermarket, Begumpet",
                    "supermarket",
                    "Telangana",
                    "Hyderabad",
                    "Hyderabad",
                ),
                (
                    "[Seeded demo] Bollaram Cold Storage Godown",
                    "godown",
                    "Telangana",
                    "Hyderabad",
                    "Sangareddy",
                ),
                (
                    "[Seeded demo] More Megastore, Kukatpally",
                    "supermarket",
                    "Telangana",
                    "Hyderabad",
                    "Medchal-Malkajgiri",
                ),
                (
                    "[Seeded demo] Charminar Provisions",
                    "kirana",
                    "Telangana",
                    "Hyderabad",
                    "Hyderabad",
                ),
                (
                    "[Seeded demo] Warangal Grain Godown",
                    "godown",
                    "Telangana",
                    "Warangal",
                    "Warangal",
                ),
                (
                    "[Seeded demo] Vizag Central Supermarket",
                    "supermarket",
                    "Andhra Pradesh",
                    "Visakhapatnam",
                    "Visakhapatnam",
                ),
            ]
            await session.execute(
                insert(vendors),
                [
                    {
                        "id": uuid4(),
                        "name": n,
                        "vendor_type": t,
                        "state": s,
                        "region": r,
                        "district": d,
                        "created_at": datetime.now(UTC),
                    }
                    for n, t, s, r, d in rows
                ],
            )
            print(f"vendors: inserted {len(rows)}")
        else:
            print("vendors: already seeded")

        # Lifecycle successors: the service is append-only, so a state change is a new row
        # naming the row it supersedes. Three raised complaints get three different states.
        for cid, status in zip(
            complaint_ids, ["acknowledged", "resolved", "rejected"], strict=False
        ):
            row = (
                (await session.execute(select(complaints).where(complaints.c.id == cid)))
                .mappings()
                .one()
            )
            await session.execute(
                insert(complaints).values(
                    id=uuid4(),
                    scan_id=row["scan_id"],
                    verdict_id=row["verdict_id"],
                    manufacturer_name=row["manufacturer_name"],
                    issue_summary=row["issue_summary"] + " (seeded demo record)",
                    status=status,
                    raised_by_officer_id=OFFICER,
                    raised_at=datetime.now(UTC),
                    supersedes_id=row["id"],
                )
            )
            print(f"complaint {cid[:8]} -> {status}")


def main() -> None:
    password = sys.argv[1]
    # `seed_demo.py <password> --append N OFFSET` submits N more listings numbered from
    # OFFSET and nothing else, for a second run on a database already seeded.
    if len(sys.argv) >= 5 and sys.argv[2] == "--append":
        status, tok = call("POST", "/auth/token", form={"username": OFFICER, "password": password})
        assert status == 200, (status, tok)
        count, offset = int(sys.argv[3]), int(sys.argv[4])
        verdicts = []
        for i in range(offset, offset + count):
            status, detail = call("POST", "/scans", body=listing(i), token=tok["access_token"])
            assert status == 201, (status, detail)
            verdicts.append(detail["verdict"])
        print(
            f"appended {count}: "
            + ", ".join(f"{v}={verdicts.count(v)}" for v in sorted(set(verdicts)))
        )
        return
    status, tok = call("POST", "/auth/token", form={"username": OFFICER, "password": password})
    assert status == 200, (status, tok)
    token = tok["access_token"]

    status, mine = call("GET", "/scans", token=token)
    assert status == 200, (status, mine)
    if any(s["officer_id"] == OFFICER for s in mine):
        print(f"scans: {OFFICER} already has {len(mine)} scans, skipping scan seed")
        scans = [s for s in mine if s["officer_id"] == OFFICER]
    else:
        scans = []
        for i in range(30):
            status, detail = call("POST", "/scans", body=listing(i), token=token)
            assert status == 201, (status, detail)
            scans.append(detail)
        print(
            f"scans: submitted {len(scans)}; verdicts: "
            + ", ".join(
                f"{v}={sum(1 for s in scans if s['verdict'] == v)}"
                for v in ("PASS", "REVIEW", "POTENTIAL_VIOLATION")
            )
        )

    complaint_ids: list[str] = []
    for s in [s for s in scans if s["verdict"] == "POTENTIAL_VIOLATION"][:6]:
        status, detail = call("GET", f"/scans/{s['id']}", token=token)
        if not detail["finalised"]:
            status, _ = call(
                "POST",
                f"/scans/{s['id']}/review",
                body={"action": "confirm", "note": "Seeded demo confirmation."},
                token=token,
            )
            assert status == 201, status
        failing = [f for f in detail["findings"] if f["state"] == "FAIL"]
        if not failing:
            continue
        f = failing[0]
        maker = next(
            (
                x["observed_value"]
                for x in detail["findings"]
                if x["field"] == "NAME_AND_ADDRESS" and x["observed_value"]
            ),
            None,
        )
        status, c = call(
            "POST",
            "/complaints",
            body={
                "scan_id": s["id"],
                "manufacturer_name": "[Seeded demo] "
                + (maker or "manufacturer as declared").split(",")[0][:80],
                "rule_id": f["rule_snapshot"]["rule_id"],
                "field": f["field"],
                "measured_value": f["observed_value"] or "not declared",
                "required_value": f["expected_value"] or "declaration present",
            },
            token=token,
        )
        if status == 201:
            complaint_ids.append(c["id"])
        else:
            print("complaint refused:", status, c)
    print(f"complaints: raised {len(complaint_ids)}")

    for pid, n in (("8901719100015", 4), ("8901725113320", 1)):
        for _ in range(n):
            status, r = call(
                "POST",
                "/reviews",
                body={"product_identifier": pid, "consumer_safety_claim": "safe"},
            )
            assert status == 201, (status, r)
        print(f"reviews: {pid} x{n} safe -> {r['publication_status']}")

    asyncio.run(seed_rows(complaint_ids))


if __name__ == "__main__":
    main()
