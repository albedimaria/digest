# Daily Digest

A personalized daily newsletter curated by Gemini 2.5 Flash with native Google Search. Every morning it sends 2-3 hand-picked stories per profile, Breaking Italy style: real news of the day opened into broader analysis.

## How it works

1. GitHub Actions runs the script every day at 07:00 UTC (09:00 Italian time)
2. Gemini searches for today's news on each profile's topics of interest
3. It picks the 2-3 most relevant stories and writes a journalistic piece for each
4. Sends an HTML email to each recipient via Gmail

## Setup

### 1. GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|--------|-------------|
| `GMAIL_APP_PASSWORD` | Gmail app password (not your regular password) |
| `GEMINI_API_KEY` | Google AI Studio API key |

### 2. Generate a Gmail App Password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Create a new app password for "Mail"
3. Paste the generated code into the `GMAIL_APP_PASSWORD` secret

### 3. Get a Gemini API Key

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Create an API key
3. Paste it into the `GEMINI_API_KEY` secret

## Profiles

Profiles live in `profiles.json` (JSON mode) or in the Supabase `profiles` table
(production mode). Each profile has:

```json
{
  "name": "Name",
  "recipient": "email@example.com",
  "active": true,
  "interests": "...",
  "prompt_template": "... (optional, overrides the default)",
  "frequency": "daily",      // "daily" | "weekly"
  "weekly_day": 0,            // 0=Mon ... 6=Sun (only if weekly)
  "num_stories": 3,           // stories (full) or links (links mode); clamp 1-6 / 1-15
  "depth": "standard",       // "brief" | "standard" | "deep"
  "mode": "full"             // "full" (analysis) | "links" (just a list of links to pick from)
}
```

Defaults apply when a field is missing, so old profiles keep working.

## Storage backends

`store.py` picks the backend automatically:

- **JSON mode** (default): profiles from `profiles.json`, history in `history.json`
  (committed back by the workflow). Good for local/dev and the current 2-user setup.
- **Supabase mode**: active when `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are set.
  Profiles, sent-story history and feedback live in Postgres.

### Supabase setup (production)

1. Create a project in the Supabase account (the one with a free project slot).
2. Open **SQL Editor**, paste and run `supabase_schema.sql`.
3. Add two GitHub secrets:
   - `SUPABASE_URL` — e.g. `https://xxxx.supabase.co`
   - `SUPABASE_SERVICE_KEY` — the **service_role** key (Settings → API). Server-side only.
4. Seed the current profiles into the DB (locally, with the two env vars set):
   ```
   python seed_supabase.py
   ```
Once the secrets are present in Actions, the daily run switches to Supabase
automatically (no code change).

## Manual run

From the **Actions** tab on GitHub → **Daily Digest** → **Run workflow**.

## Dependencies

```
google-genai>=0.8.0
```
(Supabase access uses the Python stdlib — no extra dependency.)
