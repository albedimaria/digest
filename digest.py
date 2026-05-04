"""
daily-digest — 2-3 storie curate tra tutti i tuoi interessi, stile Breaking Italy.
Una chiamata a Claude con web search, zero sezioni fisse.
"""

import os
import smtplib
import json
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import anthropic

# ── Config ────────────────────────────────────────────────────────────────────

RECIPIENT     = "ing.albertodimaria@gmail.com"
SENDER        = "ing.albertodimaria@gmail.com"
SMTP_PASS     = os.environ["GMAIL_APP_PASSWORD"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]

INTERESTS = """
- AI & developer tools: nuovi modelli, API, agentic frameworks, strumenti per dev
- Audio AI & music tech: modelli audio/musicali, MIR, ricerca su arXiv/ISMIR — solo roba significativa
- Startup audio/AI lanciate da piccoli team o solo dev
- Colombia: attualità, politica, cultura, musica
- Letteratura latinoamericana e spagnola: nuove uscite, premi, autori, cultura letteraria
- Design & UX: trend, tool, case study, ispirazioni visive
- Jazz, black music (soul, funk, R&B, hip-hop, afrobeat), musica latina (salsa, cumbia, bossa nova, MPB)
  → NO: elettronica mainstream, pop italiano, EDM
- Brujería messicana, curanderismo, tradizioni precolombiane: antropologia, storia, cultura
- Curiosità scientifiche o filosofiche profonde (stile Quanta Magazine) — solo se c'è qualcosa davvero notevole
"""

SYSTEM_PROMPT = f"""Sei un editor che cura una newsletter quotidiana personalizzata da leggere in 5 minuti.

Gli interessi del lettore sono:
{INTERESTS}

Il tuo compito:
1. Usa il web search per esplorare le notizie di oggi su questi temi.
2. Scegli le 2-3 storie più interessanti e rilevanti dell'intera giornata tra tutti i temi.
   - Privilegia la qualità sulla varietà: se ci sono due notizie forti sullo stesso tema, prendile entrambe.
   - Se su un tema non c'è niente di interessante oggi, ignoralo.
   - Cerca almeno 3-4 temi prima di decidere cosa tenere.
3. Per ogni storia selezionata, scrivi un pezzo approfondito stile Breaking Italy:
   - Un titolo diretto e informativo
   - 4-6 frasi che spiegano la notizia con contesto, perché importa, e cosa succederà dopo
   - Niente elenchi puntati: testo fluente, giornalistico
   - Indica il tema di appartenenza (es. "Audio AI", "Colombia", "Design")

Rispondi SOLO con un oggetto JSON valido, nessun testo fuori dal JSON, nessun markdown:
{{
  "stories": [
    {{
      "topic": "nome del tema",
      "title": "Titolo della notizia",
      "body": "Testo approfondito da 4-6 frasi...",
      "source": "Nome della fonte",
      "url": "https://..."
    }}
  ]
}}
"""

# ── Fetch ──────────────────────────────────────────────────────────────────────

def fetch_digest(client: anthropic.Anthropic) -> list:
    today = date.today().strftime("%d %B %Y")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2500,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{
            "role": "user",
            "content": f"Oggi è {today}. Trova le notizie più interessanti per me."
        }],
    )

    raw = "".join(
        block.text for block in response.content if hasattr(block, "text")
    ).strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw).get("stories", [])


# ── HTML ───────────────────────────────────────────────────────────────────────

TOPIC_COLORS = {
    "ai": "#7c3aed",
    "audio": "#0e7490",
    "colombia": "#dc2626",
    "letteratura": "#059669",
    "literatura": "#059669",
    "design": "#d97706",
    "jazz": "#be185d",
    "musica": "#be185d",
    "brujería": "#b45309",
    "brujeria": "#b45309",
    "scienza": "#6b7280",
    "filosofia": "#6b7280",
}

def topic_color(topic: str) -> str:
    t = topic.lower()
    for key, color in TOPIC_COLORS.items():
        if key in t:
            return color
    return "#374151"


def render_story(story: dict, index: int) -> str:
    color  = topic_color(story.get("topic", ""))
    topic  = story.get("topic", "")
    title  = story.get("title", "")
    body   = story.get("body", "")
    source = story.get("source", "")
    url    = story.get("url", "#")
    num    = ["①", "②", "③"][index] if index < 3 else f"{index+1}."

    return f"""
    <div style="margin-bottom:28px; padding:22px; background:#f9fafb;
                border-radius:10px; border-left:4px solid {color};">
      <div style="margin-bottom:8px;">
        <span style="font-size:10px; font-weight:700; text-transform:uppercase;
                     letter-spacing:1px; color:{color};">{topic}</span>
      </div>
      <h2 style="margin:0 0 12px; font-size:17px; font-weight:700;
                 color:#111827; line-height:1.4; font-family:Georgia,serif;">
        {num} {title}
      </h2>
      <p style="margin:0 0 14px; font-size:14px; color:#374151;
                line-height:1.75;">{body}</p>
      <a href="{url}" style="font-size:12px; color:{color};
                             text-decoration:none; font-weight:600;">
        Leggi su {source} →
      </a>
    </div>
    """


def build_html(stories: list, today: str) -> str:
    stories_html = "".join(render_story(s, i) for i, s in enumerate(stories))
    count_label  = f"{len(stories)} stori{'a' if len(stories)==1 else 'e'} oggi"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0; padding:0; background:#f3f4f6;
             font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
  <div style="max-width:600px; margin:32px auto; background:#ffffff;
              border-radius:14px; box-shadow:0 1px 6px rgba(0,0,0,0.08); overflow:hidden;">

    <div style="background:#111827; padding:28px 32px;">
      <h1 style="margin:0 0 4px; color:#ffffff; font-size:20px;
                 font-weight:700; letter-spacing:-0.3px;">☀️ Daily Digest</h1>
      <p style="margin:0; color:#9ca3af; font-size:12px;">{today} · {count_label}</p>
    </div>

    <div style="padding:28px 32px;">
      {stories_html}
    </div>

    <div style="padding:16px 32px; background:#f9fafb; text-align:center;
                border-top:1px solid #e5e7eb;">
      <p style="margin:0; font-size:11px; color:#9ca3af;">
        Curato da Claude · github.com/albedimaria/news-digest
      </p>
    </div>

  </div>
</body>
</html>"""


# ── Email ──────────────────────────────────────────────────────────────────────

def send_email(html: str, today: str, story_count: int):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"☀️ {story_count} storie per oggi — {today}"
    msg["From"]    = SENDER
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER, SMTP_PASS)
        server.sendmail(SENDER, RECIPIENT, msg.as_string())

    print(f"✓ Sent: {story_count} stories to {RECIPIENT}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    today  = date.today().strftime("%A, %d %B %Y")
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    print("Fetching today's digest…")
    stories = fetch_digest(client)
    print(f"  → {len(stories)} stories selected")

    html = build_html(stories, today)
    send_email(html, today, len(stories))


if __name__ == "__main__":
    main()
