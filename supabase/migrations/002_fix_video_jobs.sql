-- Add missing columns to video_jobs table
ALTER TABLE video_jobs 
ADD COLUMN IF NOT EXISTS customer_email TEXT,
ADD COLUMN IF NOT EXISTS customer_name TEXT,
ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS error_message TEXT,
ADD COLUMN IF NOT EXISTS photo_manifest JSONB,
ADD COLUMN IF NOT EXISTS scene_plan JSONB,
ADD COLUMN IF NOT EXISTS audio_url TEXT,
ADD COLUMN IF NOT EXISTS final_video_path TEXT;

-- Drop old status constraint
ALTER TABLE video_jobs DROP CONSTRAINT IF EXISTS video_jobs_status_check;

-- Add new status constraint with correct values
ALTER TABLE video_jobs 
ADD CONSTRAINT video_jobs_status_check 
CHECK (status IN (
  'pending',
  'generating_script',
  'script_generated',
  'generating_audio',
  'audio_generated', 
  'generating_video',
  'completed',
  'failed'
));

-- Ensure storage buckets exist
INSERT INTO storage.buckets (id, name, public)
VALUES 
  ('listing-photos', 'listing-photos', true),
  ('videos', 'videos', true)
ON CONFLICT (id) DO NOTHING;

-- Storage policies
DO $$ 
BEGIN
  -- listing-photos policies
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE schemaname = 'storage' 
    AND tablename = 'objects' 
    AND policyname = 'Anyone can view listing photos'
  ) THEN
    CREATE POLICY "Anyone can view listing photos"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'listing-photos');
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE schemaname = 'storage' 
    AND tablename = 'objects' 
    AND policyname = 'Service role can upload listing photos'
  ) THEN
    CREATE POLICY "Service role can upload listing photos"
    ON storage.objects FOR INSERT
    WITH CHECK (bucket_id = 'listing-photos');
  END IF;

  -- videos policies
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE schemaname = 'storage' 
    AND tablename = 'objects' 
    AND policyname = 'Anyone can view videos'
  ) THEN
    CREATE POLICY "Anyone can view videos"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'videos');
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE schemaname = 'storage' 
    AND tablename = 'objects' 
    AND policyname = 'Service role can upload videos'
  ) THEN
    CREATE POLICY "Service role can upload videos"
    ON storage.objects FOR INSERT
    WITH CHECK (bucket_id = 'videos');
  END IF;
END $$;
