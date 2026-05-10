# Daily Digest

Newsletter quotidiana personalizzata, curata da Gemini 2.5 Flash con Google Search nativo. Invia ogni mattina 2-3 storie selezionate per ogni profilo, stile Breaking Italy: notizie reali del giorno aperte in analisi più ampie.

## Come funziona

1. GitHub Actions esegue lo script ogni giorno alle 07:00 UTC (09:00 ora italiana)
2. Gemini cerca notizie del giorno sui temi di interesse di ogni profilo
3. Sceglie le 2-3 storie più rilevanti e scrive un pezzo giornalistico per ciascuna
4. Invia una email HTML a ogni destinatario via Gmail

## Setup

### 1. Secrets GitHub

Vai su **Settings → Secrets and variables → Actions** e aggiungi:

| Secret | Descrizione |
|--------|-------------|
| `GMAIL_APP_PASSWORD` | App password Gmail (non la password normale) |
| `GEMINI_API_KEY` | API key Google AI Studio |

### 2. Generare la Gmail App Password

1. Vai su [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Crea una nuova app password per "Mail"
3. Incolla il codice generato nel secret `GMAIL_APP_PASSWORD`

### 3. Ottenere la Gemini API Key

1. Vai su [aistudio.google.com](https://aistudio.google.com)
2. Crea una API key
3. Incollala nel secret `GEMINI_API_KEY`

## Profili

I profili sono definiti in `digest.py` nella lista `PROFILES`. Ogni profilo ha:

```python
{
    "name": "Nome",
    "recipient": "email@esempio.com",
    "interests": "...",  # stringa con gli interessi del lettore
}
```

Per aggiungere un nuovo destinatario basta aggiungere un elemento alla lista.

## Run manuale

Dalla tab **Actions** su GitHub → **Daily Digest** → **Run workflow**.

## Dipendenze

```
google-genai>=0.8.0
```
