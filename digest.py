"""
daily-digest — 2-3 storie curate per persona, stile Breaking Italy.
Primary: Gemini 2.5 Flash | Fallback: Perplexity Sonar
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

SENDER         = "ing.albertodimaria@gmail.com"
SMTP_PASS      = os.environ["GMAIL_APP_PASSWORD"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY", "")


# ── Prompt ────────────────────────────────────────────────────────────────────

def build_prompt(profile: dict, today: str) -> str:
    template = profile.get("prompt_template", PROMPT_TEMPLATE)
    return template.format(interests=profile["interests"], today=today)


# ── Gemini ────────────────────────────────────────────────────────────────────

def fetch_with_gemini(profile: dict, today: str) -> tuple[list, list]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_prompt(profile, today),
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3,
        ),
    )

    raw = (response.text or "").strip()
    if not raw:
        raise ValueError("Gemini ha restituito una risposta vuota")

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)
    return data.get("stories", []), data.get("also_noting", [])


# ── Perplexity ────────────────────────────────────────────────────────────────

def fetch_with_perplexity(profile: dict, today: str) -> tuple[list, list]:
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai non installato — aggiungi 'openai' a requirements.txt")

    client = OpenAI(api_key=PERPLEXITY_KEY, base_url="https://api.perplexity.ai")
    response = client.chat.completions.create(
        model="sonar",
        messages=[{"role": "user", "content": build_prompt(profile, today)}],
        temperature=0.3,
    )

    raw = (response.choices[0].message.content or "").strip()
    if not raw:
        raise ValueError("Perplexity ha restituito una risposta vuota")

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)
    return data.get("stories", []), data.get("also_noting", [])


# ── Fetch with fallback ───────────────────────────────────────────────────────

def fetch_digest(profile: dict, today: str) -> tuple[list, list, str]:
    import time

    if GEMINI_API_KEY:
        for attempt in range(4):  # 0 = initial, 1-3 = retries
            if attempt > 0:
                print(f"  Retry {attempt}/3…")
                time.sleep(10)
            try:
                if attempt == 0:
                    print("  Trying Gemini…")
                stories, also_noting = fetch_with_gemini(profile, today)
                return stories, also_noting, "Gemini"
            except Exception as e:
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

    if PERPLEXITY_KEY:
        try:
            print("  Trying Perplexity…")
            stories, also_noting = fetch_with_perplexity(profile, today)
            return stories, also_noting, "Perplexity"
        except Exception as e:
            err = str(e)
            if any(k in err for k in ("429", "quota", "rate")):
                print(f"  ⚠ PERPLEXITY QUOTA ESAURITA: {err}")
            else:
                print(f"  ⚠ PERPLEXITY ERROR: {err}")

    raise RuntimeError("Nessun provider disponibile — controlla GEMINI_API_KEY e PERPLEXITY_API_KEY")


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

def render_story(story: dict, index: int) -> str:
    color  = topic_color(story.get("topic", ""))
    num    = ["①", "②", "③"][index] if index < 3 else f"{index+1}."
    topic  = html_lib.escape(story.get("topic", ""))
    title  = html_lib.escape(story.get("title", ""))
    body   = html_lib.escape(story.get("body", ""))
    source = html_lib.escape(story.get("source", ""))
    url    = story.get("url", "#")
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
        url   = item.get("url", "#")
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

def build_html(stories: list, also_noting: list, today: str, provider: str) -> str:
    stories_html     = "".join(render_story(s, i) for i, s in enumerate(stories))
    also_noting_html = render_also_noting(also_noting)
    count_label      = f"{len(stories)} stori{'a' if len(stories)==1 else 'e'} oggi"
    return (
        '<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head>\n'
        '<body style="margin:0;padding:0;background:#f3f4f6;'
        'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">\n'
        '  <div style="max-width:600px;margin:32px auto;background:#fff;'
        'border-radius:14px;box-shadow:0 1px 6px rgba(0,0,0,0.08);overflow:hidden;">\n'
        '    <div style="background:#111827;padding:28px 32px;">\n'
        '      <h1 style="margin:0 0 4px;color:#fff;font-size:20px;font-weight:700;">daily news of</h1>\n'
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

def send_email(recipient: str, html: str, today: str, story_count: int):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"☀️ {story_count} storie per oggi — {today}"
    msg["From"]    = SENDER
    msg["To"]      = recipient
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER, SMTP_PASS)
        server.sendmail(SENDER, recipient, msg.as_string())
    print(f"  ✓ Inviata a {recipient}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    today = date.today().strftime("%A, %d %B %Y")

    for profile in PROFILES:
        print(f"\n[{profile['name']}] Fetching digest…")
        try:
            stories, also_noting, provider = fetch_digest(profile, today)
            if not stories:
                print(f"  ✗ Nessuna storia trovata per {profile['name']}, skip.")
                continue
            print(f"  → {len(stories)} stories, {len(also_noting)} also-noting via {provider}")
            html = build_html(stories, also_noting, today, provider)
            send_email(profile["recipient"], html, today, len(stories))
        except Exception as e:
            print(f"  ✗ Errore per {profile['name']}: {e}")

if __name__ == "__main__":
    main()
