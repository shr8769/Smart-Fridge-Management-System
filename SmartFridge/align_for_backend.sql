-- align_for_backend.sql
-- Purpose: Align schema with backend.py expectations without changing code.
-- Safe to run multiple times (uses IF NOT EXISTS where possible).

CREATE DATABASE IF NOT EXISTS `smartfridge`
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

USE `smartfridge`;

-- Ensure lowercase `item` table exists with required columns.
-- Create if missing (complete schema the backend expects).
CREATE TABLE IF NOT EXISTS `item` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `label` VARCHAR(255) NOT NULL,
  `quantity` VARCHAR(100) DEFAULT NULL,
  `location` VARCHAR(100) DEFAULT NULL,
  `added_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expiry_date` DATE DEFAULT NULL,
  `status` VARCHAR(50) DEFAULT 'Fresh',
  `confidence` DECIMAL(3,2) DEFAULT NULL,
  `source` VARCHAR(50) DEFAULT 'manual',
  `camera_last_seen` DATETIME NULL,
  INDEX `idx_item_expiry` (`expiry_date`),
  INDEX `idx_item_label` (`label`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- If an uppercased `Item` table exists (older schema), make sure it has needed cols too.
-- These statements are no-ops if the columns already exist.
ALTER TABLE `Item`
  ADD COLUMN IF NOT EXISTS `source` VARCHAR(50) DEFAULT 'manual',
  ADD COLUMN IF NOT EXISTS `camera_last_seen` DATETIME NULL;

-- Also ensure the lowercase `item` table (if it existed before) has the needed cols.
ALTER TABLE `item`
  ADD COLUMN IF NOT EXISTS `source` VARCHAR(50) DEFAULT 'manual',
  ADD COLUMN IF NOT EXISTS `camera_last_seen` DATETIME NULL,
  ADD COLUMN IF NOT EXISTS `confidence` DECIMAL(3,2) NULL;

-- VoiceQuery table (created by original script; include here for completeness)
CREATE TABLE IF NOT EXISTS `VoiceQuery` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `query_text` TEXT NOT NULL,
  `response_text` TEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- RecipeSuggestion table (keep INT id to remain compatible with ItemRecipeLink)
CREATE TABLE IF NOT EXISTS `RecipeSuggestion` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `title` VARCHAR(255) NOT NULL,
  `ingredients` TEXT DEFAULT NULL,
  `instructions` TEXT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional: a simple `recipes` table if some endpoints refer to it
CREATE TABLE IF NOT EXISTS `recipes` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `title` VARCHAR(255) NOT NULL,
  `ingredients` TEXT DEFAULT NULL,
  `instructions` TEXT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Preserve the link table if it didn't exist
CREATE TABLE IF NOT EXISTS `ItemRecipeLink` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `item_id` INT NOT NULL,
  `recipe_id` INT NOT NULL,
  FOREIGN KEY (`item_id`) REFERENCES `Item`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`recipe_id`) REFERENCES `RecipeSuggestion`(`id`) ON DELETE CASCADE,
  UNIQUE KEY `ux_item_recipe` (`item_id`, `recipe_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
