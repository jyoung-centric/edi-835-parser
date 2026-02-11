-- Add name_prefix and name_suffix columns to nm1_entities table
-- These columns capture additional name components from NM1 segments

ALTER TABLE bot.nm1_entities
ADD COLUMN name_prefix TEXT,
ADD COLUMN name_suffix TEXT;

-- Add comment to document the purpose
COMMENT ON COLUMN bot.nm1_entities.name_prefix IS 'Name prefix from NM1 segment (e.g., Dr., Mr., Ms.)';
COMMENT ON COLUMN bot.nm1_entities.name_suffix IS 'Name suffix from NM1 segment (e.g., Jr., Sr., III)';
