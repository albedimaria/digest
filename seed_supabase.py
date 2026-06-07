"""
Inserisce i profili di profiles.json dentro Supabase (tabella profiles).
Eseguire UNA volta dopo aver creato lo schema (supabase_schema.sql) e impostato
le variabili d'ambiente SUPABASE_URL e SUPABASE_SERVICE_KEY.

    python seed_supabase.py
"""

import os
import json
import urllib.request
import urllib.parse

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]


def sb(method, path, params=None, body=None):
    u = f"{URL}/rest/v1/{path}"
    if params:
        u += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(u, data=data, method=method)
    req.add_header("apikey", KEY)
    req.add_header("Authorization", f"Bearer {KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    with urllib.request.urlopen(req, timeout=30) as r:
        txt = r.read().decode()
        return json.loads(txt) if txt else None


def main():
    with open("profiles.json", encoding="utf-8") as f:
        profiles = json.load(f)

    for p in profiles:
        existing = sb("GET", "profiles", {"recipient": f"eq.{p['recipient']}", "select": "id"})
        row = {
            "name":            p["name"],
            "recipient":       p["recipient"],
            "active":          p.get("active", True),
            "interests":       p.get("interests", ""),
            "prompt_template": p.get("prompt_template"),
            "satisfaction":    p.get("satisfaction"),
        }
        if existing:
            sb("PATCH", "profiles", {"recipient": f"eq.{p['recipient']}"}, row)
            print(f"  aggiornato: {p['name']}")
        else:
            sb("POST", "profiles", body=row)
            print(f"  inserito:   {p['name']}")

    print("seed completato.")


if __name__ == "__main__":
    main()
