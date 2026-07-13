-- Add location/source_system tracking columns to raw_835_files
-- (app's build_raw_835_file_row now writes these). Non-destructive.

ALTER TABLE bot.raw_835_files
    ADD COLUMN IF NOT EXISTS location TEXT,
    ADD COLUMN IF NOT EXISTS source_system TEXT;
