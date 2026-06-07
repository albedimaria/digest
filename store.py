"""
Persistenza dual-mode: Supabase se SUPABASE_URL + SUPABASE_SERVICE_KEY sono
impostati, altrimenti file JSON locali (profiles.json / history.json).
Interfaccia profile-centric usata da digest.py.
"""

import os
import json
from datetime import date, timedelta
from collections import Counter

HISTORY_DAYS  = 7
SUPABASE_URL  = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY  = os.environ.get("SUPABASE_SERVICE_KEY", "")
USE_SUPABASE  = bool(SUPABASE_URL and SUPABASE_KEY)

PROFILES_FILE = "profiles.json"
HISTORY_FILE  = "history.json"

_history = None  # cache per il backend JSON


def _cutoff() -> str:
    return (date.today() - timedelta(days=HISTORY_DAYS)).isoformat()


# ── Supabase REST (PostgREST) via urllib ────────────────────────────────────────

def _sb(method: str, path: str, params: dict | None = None, body=None):
    import urllib.request, urllib.parse, urllib.error
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    if method == "POST":
        req.add_header("Prefer", "return=minimal")
    with urllib.request.urlopen(req, timeout=30) as r:
        txt = r.read().decode()
        return json.loads(txt) if txt else None


# ── JSON backend ────────────────────────────────────────────────────────────────

def _load_history() -> dict:
    global _history
    if _history is None:
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                _history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _history = {}
    return _history


# ── Interfaccia pubblica ────────────────────────────────────────────────────────

def get_profiles() -> list:
    """Profili attivi."""
    if USE_SUPABASE:
        return _sb("GET", "profiles", {"active": "eq.true", "select": "*"}) or []
    with open(PROFILES_FILE, encoding="utf-8") as f:
        return [p for p in json.load(f) if p.get("active", True)]


def get_recent(profile: dict) -> tuple[list, list]:
    """(titoli, temi) inviati negli ultimi HISTORY_DAYS giorni; temi dal più frequente."""
    if USE_SUPABASE:
        rows = _sb("GET", "sent_stories", {
            "profile_id": f"eq.{profile['id']}",
            "sent_date":  f"gte.{_cutoff()}",
            "select":     "title,topic",
        }) or []
    else:
        rows = [e for e in _load_history().get(profile["name"], []) if e.get("date", "") >= _cutoff()]

    titles = [r.get("title", "") for r in rows if r.get("title")]
    topics = [t for t, _ in Counter(
        r.get("topic", "").strip() for r in rows if r.get("topic", "").strip()
    ).most_common()]
    return titles, topics


def record_sent(profile: dict, stories: list) -> None:
    """Registra le storie inviate oggi."""
    today_iso = date.today().isoformat()
    if USE_SUPABASE:
        body = [{
            "profile_id": profile["id"],
            "sent_date":  today_iso,
            "title":      s.get("title", ""),
            "url":        s.get("url", ""),
            "topic":      s.get("topic", ""),
        } for s in stories]
        if body:
            _sb("POST", "sent_stories", body=body)
    else:
        hist = _load_history()
        entries = [e for e in hist.get(profile["name"], []) if e.get("date", "") >= _cutoff()]
        for s in stories:
            entries.append({
                "date":  today_iso,
                "title": s.get("title", ""),
                "url":   s.get("url", ""),
                "topic": s.get("topic", ""),
            })
        hist[profile["name"]] = entries


def flush() -> None:
    """Salva lo stato del backend JSON su disco (no-op in modalità Supabase)."""
    if not USE_SUPABASE and _history is not None:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(_history, f, ensure_ascii=False, indent=2)


def backend_name() -> str:
    return "Supabase" if USE_SUPABASE else "JSON locale"
