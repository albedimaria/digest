"""
daily-digest — 2-3 storie curate, stile Breaking Italy.
RSS feeds → Gemini 2.0 Flash (free tier, no grounding).
"""

import os, smtplib, json, feedparser
from datetime import date, datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Config ────────────────────────────────────────────────────────────────────

RECIPIENT      = "ing.albertodimaria@gmail.com"
SENDER         = "ing.albertodimaria@gmail.com"
SMTP_PASS      = os.environ["GMAIL_APP_PASSWORD"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

FEEDS = {
    "AI & Developer Tools": [
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
    ],
    "Audio AI & Music Tech": [
        "https://export.arxiv.org/rss/cs.SD",
        "https://www.musictech.net/feed/",
    ],
    "Colombia": [
        "https://colombiareports.com/feed/",
        "https://www.elespectador.com/arc/outboundfeeds/rss/?outputType=xml",
    ],
    "Letteratura": [
        "https://www.theguardian.com/books/rss",
    ],
    "Design & UX": [
        "https://www.smashingmagazine.com/feed/",
        "https://uxdesign.cc/feed",
    ],
    "Jazz & Musica": [
        "https://pitchfork.com/rss/news/",
        "https://www.allaboutjazz.com/rss/news.rss",
    ],
    "Scienza & Filosofia": [
        "https://www.quantamagazine.org/feed/",
    ],
}

# ── RSS fetch ─────────────────────────────────────────────────────────────────

def fetch_articles(hours: int = 48) -> list[dict]:
    cutoff   = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles = []

    for topic, urls in FEEDS.items():
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:8]:
                    pub = entry.get("published_parsed") or entry.get("updated_parsed")
                    if pub:
                        pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                        if pub_dt < cutoff:
                            continue
                    summary = entry.get("summary", "")
                    # strip HTML tags crudely
                    import re
                    summary = re.sub(r"<[^>]+>", "", summary)[:300]
                    articles.append({
                        "topic":   topic,
                        "title":   entry.get("title", "").strip(),
                        "summary": summary.strip(),
                        "url":     entry.get("link", ""),
                        "source":  feed.feed.get("title", url),
                    })
            except Exception as e:
                print(f"  Feed error ({url}): {e}")

    print(f"  → {len(articles)} articles from RSS")
    return articles


def format_articles_for_prompt(articles: list[dict]) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(
            f"[{i}] ({a['topic']}) {a['title']}\n"
            f"    Source: {a['source']} | URL: {a['url']}\n"
            f"    {a['summary']}"
        )
    return "\n\n".join(lines)


# ── Gemini ────────────────────────────────────────────────────────────────────

def fetch_digest(articles: list[dict], today: str) -> list:
    from google import genai
    from google.genai import types

    articles_text = format_articles_for_prompt(articles)

    prompt = f"""Sei un editor che cura una newsletter quotidiana personalizzata da leggere in 5 minuti.

Oggi è {today}.

Di seguito trovi gli articoli raccolti dai feed RSS nelle ultime 48 ore:

{articles_text}

Il tuo compito:
1. Scegli le 2-3 storie più interessanti e rilevanti per il lettore.
   - Privilegia qualità sulla varietà: se ci sono due notizie forti sullo stesso tema, prendile entrambe.
   - Se un tema non ha niente di interessante, ignoralo.
2. Per ogni storia selezionata scrivi un pezzo stile Breaking Italy:
   - Titolo diretto e informativo
   - 4-6 frasi con contesto, perché importa, cosa succede dopo
   - Testo fluente e giornalistico, niente elenchi puntati
   - Usa il topic esatto dall'articolo scelto

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

    client   = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3),
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw).get("stories", [])


# ── HTML ───────────────────────────────────────────────────────────────────────

TOPIC_COLORS = {
    "ai": "#7c3aed", "audio": "#0e7490", "colombia": "#dc2626",
    "letteratura": "#059669", "literatura": "#059669", "design": "#d97706",
    "jazz": "#be185d", "musica": "#be185d", "brujería": "#b45309",
    "brujeria": "#b45309", "scienza": "#6b7280", "filosofia": "#6b7280",
}

def topic_color(topic: str) -> str:
    t = topic.lower()
    for key, color in TOPIC_COLORS.items():
        if key in t:
            return color
    return "#374151"

def render_story(story: dict, index: int) -> str:
    color = topic_color(story.get("topic", ""))
    num   = ["①", "②", "③"][index] if index < 3 else f"{index+1}."
    return f"""
    <div style="margin-bottom:28px; padding:22px; background:#f9fafb;
                border-radius:10px; border-left:4px solid {color};">
      <div style="margin-bottom:8px;">
        <span style="font-size:10px; font-weight:700; text-transform:uppercase;
                     letter-spacing:1px; color:{color};">{story.get('topic','')}</span>
      </div>
      <h2 style="margin:0 0 12px; font-size:17px; font-weight:700;
                 color:#111827; line-height:1.4; font-family:Georgia,serif;">
        {num} {story.get('title','')}
      </h2>
      <p style="margin:0 0 14px; font-size:14px; color:#374151; line-height:1.75;">
        {story.get('body','')}
      </p>
      <a href="{story.get('url','#')}" style="font-size:12px; color:{color};
                                              text-decoration:none; font-weight:600;">
        Leggi su {story.get('source','')} →
      </a>
    </div>"""

def build_html(stories: list, today: str) -> str:
    stories_html = "".join(render_story(s, i) for i, s in enumerate(stories))
    count_label  = f"{len(stories)} stori{'a' if len(stories)==1 else 'e'} oggi"
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:600px;margin:32px auto;background:#fff;
              border-radius:14px;box-shadow:0 1px 6px rgba(0,0,0,0.08);overflow:hidden;">
    <div style="background:#111827;padding:28px 32px;">
      <h1 style="margin:0 0 4px;color:#fff;font-size:20px;font-weight:700;">☀️ Daily Digest</h1>
      <p style="margin:0;color:#9ca3af;font-size:12px;">{today} · {count_label}</p>
    </div>
    <div style="padding:28px 32px;">{stories_html}</div>
    <div style="padding:16px 32px;background:#f9fafb;text-align:center;border-top:1px solid #e5e7eb;">
      <p style="margin:0;font-size:11px;color:#9ca3af;">
        Curato da Gemini · github.com/albedimaria/digest
      </p>
    </div>
  </div>
</body></html>"""


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
    today    = date.today().strftime("%A, %d %B %Y")
    articles = fetch_articles(hours=48)
    if not articles:
        print("No articles found, aborting.")
        return
    print("Asking Gemini to pick the best stories…")
    stories = fetch_digest(articles, today)
    print(f"  → {len(stories)} stories selected")
    html = build_html(stories, today)
    send_email(html, today, len(stories))

if __name__ == "__main__":
    main()
