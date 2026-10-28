-- P1-04 / D-11: OAuth login (Google, Discord). EXTENSION beyond the SRS (which defines no auth).
-- NOTE: docker only runs migrations on FIRST database init. On an existing DB apply this file by hand
-- (see docs/OAUTH_SETUP.md).
ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;

CREATE TABLE IF NOT EXISTS user_identities (
    provider VARCHAR(20) NOT NULL,            -- 'google' | 'discord'
    provider_user_id VARCHAR(255) NOT NULL,   -- Google `sub` / Discord user id
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provider, provider_user_id)
);
CREATE INDEX IF NOT EXISTS idx_user_identities_user ON user_identities (user_id);
