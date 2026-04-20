-- Run this in the Supabase dashboard SQL editor (or via supabase db push).
-- Creates the recommendation_cache table and its RLS policies.

create table recommendation_cache (
  id              uuid primary key default gen_random_uuid(),
  analysis_id     uuid not null unique references style_analyses(id) on delete cascade,
  user_id         uuid not null references auth.users(id) on delete cascade,
  recommendations jsonb not null,
  created_at      timestamptz not null default now()
);

alter table recommendation_cache enable row level security;

create policy "Users can select own recommendation cache"
  on recommendation_cache for select
  using (auth.uid() = user_id);

create policy "Users can insert own recommendation cache"
  on recommendation_cache for insert
  with check (auth.uid() = user_id);

create policy "Users can delete own recommendation cache"
  on recommendation_cache for delete
  using (auth.uid() = user_id);
