-- ============================================================
-- Development users
--
-- Fixed UUIDs make tests and local development deterministic.
-- These records are local fixtures, not production users.
-- ============================================================

insert into auth.users (
  instance_id,
  id,
  aud,
  role,
  email,
  email_confirmed_at,
  raw_app_meta_data,
  raw_user_meta_data,
  created_at,
  updated_at
)
values
  (
    '00000000-0000-0000-0000-000000000000',
    '10000000-0000-0000-0000-000000000001',
    'authenticated',
    'authenticated',
    'roman@example.test',
    now(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    '{}'::jsonb,
    now(),
    now()
  ),
  (
    '00000000-0000-0000-0000-000000000000',
    '20000000-0000-0000-0000-000000000002',
    'authenticated',
    'authenticated',
    'alice@example.test',
    now(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    '{}'::jsonb,
    now(),
    now()
  );


-- ============================================================
-- Profiles
-- ============================================================

insert into public.profiles (id, username)
values
  (
    '10000000-0000-0000-0000-000000000001',
    'roman'
  ),
  (
    '20000000-0000-0000-0000-000000000002',
    'alice'
  );


-- ============================================================
-- Notes
-- ============================================================

insert into public.notes (
  id,
  user_id,
  title,
  content
)
values
  (
    '30000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    'Learn Supabase',
    'Understand migrations, seed data and RLS.'
  ),
  (
    '30000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000001',
    'Deploy Supabase',
    'Run the project on a self-hosted server.'
  ),
  (
    '30000000-0000-0000-0000-000000000003',
    '20000000-0000-0000-0000-000000000002',
    'Alice private note',
    'Roman must never be able to read this.'
  );


-- ============================================================
-- Tags
-- ============================================================

insert into public.tags (
  id,
  user_id,
  name
)
values
  (
    '40000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    'learning'
  ),
  (
    '40000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000001',
    'devops'
  ),
  (
    '40000000-0000-0000-0000-000000000003',
    '20000000-0000-0000-0000-000000000002',
    'private'
  );


-- ============================================================
-- Note/tag relationships
-- ============================================================

insert into public.note_tags (note_id, tag_id)
values
  (
    '30000000-0000-0000-0000-000000000001',
    '40000000-0000-0000-0000-000000000001'
  ),
  (
    '30000000-0000-0000-0000-000000000002',
    '40000000-0000-0000-0000-000000000002'
  ),
  (
    '30000000-0000-0000-0000-000000000003',
    '40000000-0000-0000-0000-000000000003'
  );
