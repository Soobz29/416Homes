-- Video pipeline storage buckets and schema extensions

-- Create storage buckets for video pipeline
INSERT INTO storage.buckets (id, name, public)
VALUES 
  ('listing-photos', 'listing-photos', true),
  ('videos', 'videos', true)
ON CONFLICT DO NOTHING;

-- Storage policies for listing-photos
CREATE POLICY "Anyone can view listing photos"
ON storage.objects FOR SELECT
USING (bucket_id = 'listing-photos');

CREATE POLICY "Authenticated can upload listing photos"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'listing-photos' AND auth.role() = 'authenticated');

-- Storage policies for videos
CREATE POLICY "Anyone can view videos"
ON storage.objects FOR SELECT
USING (bucket_id = 'videos');

CREATE POLICY "Authenticated can upload videos"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'videos' AND auth.role() = 'authenticated');

-- Extend video_jobs table with new columns
ALTER TABLE video_jobs
ADD COLUMN IF NOT EXISTS photo_manifest JSONB,
ADD COLUMN IF NOT EXISTS scene_plan JSONB,
ADD COLUMN IF NOT EXISTS audio_url TEXT,
ADD COLUMN IF NOT EXISTS final_video_path TEXT;

-- Indexes for common lookups
CREATE INDEX IF NOT EXISTS idx_video_jobs_customer_email 
ON video_jobs(customer_email);

CREATE INDEX IF NOT EXISTS idx_video_jobs_status 
ON video_jobs(status);

