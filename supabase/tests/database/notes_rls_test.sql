begin;

select plan(8);

-- Act as Roman through the same JWT claims used by Supabase Auth.
set local role authenticated;

select set_config(
  'request.jwt.claims',
  '{
    "sub": "10000000-0000-0000-0000-000000000001",
    "role": "authenticated"
  }',
  true
);


-- 1. auth.uid() extracts Roman's ID from the simulated JWT.

select is(
  auth.uid(),
  '10000000-0000-0000-0000-000000000001'::uuid,
  'Roman is the authenticated user'
);


-- 2. Roman sees exactly his two initial notes.

select results_eq(
  $$
    select count(*)
    from public.notes
  $$,
  $$
    values (2::bigint)
  $$,
  'Roman sees exactly two notes'
);


-- 3. Alice's note is invisible to Roman.

select results_eq(
  $$
    select count(*)
    from public.notes
    where id = '30000000-0000-0000-0000-000000000003'
  $$,
  $$
    values (0::bigint)
  $$,
  'Roman cannot read Alice note'
);


-- 4. Roman can create a note owned by Roman.

select lives_ok(
  $$
    insert into public.notes (user_id, title, content)
    values (
      '10000000-0000-0000-0000-000000000001',
      'RLS test note',
      'Created during the pgTAP test'
    )
  $$,
  'Roman can create his own note'
);


-- 5. Roman cannot create a note owned by Alice.

select throws_ok(
  $$
    insert into public.notes (user_id, title)
    values (
      '20000000-0000-0000-0000-000000000002',
      'Forbidden note'
    )
  $$,
  '42501',
  'new row violates row-level security policy for table "notes"',
  'Roman cannot create a note for Alice'
);


-- 6. Roman can update his own note.

select lives_ok(
  $$
    update public.notes
    set title = 'Learn Supabase properly'
    where id = '30000000-0000-0000-0000-000000000001'
  $$,
  'Roman can update his own note'
);


-- 7. Updating Alice's note affects no rows because it is invisible.

select results_eq(
  $$
    update public.notes
    set title = 'Roman was here'
    where id = '30000000-0000-0000-0000-000000000003'
    returning id
  $$,
  $$
    select id
    from public.notes
    where false
  $$,
  'Roman cannot update Alice note'
);


-- 8. Roman cannot transfer his note to Alice.

select throws_ok(
  $$
    update public.notes
    set user_id = '20000000-0000-0000-0000-000000000002'
    where id = '30000000-0000-0000-0000-000000000001'
  $$,
  '42501',
  'new row violates row-level security policy for table "notes"',
  'Roman cannot transfer ownership to Alice'
);

select * from finish();

rollback;
