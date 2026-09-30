"""
uv run python fetch_uniprot.py P38398
"""

import sys
from typing import TypedDict

import httpx

UNIPROT = "https://rest.uniprot.org/uniprotkb"


class ProteinSummary(TypedDict):
    accession: str
    gene: str
    length: int


def fetch_protein(accession: str) -> ProteinSummary:
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{UNIPROT}/{accession}.json")
        r.raise_for_status()  # 4xx/5xx -> httpx.HTTPStatusError
        data = r.json()
    return {
        "accession": data["primaryAccession"],
        "gene": data["genes"][0]["geneName"]["value"],
        "length": data["sequence"]["length"],
    }


if __name__ == "__main__":
    print(fetch_protein(sys.argv[1] if len(sys.argv) > 1 else "P38398"))
