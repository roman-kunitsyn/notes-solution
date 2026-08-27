-- Clients should not need to send their own ownership identifiers.
-- RLS still prevents users from explicitly supplying another user's ID.

alter table public.profiles
alter column id set default auth.uid();

alter table public.notes
alter column user_id set default auth.uid();

alter table public.tags
alter column user_id set default auth.uid();
