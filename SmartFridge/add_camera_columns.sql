-- Add columns to track camera-detected items
-- Run this SQL script in your MySQL database

USE smartfridge;

-- Add source column to track if item was added manually or via camera
ALTER TABLE item 
ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'manual' 
COMMENT 'Source of item: manual or camera';

-- Add timestamp for when camera last detected this item
ALTER TABLE item 
ADD COLUMN IF NOT EXISTS camera_last_seen DATETIME NULL 
COMMENT 'Last time camera detected this item';

-- Add index for faster camera item queries
ALTER TABLE item 
ADD INDEX IF NOT EXISTS idx_source (source);

-- Verify changes
DESCRIBE item;
