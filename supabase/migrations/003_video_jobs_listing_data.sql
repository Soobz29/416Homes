-- Optional listing metadata (custom uploads, tier flags) for video jobs
ALTER TABLE video_jobs
ADD COLUMN IF NOT EXISTS listing_data JSONB;
