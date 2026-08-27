-- Private Storage bucket for note attachments.
--
-- Required object path:
--   <user-id>/<note-id>/<filename>
--
-- Example:
--   81b8.../d921.../requirements.pdf
insert into
  storage.buckets (
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
  )
values
  (
    'note-attachments',
    'note-attachments',
    false,
    10485760, -- 10 MiB
    array[
      'image/png',
      'image/jpeg',
      'application/pdf',
      'text/plain'
    ]::text[]
  ) on conflict (id)
do
update
set
  name = excluded.name,
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Read/download only attachments belonging to one of the user's notes.
create policy "note attachments select own" on storage.objects for
select
  to authenticated using (
    bucket_id = 'note-attachments'
    and coalesce(array_length(storage.foldername (name), 1), 0) = 2
    and (storage.foldername (name)) [1] = (
      select
        auth.uid ()
    )::text
    and exists (
      select
        1
      from
        public.notes
      where
        notes.id::text = (storage.foldername (name)) [2]
        and notes.user_id = (
          select
            auth.uid ()
        )
    )
  );

-- Upload only into the authenticated user's folder and an owned note.
create policy "note attachments insert own" on storage.objects for insert to authenticated
with
  check (
    bucket_id = 'note-attachments'
    and coalesce(array_length(storage.foldername (name), 1), 0) = 2
    and (storage.foldername (name)) [1] = (
      select
        auth.uid ()
    )::text
    and exists (
      select
        1
      from
        public.notes
      where
        notes.id::text = (storage.foldername (name)) [2]
        and notes.user_id = (
          select
            auth.uid ()
        )
    )
  );

-- Required for replacing/upserting an existing attachment.
create policy "note attachments update own" on storage.objects for
update to authenticated using (
  bucket_id = 'note-attachments'
  and coalesce(array_length(storage.foldername (name), 1), 0) = 2
  and (storage.foldername (name)) [1] = (
    select
      auth.uid ()
  )::text
  and exists (
    select
      1
    from
      public.notes
    where
      notes.id::text = (storage.foldername (name)) [2]
      and notes.user_id = (
        select
          auth.uid ()
      )
  )
)
with
  check (
    bucket_id = 'note-attachments'
    and coalesce(array_length(storage.foldername (name), 1), 0) = 2
    and (storage.foldername (name)) [1] = (
      select
        auth.uid ()
    )::text
    and exists (
      select
        1
      from
        public.notes
      where
        notes.id::text = (storage.foldername (name)) [2]
        and notes.user_id = (
          select
            auth.uid ()
        )
    )
  );

-- Delete only attachments belonging to one of the user's notes.
create policy "note attachments delete own" on storage.objects for delete to authenticated using (
  bucket_id = 'note-attachments'
  and coalesce(array_length(storage.foldername (name), 1), 0) = 2
  and (storage.foldername (name)) [1] = (
    select
      auth.uid ()
  )::text
  and exists (
    select
      1
    from
      public.notes
    where
      notes.id::text = (storage.foldername (name)) [2]
      and notes.user_id = (
        select
          auth.uid ()
      )
  )
);
