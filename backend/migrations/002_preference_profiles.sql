-- EXTENSION beyond the SRS (decision D-05): storage for LLM-extracted chat preferences (RF-3.2).
CREATE TABLE user_preference_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
