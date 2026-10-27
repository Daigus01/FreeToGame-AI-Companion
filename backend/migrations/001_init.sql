-- Canonical schema, taken verbatim from SRS section 6 (+ indexes). Requires PostgreSQL 13+ (gen_random_uuid).
-- Applied automatically by docker-compose (mounted in /docker-entrypoint-initdb.d on first DB init).

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE games (
    id INT PRIMARY KEY, -- original FreeToGame id
    title VARCHAR(255) NOT NULL,
    thumbnail TEXT,
    short_description TEXT,
    genre VARCHAR(100),
    platform VARCHAR(50),
    publisher VARCHAR(100),
    developer VARCHAR(100),
    release_date DATE,
    freetogame_profile_url TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_game_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    game_id INT REFERENCES games(id) ON DELETE CASCADE,
    interaction_type VARCHAR(50) NOT NULL, -- 'view', 'click', 'saved', 'played', 'disliked'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    sender VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system', 'tool'
    content TEXT NOT NULL,
    tool_calls JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE daily_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    recommendation_date DATE NOT NULL,
    game_ids INT[] NOT NULL, -- 5 recommended game ids
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, recommendation_date)
);

-- Indexes (not in SRS; needed for the access patterns of the ML job and chat history)
CREATE INDEX idx_interactions_user_created ON user_game_interactions (user_id, created_at DESC);
CREATE INDEX idx_interactions_game ON user_game_interactions (game_id);
CREATE INDEX idx_chat_messages_session_created ON chat_messages (session_id, created_at);
CREATE INDEX idx_chat_sessions_user ON chat_sessions (user_id);
