-- Run this in the Supabase dashboard SQL editor (or via supabase db push).

create table user_profiles (
  user_id           uuid primary key references auth.users(id) on delete cascade,
  gender            text,
  age_range         text,
  body_type         text,
  height_cm         integer,
  weight_kg         integer,
  preferred_styles  text[]      not null default '{}',
  favorite_brands   text[]      not null default '{}',
  occasions         text[]      not null default '{}',
  shirt_size        text,
  pants_size        text,
  shoe_size         text,
  budget_min_usd    integer,
  budget_max_usd    integer,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

alter table user_profiles enable row level security;

create policy "Users can select own profile"
  on user_profiles for select
  using (auth.uid() = user_id);

create policy "Users can insert own profile"
  on user_profiles for insert
  with check (auth.uid() = user_id);

create policy "Users can update own profile"
  on user_profiles for update
  using (auth.uid() = user_id);

-- Keep updated_at current on every UPDATE
create or replace function update_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger user_profiles_updated_at
  before update on user_profiles
  for each row execute function update_updated_at();
