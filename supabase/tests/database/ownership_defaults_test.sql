begin;

select plan(5);

-- Create a temporary Auth user before switching to the authenticated role.

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
values (
  '00000000-0000-0000-0000-000000000000',
  '50000000-0000-0000-0000-000000000005',
  'authenticated',
  'authenticated',
  'ownership-test@example.test',
  now(),
  '{"provider":"email","providers":["email"]}'::jsonb,
  '{}'::jsonb,
  now(),
  now()
);

set local role authenticated;

select set_config(
  'request.jwt.claims',
  '{
    "sub": "50000000-0000-0000-0000-000000000005",
    "role": "authenticated"
  }',
  true
);


-- 1. Profile ID defaults to auth.uid().

select results_eq(
  $$
    insert into public.profiles (username)
    values ('ownership-test-user')
    returning id
  $$,
  $$
    values ('50000000-0000-0000-0000-000000000005'::uuid)
  $$,
  'profile ID defaults to auth.uid()'
);


-- 2. Note owner defaults to auth.uid().

select results_eq(
  $$
    insert into public.notes (title, content)
    values ('Default owner note', 'No user_id was supplied')
    returning user_id
  $$,
  $$
    values ('50000000-0000-0000-0000-000000000005'::uuid)
  $$,
  'note user_id defaults to auth.uid()'
);


-- 3. Tag owner defaults to auth.uid().

select results_eq(
  $$
    insert into public.tags (name)
    values ('automatic-owner')
    returning user_id
  $$,
  $$
    values ('50000000-0000-0000-0000-000000000005'::uuid)
  $$,
  'tag user_id defaults to auth.uid()'
);


-- 4. Explicitly assigning Alice as note owner remains forbidden.

select throws_ok(
  $$
    insert into public.notes (user_id, title)
    values (
      '20000000-0000-0000-0000-000000000002',
      'Forbidden Alice note'
    )
  $$,
  '42501',
  'new row violates row-level security policy for table "notes"',
  'user cannot override note ownership'
);


-- 5. Explicitly assigning Alice as tag owner remains forbidden.

select throws_ok(
  $$
    insert into public.tags (user_id, name)
    values (
      '20000000-0000-0000-0000-000000000002',
      'forbidden-tag'
    )
  $$,
  '42501',
  'new row violates row-level security policy for table "tags"',
  'user cannot override tag ownership'
);

select * from finish();

rollback;
