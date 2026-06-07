"""
daily-digest — 2-3 storie curate per persona, stile Breaking Italy.
Provider: Gemini 2.5 Flash (free tier) con Google Search.
"""

import os
import smtplib
import json
import html as html_lib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import PROFILES, PROMPT_TEMPLATE

# ── Config ────────────────────────────────────────────────────────────────────

GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MESI   = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
          "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]

def italian_date(d: date) -> str:
    return f"{GIORNI[d.weekday()]} {d.day} {MESI[d.month - 1]} {d.year}"

HISTORY_FILE = "history.json"
HISTORY_DAYS = 7

def load_history() -> dict:
    """Storico delle storie inviate per profilo. Robusto a file mancante/corrotto."""
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _recent_entries(history: dict, profile_name: str) -> list:
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=HISTORY_DAYS)).isoformat()
    return [e for e in history.get(profile_name, []) if e.get("date", "") >= cutoff]

def recent_titles(history: dict, profile_name: str) -> list:
    """Titoli inviati negli ultimi HISTORY_DAYS giorni per questo profilo."""
    return [e["title"] for e in _recent_entries(history, profile_name)]

def recent_topics(history: dict, profile_name: str) -> list:
    """Temi trattati di recente, dal più frequente, per evitare di ripeterli."""
    from collections import Counter
    counts = Counter(
        e.get("topic", "").strip() for e in _recent_entries(history, profile_name)
        if e.get("topic", "").strip()
    )
    return [topic for topic, _ in counts.most_common()]

def record_sent(history: dict, profile_name: str, stories: list) -> None:
    """Aggiunge le storie inviate allo storico e pota le voci più vecchie di HISTORY_DAYS."""
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=HISTORY_DAYS)).isoformat()
    today_iso = date.today().isoformat()
    entries = [e for e in history.get(profile_name, []) if e.get("date", "") >= cutoff]
    for s in stories:
        entries.append({
            "date": today_iso,
            "title": s.get("title", ""),
            "url": s.get("url", ""),
            "topic": s.get("topic", ""),
        })
    history[profile_name] = entries

def save_history(history: dict) -> None:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def parse_response(raw: str) -> tuple[list, list]:
    """Estrae stories e also_noting da una risposta LLM, tollerando markdown e testo extra."""
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("risposta vuota dal provider")

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    # fallback: estrai il primo oggetto JSON bilanciato se c'è testo intorno
    if not raw.startswith("{"):
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            raw = raw[start:end + 1]

    data = json.loads(raw)
    return data.get("stories", []), (data.get("also_noting", []) or [])[:6]

SENDER         = "ing.albertodimaria@gmail.com"
SMTP_PASS      = os.environ["GMAIL_APP_PASSWORD"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


# ── Prompt ────────────────────────────────────────────────────────────────────

def build_prompt(profile: dict, today: str, recent: list | None = None,
                 recent_topics: list | None = None) -> str:
    template = profile.get("prompt_template", PROMPT_TEMPLATE)
    prompt = template.format(interests=profile["interests"], today=today)
    if recent:
        avoid = "\n".join(f"- {t}" for t in recent)
        prompt += (
            "\n\nIMPORTANTE — queste storie sono già state inviate nei giorni scorsi. "
            "NON riproporle e non scegliere notizie sostanzialmente equivalenti:\n" + avoid
        )
    if recent_topics:
        temi = ", ".join(recent_topics)
        prompt += (
            "\n\nVARIETÀ — nei giorni scorsi hai già trattato spesso questi temi: " + temi + ". "
            "Per le storie dopo la prima, privilegia temi DIVERSI da questi e diversi tra loro."
        )
    return prompt


# ── Gemini ────────────────────────────────────────────────────────────────────

def fetch_with_gemini(profile: dict, today: str, recent: list | None = None,
                      recent_topics: list | None = None) -> tuple[list, list]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_prompt(profile, today, recent, recent_topics),
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3,
        ),
    )

    return parse_response(response.text)


# ── Fetch ─────────────────────────────────────────────────────────────────────

def fetch_digest(profile: dict, today: str, recent: list | None = None,
                 recent_topics: list | None = None) -> tuple[list, list, str]:
    import time

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY non impostato")

    last_err = None
    for attempt in range(4):  # 0 = initial, 1-3 = retries
        if attempt > 0:
            print(f"  Retry {attempt}/3…")
            time.sleep(10)
        try:
            if attempt == 0:
                print("  Trying Gemini…")
            stories, also_noting = fetch_with_gemini(profile, today, recent, recent_topics)
            return stories, also_noting, "Gemini"
        except Exception as e:
            last_err = e
            err = str(e)
            if any(k in err for k in ("503", "UNAVAILABLE")) and attempt < 3:
                continue
            if any(k in err for k in ("429", "RESOURCE_EXHAUSTED", "quota")):
                print(f"  ⚠ GEMINI QUOTA ESAURITA: {err}")
            elif any(k in err for k in ("503", "UNAVAILABLE")):
                print(f"  ⚠ GEMINI UNAVAILABLE dopo 3 tentativi: {err}")
            else:
                print(f"  ⚠ GEMINI ERROR: {err}")
            break

    raise RuntimeError(f"Gemini non disponibile: {last_err}")


# ── HTML ───────────────────────────────────────────────────────────────────────

TOPIC_COLORS = {
    "ai": "#7c3aed", "audio": "#0e7490", "colombia": "#dc2626",
    "letteratura": "#059669", "literatura": "#059669", "design": "#d97706",
    "jazz": "#be185d", "musica": "#be185d", "brujería": "#b45309",
    "brujeria": "#b45309", "scienza": "#6b7280", "filosofia": "#6b7280",
    "arte": "#ea580c", "fotografia": "#0284c7", "cinema": "#7c3aed",
    "ambiente": "#16a34a", "sostenibilità": "#16a34a", "ux": "#d97706",
}

def topic_color(topic: str) -> str:
    t = topic.lower()
    for key, color in TOPIC_COLORS.items():
        if key in t:
            return color
    return "#374151"

def safe_url(url: str) -> str:
    """Accetta solo http(s), altrimenti '#'. Escapa per il contesto attributo HTML."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return "#"
    return html_lib.escape(url, quote=True)

def render_story(story: dict, index: int) -> str:
    color  = topic_color(story.get("topic", ""))
    num    = ["①", "②", "③"][index] if index < 3 else f"{index+1}."
    topic  = html_lib.escape(story.get("topic", ""))
    title  = html_lib.escape(story.get("title", ""))
    body   = html_lib.escape(story.get("body", ""))
    source = html_lib.escape(story.get("source", ""))
    url    = safe_url(story.get("url", ""))
    return (
        '\n    <div style="margin-bottom:28px;padding:22px;background:#f9fafb;'
        'border-radius:10px;border-left:4px solid ' + color + ';">'
        '\n      <div style="margin-bottom:8px;">'
        '\n        <span style="font-size:10px;font-weight:700;text-transform:uppercase;'
        'letter-spacing:1px;color:' + color + ';">' + topic + '</span>'
        '\n      </div>'
        '\n      <h2 style="margin:0 0 12px;font-size:17px;font-weight:700;'
        'color:#111827;line-height:1.4;font-family:Georgia,serif;">'
        '\n        ' + num + ' ' + title +
        '\n      </h2>'
        '\n      <p style="margin:0 0 14px;font-size:14px;color:#374151;line-height:1.75;">'
        '\n        ' + body +
        '\n      </p>'
        '\n      <a href="' + url + '" style="font-size:12px;color:' + color + ';'
        'text-decoration:none;font-weight:600;">'
        '\n        Leggi su ' + source + ' →'
        '\n      </a>'
        '\n    </div>'
    )

def render_also_noting(items: list) -> str:
    if not items:
        return ""
    rows = ""
    for item in items:
        color = topic_color(item.get("topic", ""))
        topic = html_lib.escape(item.get("topic", ""))
        title = html_lib.escape(item.get("title", ""))
        url   = safe_url(item.get("url", ""))
        rows += (
            '\n      <li style="margin-bottom:8px;">'
            '<span style="font-size:10px;font-weight:700;text-transform:uppercase;'
            'letter-spacing:1px;color:' + color + ';margin-right:6px;">' + topic + '</span>'
            '<a href="' + url + '" style="font-size:13px;color:#374151;text-decoration:none;">'
            + title + '</a>'
            '</li>'
        )
    return (
        '\n    <div style="margin-top:8px;padding:20px 22px;background:#f3f4f6;'
        'border-radius:10px;">'
        '\n      <p style="margin:0 0 10px;font-size:11px;font-weight:700;'
        'text-transform:uppercase;letter-spacing:1px;color:#6b7280;">NB — anche oggi</p>'
        '\n      <ul style="margin:0;padding-left:16px;list-style:disc;">'
        + rows +
        '\n      </ul>'
        '\n    </div>'
    )

def build_html(stories: list, also_noting: list, today: str, provider: str, name: str = "") -> str:
    # togli dalle menzioni rapide gli URL e i titoli già usati nelle storie principali
    used_urls   = {(s.get("url") or "").strip() for s in stories}
    used_titles = {(s.get("title") or "").strip().lower() for s in stories}
    also_noting = [
        it for it in also_noting
        if (it.get("url") or "").strip() not in used_urls
        and (it.get("title") or "").strip().lower() not in used_titles
    ]
    stories_html     = "".join(render_story(s, i) for i, s in enumerate(stories))
    also_noting_html = render_also_noting(also_noting)
    count_label      = f"{len(stories)} stori{'a' if len(stories)==1 else 'e'} oggi"
    header_title     = "daily news of " + html_lib.escape(name) if name else "daily news"
    return (
        '<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head>\n'
        '<body style="margin:0;padding:0;background:#f3f4f6;'
        'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">\n'
        '  <div style="max-width:600px;margin:32px auto;background:#fff;'
        'border-radius:14px;box-shadow:0 1px 6px rgba(0,0,0,0.08);overflow:hidden;">\n'
        '    <div style="background:#111827;padding:28px 32px;">\n'
        '      <h1 style="margin:0 0 4px;color:#fff;font-size:20px;font-weight:700;">' + header_title + '</h1>\n'
        '      <p style="margin:0;color:#9ca3af;font-size:12px;">' + today + ' · ' + count_label + '</p>\n'
        '    </div>\n'
        '    <div style="padding:28px 32px;">' + stories_html + also_noting_html + '</div>\n'
        '    <div style="padding:16px 32px;background:#f9fafb;text-align:center;border-top:1px solid #e5e7eb;">\n'
        '      <p style="margin:0;font-size:11px;color:#9ca3af;">\n'
        '        Curato da ' + provider + ' · github.com/albedimaria/digest\n'
        '      </p>\n'
        '    </div>\n'
        '  </div>\n'
        '</body></html>'
    )


# ── Email ──────────────────────────────────────────────────────────────────────

def build_subject(stories: list) -> str:
    top   = (stories[0].get("title", "") if stories else "").strip()
    extra = len(stories) - 1
    if not top:
        return f"☀️ {len(stories)} storie per oggi"
    suffix = f" (+{extra})" if extra > 0 else ""
    return f"☀️ {top}{suffix}"

def send_email(recipient: str, html: str, subject: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER
    msg["To"]      = recipient
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER, SMTP_PASS)
        server.sendmail(SENDER, recipient, msg.as_string())
    print(f"  ✓ Inviata a {recipient}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    import sys
    today   = italian_date(date.today())
    history = load_history()
    failed  = False

    for profile in PROFILES:
        name = profile["name"]
        print(f"\n[{name}] Fetching digest…")
        try:
            recent = recent_titles(history, name)
            topics = recent_topics(history, name)
            if recent:
                print(f"  ({len(recent)} storie recenti da evitare; temi: {', '.join(topics) or '—'})")
            stories, also_noting, provider = fetch_digest(profile, today, recent, topics)
            if not stories:
                print(f"  ✗ Nessuna storia trovata per {name}, skip.")
                failed = True
                continue
            print(f"  → {len(stories)} stories, {len(also_noting)} also-noting via {provider}")
            html = build_html(stories, also_noting, today, provider, name)
            send_email(profile["recipient"], html, build_subject(stories))
            record_sent(history, name, stories)
        except Exception as e:
            print(f"  ✗ Errore per {name}: {e}")
            failed = True

    save_history(history)

    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()
