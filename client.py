"""Consumer side: talk to the API like any other service would.

Start the server first:  uv run uvicorn app.main:app --reload
Then run:                uv run python client.py
"""

from typing import Any

import httpx

BASE_URL = "http://127.0.0.1:8000"


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
        # CREATE
        new: dict[str, Any] = {
            "name": "TP53-exon5",
            "organism": "homo_sapiens",
            "sequence": "TACCTGCCGGAGCAGG",
        }
        r = client.post("/samples", json=new)
        print(r.status_code, r.headers.get("Location"))
        r.raise_for_status()
        sample = r.json()
        print(f"GC content: {sample['gc_content']:.1%}")

        # READ (collection with filter)
        r = client.get("/samples", params={"organism": "homo_sapiens"})
        print("total human samples:", r.json()["total"])

        # UPDATE (partial)
        r = client.patch(f"/samples/{sample['id']}", json={"name": "TP53-exon5-v2"})
        print("renamed ->", r.json()["name"])

        # Validation error example
        r = client.post("/samples", json={**new, "name": "bad", "sequence": "ATGXYZ"})
        print(r.status_code, r.json()["detail"][0]["msg"])

        # DELETE
        r = client.delete(f"/samples/{sample['id']}")
        print("deleted:", r.status_code)


if __name__ == "__main__":
    main()
