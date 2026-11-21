"""Shared test plumbing. Later tasks add the fake model and the environment's isolation here."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "adk_spec"
