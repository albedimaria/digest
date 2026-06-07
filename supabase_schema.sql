-- ── Schema digest ───────────────────────────────────────────────────────────
-- Da eseguire una volta nel SQL Editor del progetto Supabase (account outlook).
-- Accesso solo server-side con la service key (RLS attiva, nessuna policy pubblica).

create table if not exists profiles (
  id              bigint generated always as identity primary key,
  name            text    not null,
  recipient       text    not null unique,
  active          boolean not null default true,
  interests       text    not null default '',
  prompt_template text,                       -- null → usa il template di default nel codice
  satisfaction    int,                        -- ultimo voto 1-5
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create table if not exists sent_stories (
  id          bigint generated always as identity primary key,
  profile_id  bigint not null references profiles(id) on delete cascade,
  sent_date   date   not null default current_date,
  title       text,
  url         text,
  topic       text,
  created_at  timestamptz not null default now()
);
create index if not exists sent_stories_profile_date_idx
  on sent_stories (profile_id, sent_date desc);

create table if not exists feedback (
  id          bigint generated always as identity primary key,
  profile_id  bigint not null references profiles(id) on delete cascade,
  rating      int,                            -- 1-5
  note        text,                           -- testo libero del lettore
  processed   boolean not null default false, -- true quando è già stato applicato al prompt
  created_at  timestamptz not null default now()
);
create index if not exists feedback_unprocessed_idx
  on feedback (profile_id) where not processed;

-- RLS: blocca tutto agli anon/authenticated; la service key bypassa RLS.
alter table profiles     enable row level security;
alter table sent_stories enable row level security;
alter table feedback     enable row level security;
