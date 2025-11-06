"""
I infer a coarse document_type from a filename so I can route vendor checks
without asking the user to classify each file manually.

Rules:
- filenames that start with 'passport_' become 'passport'
- filenames that start with 'proof_of_address_' become 'proof_of_address'
- filenames that start with 'kyb_' become 'kyb'
- filenames that start with 'ubo_' or 'ubo_declaration_' become 'ubo_declaration'
- everything else becomes 'unknown'
"""

from __future__ import annotations

import os


def infer_document_type(filename: str) -> str:
    """I infer a simple document type based on the start of the filename."""
    name = os.path.basename(filename)
    lower = name.lower()

    # Simple, explicit rules
    if lower.startswith("passport_"):
        return "passport"
    if lower.startswith("proof_of_address_"):
        return "proof_of_address"
    if lower.startswith("kyb_"):
        return "kyb"
    if lower.startswith("ubo_") or lower.startswith("ubo_declaration_"):
        return "ubo_declaration"
    return "unknown"


if __name__ == "__main__":
    samples = [
        "passport_alex.png",
        "proof_of_address_bill.pdf",
        "kyb_company.pdf",
        "random.png",
    ]
    for s in samples:
        print(s, "->", infer_document_type(s))
