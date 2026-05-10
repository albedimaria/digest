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

Profiles are defined in `digest.py` in the `PROFILES` list. Each profile has:

```python
{
    "name": "Name",
    "recipient": "email@example.com",
    "interests": "...",  # free-text description of the reader's interests
}
```

To add a new recipient, just append an entry to the list.

## Manual run

From the **Actions** tab on GitHub → **Daily Digest** → **Run workflow**.

## Dependencies

```
google-genai>=0.8.0
```
