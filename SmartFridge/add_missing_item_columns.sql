-- add_missing_item_columns.sql
-- Safely add columns required by backend to legacy `item` table

USE `smartfridge`;

-- Add `source` column (who/what added the item: manual, camera, voice)
ALTER TABLE `item`
  ADD COLUMN IF NOT EXISTS `source` VARCHAR(50) DEFAULT 'manual';

-- Add last seen timestamp for camera-detected items
ALTER TABLE `item`
  ADD COLUMN IF NOT EXISTS `camera_last_seen` DATETIME NULL;

-- Add detection confidence for camera items
ALTER TABLE `item`
  ADD COLUMN IF NOT EXISTS `confidence` DECIMAL(3,2) NULL;
