"""
Supabase Database Schema Initialization

Run this script to generate the SQL for creating all required tables.
Copy the output and paste into Supabase SQL Editor.
"""

def generate_schema_sql():
    """Generate complete database schema SQL"""
    
    sql = """
-- 416Homes Database Schema
-- Run this in Supabase SQL Editor

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Listings table with vector embeddings
CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,
    address TEXT NOT NULL,
    price INTEGER NOT NULL,
    bedrooms TEXT,
    bathrooms TEXT,
    area TEXT,
    city TEXT,
    lat DECIMAL(10, 8),
    lng DECIMAL(11, 8),
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    photo TEXT,
    scraped_at TIMESTAMP WITH TIME ZONE NOT NULL,
    strategy TEXT DEFAULT 'unknown',
    searchable_text TEXT,
    embedding vector(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Migration: add photo column if not present (safe to run multiple times)
ALTER TABLE listings ADD COLUMN IF NOT EXISTS photo TEXT;

-- Sold comparable properties
CREATE TABLE IF NOT EXISTS sold_comps (
    id TEXT PRIMARY KEY,
    address TEXT NOT NULL,
    price INTEGER NOT NULL,
    bedrooms TEXT,
    bathrooms TEXT,
    area TEXT,
    neighbourhood TEXT,
    sold_date TIMESTAMP WITH TIME ZONE,
    lat DECIMAL(10, 8),
    lng DECIMAL(11, 8),
    source TEXT NOT NULL,
    scraped_at TIMESTAMP WITH TIME ZONE NOT NULL,
    strategy TEXT DEFAULT 'unknown',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Video jobs table
CREATE TABLE IF NOT EXISTS video_jobs (
    id TEXT PRIMARY KEY,
    listing_url TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    customer_name TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'generating_script', 'script_generated', 'generating_audio', 'audio_generated', 'generating_video', 'complete', 'completed', 'failed', 'revision_requested')),
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    error_message TEXT,
    video_url TEXT,
    script_data JSONB,
    audio_url TEXT,
    final_video_path TEXT,
    listing_data JSONB DEFAULT '{}',
    revision_count INTEGER DEFAULT 0,
    revision_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add listing_data column if upgrading an existing database
ALTER TABLE video_jobs ADD COLUMN IF NOT EXISTS listing_data JSONB DEFAULT '{}';

-- Buyer alerts table
CREATE TABLE IF NOT EXISTS buyer_alerts (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT,
    neighbourhoods TEXT[] DEFAULT '{}',
    min_price INTEGER,
    max_price INTEGER,
    min_bedrooms INTEGER,
    min_bathrooms INTEGER,
    property_types TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent matches table
CREATE TABLE IF NOT EXISTS agent_matches (
    id TEXT PRIMARY KEY,
    listing_id TEXT REFERENCES listings(id),
    alert_id TEXT REFERENCES buyer_alerts(id),
    match_score DECIMAL(3,2),
    match_reason TEXT,
    email_sent BOOLEAN DEFAULT false,
    email_sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Vector similarity search function
CREATE OR REPLACE FUNCTION search_similar_listings(
    query_embedding vector(768),
    match_count INTEGER DEFAULT 10,
    similarity_threshold DECIMAL DEFAULT 0.7
)
RETURNS TABLE (
    id TEXT,
    address TEXT,
    price INTEGER,
    bedrooms TEXT,
    bathrooms TEXT,
    area TEXT,
    lat DECIMAL(10, 8),
    lng DECIMAL(11, 8),
    source TEXT,
    url TEXT,
    scraped_at TIMESTAMP WITH TIME ZONE,
    strategy TEXT,
    similarity DECIMAL
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        l.id,
        l.address,
        l.price,
        l.bedrooms,
        l.bathrooms,
        l.area,
        l.lat,
        l.lng,
        l.source,
        l.url,
        l.scraped_at,
        l.strategy,
        1 - (l.embedding <=> query_embedding) as similarity
    FROM listings l
    WHERE l.embedding IS NOT NULL
        AND 1 - (l.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_listings_source ON listings(source);
CREATE INDEX IF NOT EXISTS idx_listings_scraped_at ON listings(scraped_at);
CREATE INDEX IF NOT EXISTS idx_listings_price ON listings(price);
CREATE INDEX IF NOT EXISTS idx_sold_comps_neighbourhood ON sold_comps(neighbourhood);
CREATE INDEX IF NOT EXISTS idx_sold_comps_sold_date ON sold_comps(sold_date);
CREATE INDEX IF NOT EXISTS idx_video_jobs_status ON video_jobs(status);
CREATE INDEX IF NOT EXISTS idx_video_jobs_customer_email ON video_jobs(customer_email);
CREATE INDEX IF NOT EXISTS idx_buyer_alerts_email ON buyer_alerts(email);
CREATE INDEX IF NOT EXISTS idx_buyer_alerts_is_active ON buyer_alerts(is_active);
CREATE INDEX IF NOT EXISTS idx_agent_matches_listing_id ON agent_matches(listing_id);
CREATE INDEX IF NOT EXISTS idx_agent_matches_alert_id ON agent_matches(alert_id);

-- Row Level Security (RLS)
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE sold_comps ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE buyer_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_matches ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- Allow public read access to listings
CREATE POLICY "Public listings are viewable by everyone" ON listings
    FOR SELECT USING (true);

-- Allow service role to insert/update listings
CREATE POLICY "Service role can manage listings" ON listings
    FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Allow public read access to sold comps
CREATE POLICY "Public sold comps are viewable by everyone" ON sold_comps
    FOR SELECT USING (true);

-- Allow service role to manage sold comps
CREATE POLICY "Service role can manage sold comps" ON sold_comps
    FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Users can only access their own video jobs
CREATE POLICY "Users can view own video jobs" ON video_jobs
    FOR SELECT USING (auth.uid()::text = customer_email);

CREATE POLICY "Users can insert own video jobs" ON video_jobs
    FOR INSERT WITH CHECK (auth.uid()::text = customer_email);

CREATE POLICY "Service role can manage video jobs" ON video_jobs
    FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Users can only access their own alerts
CREATE POLICY "Users can view own alerts" ON buyer_alerts
    FOR SELECT USING (auth.uid()::text = email);

CREATE POLICY "Users can manage own alerts" ON buyer_alerts
    FOR ALL USING (auth.uid()::text = email);

CREATE POLICY "Service role can manage alerts" ON buyer_alerts
    FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Agent matches are viewable by service role only
CREATE POLICY "Service role can manage agent matches" ON agent_matches
    FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Updated at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers
CREATE TRIGGER update_listings_updated_at BEFORE UPDATE ON listings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sold_comps_updated_at BEFORE UPDATE ON sold_comps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_video_jobs_updated_at BEFORE UPDATE ON video_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_buyer_alerts_updated_at BEFORE UPDATE ON buyer_alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""

    return sql

if __name__ == "__main__":
    print("=== 416Homes Database Schema ===")
    print("Copy this SQL and paste into Supabase SQL Editor:")
    print()
    print(generate_schema_sql())
    print()
    print("=== Schema Complete ===")
    print("After running this SQL, your database will be ready for the 416Homes application.")
