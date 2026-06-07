# TODO — daily digest

Roadmap degli interventi rimandati. Ordine indicativo per priorità.

## Qualità notizie (quando serve / col carico utenti)
- [ ] **Switch provider** — Gemini 2.5 Flash free tier è il collo di bottiglia su
      qualità e quota. Valutare Claude o GPT con web search quando ci sono utenti
      paganti che ripagano l'API. Tenere il codice già astratto (vedi sotto).
- [ ] **Pre-fetch fonti reali** — invece di affidarsi solo alla ricerca del modello,
      tirare giù candidati VERI da fonti gratuite (Hacker News API, GitHub Trending,
      arXiv API, RSS) e passarli al modello. Risolve URL inventati e storie generiche
      alla radice. La parte free (RSS/API pubbliche) è fattibile senza costi; Apify
      solo se serve scraping più complesso.

## Affidabilità
- [ ] **Scheduler dedicato** — GitHub Actions cron è gratis ma può ritardare/saltare
      sotto carico. Se diventa prodotto, spostare su Render/Railway cron o mini VPS
      (~5€/mese). Per ora GH Actions è sufficiente e abbastanza puntuale.
- [x] Notifica di fallimento — coperta: con `sys.exit(1)` GitHub manda email
      automatica al owner quando un run fallisce.

## Architettura prodotto (basi predisposte, full-build rimandato)
- [ ] **Astrazione provider** — un'unica interfaccia `fetch(profile, today, recent)`
      così cambiare modello è una riga. (parzialmente già così con fetch_digest)
- [ ] **Profili in formato dati** — spostare PROFILES da config.py a JSON/SQLite
      quando gli utenti crescono.
- [ ] **Onboarding** — form web (nome, email, interessi in linguaggio naturale).
- [ ] **Pagamenti** — Stripe, ipotesi 3€/mese.
- [ ] **Feedback loop mensile** — email "cosa cambieresti?", la risposta in
      linguaggio naturale aggiorna il prompt del profilo. È il vero differenziatore
      vs Mailbrew.
- [ ] **Delivery alternativa** — Telegram (semplice, target tech) come opzione;
      WhatsApp solo se molto richiesto (costoso/complesso).

## Fatto
- [x] Separazione config / codice (config.py)
- [x] Sezione "NB — anche oggi" con menzioni rapide
- [x] Prompt per-profilo
- [x] Regola anti-allucinazione URL
- [x] Fix exit-code per far emergere i fallimenti in CI
- [x] Date in italiano, parsing JSON robusto, fix secret CI
- [x] Memoria anti-ripetizione (history.json, finestra 7 giorni)
