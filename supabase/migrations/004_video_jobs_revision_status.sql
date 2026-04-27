-- Allow `revision_requested` as a valid video_jobs.status.
--
-- Context: api/main.py and the video worker both transition jobs through
-- `revision_requested` (set when a customer asks for a redo, then picked up
-- and reset to `generating_script`). The check constraint defined in
-- 002_fix_video_jobs.sql did not include this value, so any UPDATE that
-- tried to set it failed in production.
--
-- This migration drops and re-adds the status check constraint with the
-- additional value. Safe to re-run: DROP IF EXISTS + ADD.

ALTER TABLE video_jobs DROP CONSTRAINT IF EXISTS video_jobs_status_check;

ALTER TABLE video_jobs
ADD CONSTRAINT video_jobs_status_check
CHECK (status IN (
  'pending',
  'generating_script',
  'script_generated',
  'generating_audio',
  'audio_generated',
  'generating_video',
  'revision_requested',
  'completed',
  'failed'
));
