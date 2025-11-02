"""
I provide a tiny helper that turns a filename into a document_type.

I keep the rules intentionally simple so they're easy to read and test:
- filenames that start with 'passport_' become 'passport'
- filenames that start with 'proof_of_address_' become 'proof_of_address'
- filenames that start with 'kyb_' become 'kyb'
- everything else becomes 'unknown'

I write this as a plain function so I can import it anywhere.
"""

from __future__ import annotations  # I allow future annotations style in older Python

import os  # I read just the basename so directories don't affect detection


def infer_document_type(filename: str) -> str:
    """I infer a simple document type based on the start of the filename.

    I normalize to the base name and lower case so 'Passport_Alex.PNG' still
    matches 'passport_'. If nothing matches, I say 'unknown'.
    """
    # I take only the file name part in case a path slips through.
    name = os.path.basename(filename)  # I strip any directories from the input
    # I compare in lower case so users don't have to worry about case.
    lower = name.lower()  # I normalize to lower case for predictable checks

    # I apply very small, explicit rules so it's obvious what happens.
    if lower.startswith("passport_"):
        return "passport"  # I tag this bag as a passport document
    if lower.startswith("proof_of_address_"):
        return "proof_of_address"  # I tag this bag as a proof of address
    if lower.startswith("kyb_"):
        return "kyb"  # I tag this bag as a KYB document
    return "unknown"  # I default to unknown so the next step can decide what to do


if __name__ == "__main__":
    # I demonstrate quick checks you can copy/paste into a REPL.
    samples = [
        "passport_alex.png",
        "proof_of_address_bill.pdf",
        "kyb_company.pdf",
        "random.png",
    ]
    for s in samples:
        print(s, "->", infer_document_type(s))  # I print each mapping so I can see if rules make sense

