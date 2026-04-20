-- Migration: add wardrobe_items table
-- Run this in the Supabase SQL editor before using the wardrobe feature.

create table if not exists wardrobe_items (
  id          uuid        primary key default gen_random_uuid(),
  user_id     uuid        not null references auth.users(id) on delete cascade,
  image_url   text        not null,
  ownership   text        not null check (ownership in ('owned', 'wishlist')),
  category    text,
  colors      text[]      not null default '{}',
  style_tags  text[]      not null default '{}',
  description text,
  user_notes  text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

alter table wardrobe_items enable row level security;

create policy "Users can select their own wardrobe items"
  on wardrobe_items for select
  using (auth.uid() = user_id);

create policy "Users can insert their own wardrobe items"
  on wardrobe_items for insert
  with check (auth.uid() = user_id);

create policy "Users can update their own wardrobe items"
  on wardrobe_items for update
  using (auth.uid() = user_id);

create policy "Users can delete their own wardrobe items"
  on wardrobe_items for delete
  using (auth.uid() = user_id);

-- Reuse the update_updated_at trigger function (already created by add_user_profiles.sql).
-- If running this migration in isolation, uncomment the block below:
-- create or replace function update_updated_at()
-- returns trigger language plpgsql as $$
-- begin
--   new.updated_at = now();
--   return new;
-- end;
-- $$;

create trigger wardrobe_items_updated_at
  before update on wardrobe_items
  for each row execute function update_updated_at();
