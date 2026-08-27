-- ============================================================
-- Profiles
-- ============================================================
create table
  public.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    username text not null,
    created_at timestamptz not null default now(),
    constraint profiles_username_not_empty check (length(trim(username)) > 0)
  );

create unique index profiles_username_unique_idx on public.profiles (lower(username));

-- ============================================================
-- Notes
-- ============================================================
create table
  public.notes (
    id uuid primary key default gen_random_uuid (),
    user_id uuid not null references auth.users (id) on delete cascade,
    title text not null,
    content text not null default '',
    is_archived boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint notes_title_not_empty check (length(trim(title)) > 0)
  );

create index notes_user_id_idx on public.notes (user_id);

create index notes_user_created_at_idx on public.notes (user_id, created_at desc);

create index notes_active_idx on public.notes (user_id, updated_at desc)
where
  is_archived = false;

-- ============================================================
-- Tags
-- ============================================================
create table
  public.tags (
    id uuid primary key default gen_random_uuid (),
    user_id uuid not null references auth.users (id) on delete cascade,
    name text not null,
    created_at timestamptz not null default now(),
    constraint tags_name_not_empty check (length(trim(name)) > 0)
  );

create index tags_user_id_idx on public.tags (user_id);

create unique index tags_user_name_unique_idx on public.tags (user_id, lower(name));

-- ============================================================
-- Note/tag relationship
-- ============================================================
create table
  public.note_tags (
    note_id uuid not null references public.notes (id) on delete cascade,
    tag_id uuid not null references public.tags (id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (note_id, tag_id)
  );

create index note_tags_tag_id_idx on public.note_tags (tag_id);

-- ============================================================
-- Automatically update notes.updated_at
-- ============================================================
create function public.set_updated_at () returns trigger language plpgsql
set
  search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger notes_set_updated_at before
update on public.notes for each row
execute function public.set_updated_at ();

-- ============================================================
-- Data API permissions
--
-- GRANT makes tables available to the API roles.
-- RLS below determines which rows each user may access.
-- ============================================================
grant usage on schema public to anon,
authenticated;

grant
select
,
  insert,
update,
delete on public.profiles,
public.notes,
public.tags,
public.note_tags to authenticated;

-- ============================================================
-- Enable Row Level Security
-- ============================================================
alter table public.profiles enable row level security;

alter table public.notes enable row level security;

alter table public.tags enable row level security;

alter table public.note_tags enable row level security;

-- ============================================================
-- Profiles policies
-- ============================================================
create policy "users can read their own profile" on public.profiles for
select
  to authenticated using (
    (
      select
        auth.uid ()
    ) = id
  );

create policy "users can create their own profile" on public.profiles for insert to authenticated
with
  check (
    (
      select
        auth.uid ()
    ) = id
  );

create policy "users can update their own profile" on public.profiles for
update to authenticated using (
  (
    select
      auth.uid ()
  ) = id
)
with
  check (
    (
      select
        auth.uid ()
    ) = id
  );

create policy "users can delete their own profile" on public.profiles for delete to authenticated using (
  (
    select
      auth.uid ()
  ) = id
);

-- ============================================================
-- Notes policies
-- ============================================================
create policy "users can read their own notes" on public.notes for
select
  to authenticated using (
    (
      select
        auth.uid ()
    ) = user_id
  );

create policy "users can create their own notes" on public.notes for insert to authenticated
with
  check (
    (
      select
        auth.uid ()
    ) = user_id
  );

create policy "users can update their own notes" on public.notes for
update to authenticated using (
  (
    select
      auth.uid ()
  ) = user_id
)
with
  check (
    (
      select
        auth.uid ()
    ) = user_id
  );

create policy "users can delete their own notes" on public.notes for delete to authenticated using (
  (
    select
      auth.uid ()
  ) = user_id
);

-- ============================================================
-- Tags policies
-- ============================================================
create policy "users can read their own tags" on public.tags for
select
  to authenticated using (
    (
      select
        auth.uid ()
    ) = user_id
  );

create policy "users can create their own tags" on public.tags for insert to authenticated
with
  check (
    (
      select
        auth.uid ()
    ) = user_id
  );

create policy "users can update their own tags" on public.tags for
update to authenticated using (
  (
    select
      auth.uid ()
  ) = user_id
)
with
  check (
    (
      select
        auth.uid ()
    ) = user_id
  );

create policy "users can delete their own tags" on public.tags for delete to authenticated using (
  (
    select
      auth.uid ()
  ) = user_id
);

-- ============================================================
-- Note-tag policies
--
-- A relationship is accessible only when both the note and
-- the tag belong to the authenticated user.
-- ============================================================
create policy "users can read their own note tags" on public.note_tags for
select
  to authenticated using (
    exists (
      select
        1
      from
        public.notes
      where
        notes.id = note_tags.note_id
        and notes.user_id = (
          select
            auth.uid ()
        )
    )
    and exists (
      select
        1
      from
        public.tags
      where
        tags.id = note_tags.tag_id
        and tags.user_id = (
          select
            auth.uid ()
        )
    )
  );

create policy "users can create their own note tags" on public.note_tags for insert to authenticated
with
  check (
    exists (
      select
        1
      from
        public.notes
      where
        notes.id = note_tags.note_id
        and notes.user_id = (
          select
            auth.uid ()
        )
    )
    and exists (
      select
        1
      from
        public.tags
      where
        tags.id = note_tags.tag_id
        and tags.user_id = (
          select
            auth.uid ()
        )
    )
  );

create policy "users can delete their own note tags" on public.note_tags for delete to authenticated using (
  exists (
    select
      1
    from
      public.notes
    where
      notes.id = note_tags.note_id
      and notes.user_id = (
        select
          auth.uid ()
      )
  )
  and exists (
    select
      1
    from
      public.tags
    where
      tags.id = note_tags.tag_id
      and tags.user_id = (
        select
          auth.uid ()
      )
  )
);
