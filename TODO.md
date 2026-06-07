# TODO — daily digest

Roadmap degli interventi rimandati. Ordine indicativo per priorità.

## Qualità notizie (quando serve / col carico utenti)
- [ ] **Switch provider / profondità reale** — Gemini 2.5 Flash free tier è il collo
      di bottiglia sull'approfondimento (depth='deep' spinge il prompt ma il modello
      ha un tetto). Per una qualità Breaking Italy vera serve Gemini Pro / Claude / GPT.
      Predisporre un campo profilo 'model' / tier premium quando ci sono utenti paganti.
      NB: il fallback Perplexity è stato rimosso (non era free).
- [ ] **Modalità links — heading/UX dedicata** — funziona ma è grezza; rifinire la
      resa quando arriva la web app.
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
- [x] **Profili in formato dati** — fatto: profiles.json, poi store.py dual-mode.
- [~] **Supabase come data layer** — schema + store.py pronti. DA FARE dall'utente:
      creare progetto (account outlook, slot libero), eseguire supabase_schema.sql,
      impostare i secret SUPABASE_URL + SUPABASE_SERVICE_KEY, lanciare seed_supabase.py.
      Vedi README sezione "Supabase".
- [ ] **Feedback loop (email-reply)** — IN COSTRUZIONE. Schema feedback già pronto.
      Prossimo step: footer con voto 1-5 nell'email + script che legge le risposte
      via IMAP Gmail e un LLM traduce il testo libero in modifiche al prompt.
      È il vero differenziatore vs Mailbrew.
- [ ] **Onboarding** — form web (nome, email, interessi in linguaggio naturale).
- [ ] **Pagamenti** — Stripe, ipotesi 3€/mese.
- [ ] **Delivery alternativa** — Telegram (semplice, target tech) come opzione;
      WhatsApp solo se molto richiesto (costoso/complesso).
- [ ] **Privacy** — il repo è PUBLIC. Con Supabase i dati utente escono dal git
      (bene), ma valutare comunque repo privato prima della produzione.

## Fatto
- [x] Separazione config / codice (config.py)
- [x] Sezione "NB — anche oggi" con menzioni rapide
- [x] Prompt per-profilo
- [x] Regola anti-allucinazione URL
- [x] Fix exit-code per far emergere i fallimenti in CI
- [x] Date in italiano, parsing JSON robusto, fix secret CI
- [x] Memoria anti-ripetizione (history.json, finestra 7 giorni)
