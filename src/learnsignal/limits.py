"""Data limits, all in one place.

On someone's own computer (standalone, a local Signal Hub or an internal deployment) Learn Signal has no built-in
limits: every calculation is polynomial in the size of the table (options x scenarios x study results), so the
computer's memory and processor are the limit. A public demo sets SIGNAL_PUBLIC=1; only then do the hard caps below
apply, to protect a shared server.
"""
import os

DEMO = {
    "upload_bytes": 50 * 1024 * 1024,      # spreadsheets in total, or one JSON file
    "unpacked_bytes": 200 * 1024 * 1024,   # an .xlsx archive once unpacked (compressed-archive bombs)
    "archive_members": 1000,               # files inside an .xlsx archive
    "sheets": 30,
    "rows": 10_000,                        # per sheet or CSV
    "columns": 80,
    "cells": 250_000,                      # across all uploaded files
    "paste_chars": 1_000_000,              # a pasted AI reply
    "notes_chars": 35_000,                 # material pasted into the AI prompt
    "states": 30,
    "actions": 12,
    "payoffs": 360,
    "studies": 12,
    "results_per_study": 10,
    "signals": 3_600,
    "questions": 20,
    "partitions": 600,
    "sources": 100,
}
BYTES = {"upload_bytes", "unpacked_bytes"}
DEMO_NOTE = "This is a limit of the public demo; the downloaded app has none."
MEMORY = ("Not enough memory for this on this computer. Close other programs, or remove sheets, rows and columns "
          "that are not part of the decision table, and try again.")


def public() -> bool:
    """True in a public demo, which sets SIGNAL_PUBLIC=1. Independent of SIGNAL_HUB."""
    return os.environ.get("SIGNAL_PUBLIC") == "1"


def cap(name: str) -> int | None:
    """The demo cap for a quantity, or None (no limit) outside a public demo."""
    return DEMO[name] if public() else None


def describe(name: str) -> str:
    value = DEMO[name]
    return f"{value // 2**20:,} MB" if name in BYTES else f"{value:,}"


def check(name: str, value: int, what: str) -> None:
    """Raise a DataProblem naming the demo limit when a public demo's cap is exceeded."""
    limit = cap(name)
    if limit is not None and value > limit:
        from learnsignal.portable import DataProblem

        raise DataProblem(f"{what}: more than {describe(name)}. {DEMO_NOTE}")
