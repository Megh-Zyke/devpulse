"""
DevPulse — Firestore persistence

Saves each run's agent output (research items, PR reviews, monitor alerts,
and the final digest) to a Firebase Firestore collection so history isn't
lost between runs.

Credentials (either works):
  FIREBASE_CREDENTIALS_JSON  — full service-account JSON as a string
  FIREBASE_CREDENTIALS_PATH  — path to a service-account JSON file
                                (default: "firebase-credentials.json")

If neither is configured, saving is skipped — local/dev runs without
Firestore access still work.
"""

from __future__ import annotations
import json
import os
from functools import lru_cache
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore

DIGESTS_COLLECTION = "digests"


def _credentials_available() -> bool:
    if os.getenv("FIREBASE_CREDENTIALS_JSON"):
        return True
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
    return os.path.exists(cred_path)


@lru_cache(maxsize=1)
def _get_client():
    if not firebase_admin._apps:
        cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if cred_json:
            cred = credentials.Certificate(json.loads(cred_json))
        else:
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
            cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def save_run(state: dict[str, Any], digest_markdown: str) -> None:
    """Persist one DevPulse run to Firestore. No-op if not configured."""
    if not _credentials_available():
        return

    db = _get_client()
    run_date = state.get("run_date", "")
    db.collection(DIGESTS_COLLECTION).document(run_date).set({
        "run_date": run_date,
        "topics": state.get("topics", []),
        "github_repos": state.get("github_repos", []),
        "research_items": state.get("research_items", []),
        "pr_reviews": state.get("pr_reviews", []),
        "monitor_alerts": state.get("monitor_alerts", []),
        "errors": state.get("errors", []),
        "digest_markdown": digest_markdown,
        "created_at": firestore.SERVER_TIMESTAMP,
    })


def get_run(run_date: str) -> dict[str, Any] | None:
    """Fetch a previously saved run by date (YYYY-MM-DD). None if not configured or not found."""
    if not _credentials_available():
        return None
    db = _get_client()
    doc = db.collection(DIGESTS_COLLECTION).document(run_date).get()
    return doc.to_dict() if doc.exists else None
