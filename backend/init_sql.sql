-- Database initialization script for AI GitHub Explainer
-- This script sets up the initial database schema

-- Create database (if not exists)
-- Note: This is handled by the POSTGRES_DB environment variable in Docker

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types
CREATE TYPE commit_type AS ENUM (
    'feature',
    'bugfix', 
    'security',
    'performance',
    'documentation',
    'refactor',
    'test',
    'style',
    'chore',
    'other'
);

CREATE TYPE post_type AS ENUM (
    'feature_announcement',
    'bug_fix_summary',
    'security_update', 
    'performance_improvement',
    'general_update',
    'release_notes',
    'development_progress'
);

CREATE TYPE post_template AS ENUM (
    'template_feature',
    'template_bugfix',
    'template_security',
    'template_performance',
    'template_general'
);

-- Repositories table
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    description TEXT,
    url VARCHAR(500),
    default_branch VARCHAR(100) DEFAULT 'main',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Commits table
CREATE TABLE commits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sha VARCHAR(40) NOT NULL,
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    author_name VARCHAR(255),
    author_email VARCHAR(255),
    author_username VARCHAR(255),
    committer_name VARCHAR(255),
    committer_email VARCHAR(255),
    committed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    url VARCHAR(500),
    type commit_type DEFAULT 'other',
    additions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    total_changes INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    is_breaking_change BOOLEAN DEFAULT false,
    affects_security BOOLEAN DEFAULT false,
    affects_performance BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(sha, repository_id)
);

-- File changes table
CREATE TABLE file_changes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    commit_id UUID REFERENCES commits(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    status VARCHAR(20), -- added, modified, removed, renamed
    additions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    changes INTEGER DEFAULT 0,
    patch TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Posts table
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    type post_type NOT NULL,
    template post_template NOT NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    detailed_explanation TEXT,
    time_period VARCHAR(10), -- 2h, 24h, etc.
    target_audience VARCHAR(50) DEFAULT 'general',
    html_content TEXT,
    file_path VARCHAR(500),
    commit_count INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    contributors_count INTEGER DEFAULT 0,
    breaking_changes INTEGER DEFAULT 0,
    security_fixes INTEGER DEFAULT 0,
    generation_time_seconds REAL,
    tokens_used INTEGER,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Post commits relationship (many-to-many)
CREATE TABLE post_commits (
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    commit_id UUID REFERENCES commits(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, commit_id)
);

-- Tags table for posts
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Post tags relationship
CREATE TABLE post_tags (
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, tag_id)
);

-- Analytics table for tracking post performance
CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL, -- view, like, share, comment
    user_id VARCHAR(100), -- optional user identifier
    user_agent TEXT,
    ip_address INET,
    referrer VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Collection runs table to track automated collections
CREATE TABLE collection_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    commits_collected INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX idx_commits_repository_id ON commits(repository_id);
CREATE INDEX idx_commits_committed_at ON commits(committed_at);
CREATE INDEX idx_commits_sha ON commits(sha);
CREATE INDEX idx_commits_type ON commits(type);
CREATE INDEX idx_commits_security ON commits(affects_security) WHERE affects_security = true;
CREATE INDEX idx_commits_breaking ON commits(is_breaking_change) WHERE is_breaking_change = true;

CREATE INDEX idx_file_changes_commit_id ON file_changes(commit_id);
CREATE INDEX idx_file_changes_filename ON file_changes(filename);

CREATE INDEX idx_posts_repository_id ON posts(repository_id);
CREATE INDEX idx_posts_created_at ON posts(created_at);
CREATE INDEX idx_posts_type ON posts(type);
CREATE INDEX idx_posts_template ON posts(template);
CREATE INDEX idx_posts_time_period ON posts(time_period);

CREATE INDEX idx_post_commits_post_id ON post_commits(post_id);
CREATE INDEX idx_post_commits_commit_id ON post_commits(commit_id);

CREATE INDEX idx_analytics_events_post_id ON analytics_events(post_id);
CREATE INDEX idx_analytics_events_type ON analytics_events(event_type);
CREATE INDEX idx_analytics_events_created_at ON analytics_events(created_at);

CREATE INDEX idx_collection_runs_repository_id ON collection_runs(repository_id);
CREATE INDEX idx_collection_runs_created_at ON collection_runs(created_at);

-- Create full-text search indexes
CREATE INDEX idx_commits_message_fts ON commits USING gin(to_tsvector('english', message));
CREATE INDEX idx_posts_content_fts ON posts USING gin(to_tsvector('english', title || ' ' || COALESCE(summary, '') || ' ' || COALESCE(detailed_explanation, '')));

-- Create triggers to automatically update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_repositories_updated_at 
    BEFORE UPDATE ON repositories 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_posts_updated_at 
    BEFORE UPDATE ON posts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create views for common queries
CREATE VIEW repository_stats AS
SELECT 
    r.id,
    r.name,
    r.full_name,
    COUNT(DISTINCT c.id) as total_commits,
    COUNT(DISTINCT p.id) as total_posts,
    MAX(c.committed_at) as last_commit_at,
    MAX(p.created_at) as last_post_at,
    SUM(c.additions) as total_additions,
    SUM(c.deletions) as total_deletions,
    COUNT(DISTINCT c.author_email) as unique_contributors
FROM repositories r
LEFT JOIN commits c ON r.id = c.repository_id
LEFT JOIN posts p ON r.id = p.repository_id
WHERE r.is_active = true
GROUP BY r.id, r.name, r.full_name;

CREATE VIEW post_performance AS
SELECT 
    p.id,
    p.title,
    p.type,
    p.template,
    p.repository_id,
    p.created_at,
    p.views,
    p.likes,
    p.shares,
    COALESCE(comment_count.count, 0) as comments,
    (p.views::float / NULLIF(EXTRACT(EPOCH FROM (NOW() - p.created_at))/3600, 0)) as views_per_hour
FROM posts p
LEFT JOIN (
    SELECT post_id, COUNT(*) as count
    FROM analytics_events 
    WHERE event_type = 'comment'
    GROUP BY post_id
) comment_count ON p.id = comment_count.post_id;

-- Insert some initial data
INSERT INTO tags (name) VALUES 
    ('development'),
    ('features'),
    ('bugfix'),
    ('security'),
    ('performance'),
    ('documentation'),
    ('testing'),
    ('refactoring'),
    ('deployment'),
    ('maintenance');

-- Create function to clean up old data
CREATE OR REPLACE FUNCTION cleanup_old_data(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
    cutoff_date TIMESTAMP WITH TIME ZONE;
BEGIN
    cutoff_date := NOW() - INTERVAL '1 day' * days_to_keep;
    
    -- Delete old analytics events (keep for shorter period)
    DELETE FROM analytics_events 
    WHERE created_at < cutoff_date - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RAISE NOTICE 'Deleted % old analytics events', deleted_count;
    
    -- Delete old collection runs
    DELETE FROM collection_runs 
    WHERE created_at < cutoff_date;
    
    -- Optionally delete old commits (be careful with this)
    -- DELETE FROM commits WHERE committed_at < cutoff_date;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO github_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO github_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO github_user;

COMMIT;