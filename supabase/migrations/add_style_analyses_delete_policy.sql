-- Run this in the Supabase dashboard SQL editor (or via supabase db push).
-- Allows authenticated users to delete only their own style_analyses rows.
create policy "Users can delete own analyses"
  on style_analyses
  for delete
  using (auth.uid() = user_id);
