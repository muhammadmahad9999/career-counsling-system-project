-- =============================================================================
-- FuturePath — Supabase Database Schema
-- Run this in: Supabase Dashboard → SQL Editor → New Query → Paste → Run
-- =============================================================================

-- STUDENTS TABLE — extends Supabase auth.users
create table if not exists public.students (
  id uuid references auth.users(id) on delete cascade primary key,
  full_name text,
  phone text,
  city text,
  fsc_stream text check (fsc_stream in (
    'Pre-Medical', 'Pre-Engineering', 'ICS', 'FA', 'Commerce', 'Other'
  )),
  fsc_percentage float,
  matric_percentage float,
  target_career text,
  target_university text,
  entry_test_planned text,
  preferred_language text default 'en' check (preferred_language in ('en', 'ur')),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- CONVERSATIONS TABLE — one per chat session
create table if not exists public.conversations (
  id uuid default gen_random_uuid() primary key,
  student_id uuid references public.students(id) on delete cascade,
  title text,
  is_active boolean default true,
  created_at timestamptz default now(),
  last_message_at timestamptz default now()
);

-- MESSAGES TABLE — every single message
create table if not exists public.messages (
  id uuid default gen_random_uuid() primary key,
  conversation_id uuid references public.conversations(id) on delete cascade,
  student_id uuid references public.students(id) on delete cascade,
  role text check (role in ('user', 'assistant')),
  content text not null,
  language text default 'en',
  is_voice boolean default false,
  audio_url text,
  search_used boolean default false,
  created_at timestamptz default now()
);

-- SAVED RESOURCES TABLE — bookmarked links
create table if not exists public.saved_resources (
  id uuid default gen_random_uuid() primary key,
  student_id uuid references public.students(id) on delete cascade,
  title text not null,
  url text not null,
  resource_type text check (resource_type in (
    'youtube', 'scholarship', 'course', 'university', 'article', 'other'
  )),
  notes text,
  is_bookmarked boolean default true,
  created_at timestamptz default now()
);

-- ENTRY TEST SCORES TABLE
create table if not exists public.entry_test_scores (
  id uuid default gen_random_uuid() primary key,
  student_id uuid references public.students(id) on delete cascade,
  test_type text,
  score float,
  total float,
  subject text,
  weak_topics text[],
  taken_at timestamptz default now()
);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS) — students can only access their own data
-- =============================================================================

alter table public.students enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.saved_resources enable row level security;
alter table public.entry_test_scores enable row level security;

create policy "student can manage own profile"
  on public.students for all using (auth.uid() = id);

create policy "student can manage own conversations"
  on public.conversations for all using (auth.uid() = student_id);

create policy "student can manage own messages"
  on public.messages for all using (auth.uid() = student_id);

create policy "student can manage own resources"
  on public.saved_resources for all using (auth.uid() = student_id);

create policy "student can manage own scores"
  on public.entry_test_scores for all using (auth.uid() = student_id);

-- =============================================================================
-- AUTO-CREATE student profile when user signs up
-- =============================================================================

create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.students (id, full_name)
  values (new.id, new.raw_user_meta_data->>'full_name');
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
