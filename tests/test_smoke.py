"""Smoke test for multi-agentic.

This test exists to make CI land green from commit 1. Replace with real
tests as the repo grows. Per global rule §6 (verify work), every
non-trivial change should add or modify a test.
"""

from __future__ import annotations


def test_python_runs() -> None:
    """Trivial gate — Python is alive and can run a test.

    If you haven't written real tests yet, this is here so that pytest
    exits 0 instead of exit 5 (no tests collected) — the latter would
    fail CI. Replace this test the moment you have something actually
    worth testing.
    """
    assert 1 + 1 == 2
