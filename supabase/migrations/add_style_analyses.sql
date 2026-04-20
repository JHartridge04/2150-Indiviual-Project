-- Migration: add style_analyses table
-- Stores the result of every AI-powered outfit analysis for a user.

CREATE TABLE IF NOT EXISTS style_analyses (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    image_url   text,
    colors      text[],
    silhouettes text[],
    style_tags  text[],
    summary     text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Enable Row Level Security so users can only access their own rows.
ALTER TABLE style_analyses ENABLE ROW LEVEL SECURITY;

-- SELECT policy: authenticated users may read only their own analyses.
CREATE POLICY "Users can view their own analyses"
    ON style_analyses
    FOR SELECT
    USING (auth.uid() = user_id);

-- INSERT policy: authenticated users may insert rows only for themselves.
CREATE POLICY "Users can insert their own analyses"
    ON style_analyses
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);
