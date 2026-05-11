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

# ── Config ────────────────────────────────────────────────────────────────────

SENDER         = "ing.albertodimaria@gmail.com"
SMTP_PASS      = os.environ["GMAIL_APP_PASSWORD"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY", "")

PROFILES = [
    {
        "name": "Alberto",
        "recipient": "ing.albertodimaria@gmail.com",
        "interests": """
- AI & developer tools: nuovi modelli, API, agentic frameworks, strumenti per dev
- Audio AI & music tech: modelli audio/musicali, MIR, ricerca su arXiv/ISMIR — solo roba significativa
- Startup audio/AI lanciate da piccoli team o solo dev
- Colombia: attualità, politica, cultura, musica — varia tra cultura, musica, economia, società, storia, ambiente
- Letteratura latinoamericana e spagnola: nuove uscite, premi, autori, cultura letteraria
- Design & UX: trend, tool, case study, ispirazioni visive
- Jazz, black music (soul, funk, R&B, hip-hop, afrobeat), musica latina (salsa, cumbia, bossa nova, MPB)
  → NO: elettronica mainstream, pop italiano, EDM
- Brujería messicana, curanderismo, tradizioni precolombiane: antropologia, storia, cultura
- Curiosità scientifiche o filosofiche profonde (stile Quanta Magazine) — solo se c'è qualcosa davvero notevole
""",
    },
    {
        "name": "Laura",
        "recipient": "laura.zanchetta00@gmail.com",
        "interests": """
- Arte contemporanea & gallerie: mostre, artisti emergenti, mercato dell'arte
- Illustrazione editoriale & poster: illustratori da seguire, nuove pubblicazioni, campagne visive
- Fotografia: fotografi, tendenze, progetti documentari, fotogiornalismo
- UX/UI design: tool e novità (Figma, Framer...), design system, accessibilità, trend visivi & tipografia
- AI generativa applicata al design e all'arte: nuovi modelli, tool creativi, impatto sul mondo visivo
- Cinema & serie — con focus su backstage e processo creativo, non recensioni:
  film d'autore, festival (Cannes, Venezia, Berlino e indipendenti), curiosità di produzione
- Ambiente & sostenibilità: cambiamento climatico, biodiversità, design etico e sostenibile
- Attualità generale (geopolitica, società) — solo se c'è qualcosa di davvero importante
""",
    },
]

# ── Prompt ────────────────────────────────────────────────────────────────────

def build_prompt(interests: str, today: str) -> str:
    return f"""Sei un editor che cura una newsletter quotidiana personalizzata da leggere in 5 minuti in metropolitana.

Gli interessi del lettore sono:
{interests}

Oggi è {today}.

Il tuo compito:
1. Cerca notizie di oggi su questi temi usando il web.
2. Scegli le 2-3 storie più interessanti e rilevanti tra tutti i temi.
   - Privilegia qualità sulla varietà: se ci sono due notizie forti sullo stesso tema, prendile entrambe.
   - Se su un tema non c'è niente di interessante oggi, ignoralo.
   - Cerca almeno 3-4 temi prima di decidere cosa tenere.
   - Evita di selezionare sempre lo stesso tipo di notizia per lo stesso tema.
3. Per ogni storia scrivi un pezzo approfondito stile Breaking Italy:
   - Titolo diretto e informativo
   - 4-6 frasi che partono dal fatto del giorno come gancio e lo aprono in un'analisi più ampia:
     contesto storico o strutturale, conseguenze, perché conta oltre la cronaca immediata
   - La cronaca pura non basta: ogni pezzo deve lasciare al lettore una comprensione più profonda
   - Testo fluente e giornalistico, no elenchi puntati
   - Indica il tema (es. "Audio AI", "Cinema", "Design")

Rispondi SOLO con JSON valido, zero testo fuori dal JSON, zero markdown:
{{
  "stories": [
    {{
      "topic": "nome del tema",
      "title": "Titolo",
      "body": "Testo 4-6 frasi...",
      "source": "Nome fonte",
      "url": "https://..."
    }}
  ]
}}"""


# ── Gemini ────────────────────────────────────────────────────────────────────

def fetch_with_gemini(interests: str, today: str) -> list:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_prompt(interests, today),
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

    return json.loads(raw).get("stories", [])


# ── Perplexity ────────────────────────────────────────────────────────────────

def fetch_with_perplexity(interests: str, today: str) -> list:
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai non installato — aggiungi 'openai' a requirements.txt")

    client = OpenAI(api_key=PERPLEXITY_KEY, base_url="https://api.perplexity.ai")
    response = client.chat.completions.create(
        model="sonar",
        messages=[{"role": "user", "content": build_prompt(interests, today)}],
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

    return json.loads(raw).get("stories", [])


# ── Fetch with fallback ───────────────────────────────────────────────────────

def fetch_digest(interests: str, today: str) -> tuple[list, str]:
    import time

    if GEMINI_API_KEY:
        for attempt in range(4):  # 0 = initial, 1-3 = retries
            if attempt > 0:
                print(f"  Retry {attempt}/3…")
                time.sleep(10)
            try:
                if attempt == 0:
                    print("  Trying Gemini…")
                stories = fetch_with_gemini(interests, today)
                return stories, "Gemini"
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
            stories = fetch_with_perplexity(interests, today)
            return stories, "Perplexity"
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
    return f"""
    <div style="margin-bottom:28px;padding:22px;background:#f9fafb;
                border-radius:10px;border-left:4px solid {color};">
      <div style="margin-bottom:8px;">
        <span style="font-size:10px;font-weight:700;text-transform:uppercase;
                     letter-spacing:1px;color:{color};">{topic}</span>
      </div>
      <h2 style="margin:0 0 12px;font-size:17px;font-weight:700;
                 color:#111827;line-height:1.4;font-family:Georgia,serif;">
        {num} {title}
      </h2>
      <p style="margin:0 0 14px;font-size:14px;color:#374151;line-height:1.75;">
        {body}
      </p>
      <a href="{url}" style="font-size:12px;color:{color};
                             text-decoration:none;font-weight:600;">
        Leggi su {source} →
      </a>
    </div>"""

def build_html(stories: list, today: str, provider: str) -> str:
    stories_html = "".join(render_story(s, i) for i, s in enumerate(stories))
    count_label  = f"{len(stories)} stori{'a' if len(stories)==1 else 'e'} oggi"
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:600px;margin:32px auto;background:#fff;
              border-radius:14px;box-shadow:0 1px 6px rgba(0,0,0,0.08);overflow:hidden;">
    <div style="background:#111827;padding:28px 32px;">
      <h1 style="margin:0 0 4px;color:#fff;font-size:20px;font-weight:700;">le news per te</h1>
      <p style="margin:0;color:#9ca3af;font-size:12px;">{today} · {count_label}</p>
    </div>
    <div style="padding:28px 32px;">{stories_html}</div>
    <div style="padding:16px 32px;background:#f9fafb;text-align:center;border-top:1px solid #e5e7eb;">
      <p style="margin:0;font-size:11px;color:#9ca3af;">
        Curato da {provider} · github.com/albedimaria/digest
      </p>
    </div>
  </div>
</body></html>"""


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
            stories, provider = fetch_digest(profile["interests"], today)
            if not stories:
                print(f"  ✗ Nessuna storia trovata per {profile['name']}, skip.")
                continue
            print(f"  → {len(stories)} stories via {provider}")
            html = build_html(stories, today, provider)
            send_email(profile["recipient"], html, today, len(stories))
        except Exception as e:
            print(f"  ✗ Errore per {profile['name']}: {e}")

if __name__ == "__main__":
    main()
