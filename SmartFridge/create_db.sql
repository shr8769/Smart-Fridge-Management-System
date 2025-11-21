-- create_db.sql
-- Run this script to create the smartfridge database, a sample user, tables and sample data.
-- IMPORTANT: change passwords and users to match your environment before running in production.

-- 1) Create database
CREATE DATABASE IF NOT EXISTS `smartfridge`
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

USE `smartfridge`;

-- 2) Create tables (use lowercase `item` to match backend expectations)
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

CREATE TABLE IF NOT EXISTS `RemovalEvent` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `item_id` INT NOT NULL,
  `reason` VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`item_id`) REFERENCES `item`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `RecipeSuggestion` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `title` VARCHAR(255) NOT NULL,
  `ingredients` TEXT DEFAULT NULL,
  `instructions` TEXT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `VoiceQuery` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `query_text` TEXT NOT NULL,
  `response_text` TEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ItemRecipeLink` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `item_id` INT NOT NULL,
  `recipe_id` INT NOT NULL,
  FOREIGN KEY (`item_id`) REFERENCES `item`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`recipe_id`) REFERENCES `RecipeSuggestion`(`id`) ON DELETE CASCADE,
  UNIQUE KEY `ux_item_recipe` (`item_id`, `recipe_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional recipes table for some endpoints (kept simple)
CREATE TABLE IF NOT EXISTS `recipes` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `title` VARCHAR(255) NOT NULL,
  `ingredients` TEXT DEFAULT NULL,
  `instructions` TEXT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3) Sample data for quick testing
-- Idempotent sample items (skip if a matching label already exists)
INSERT INTO `item` (label, quantity, location, expiry_date, status, confidence)
SELECT 'Whole Milk', '2L', 'Door', DATE_ADD(CURDATE(), INTERVAL 7 DAY), 'Fresh', 0.95
WHERE NOT EXISTS (SELECT 1 FROM `item` WHERE `label` = 'Whole Milk');

INSERT INTO `item` (label, quantity, location, expiry_date, status, confidence)
SELECT 'Free-Range Eggs', '12 pcs', 'Top Shelf', DATE_ADD(CURDATE(), INTERVAL 12 DAY), 'Fresh', 0.92
WHERE NOT EXISTS (SELECT 1 FROM `item` WHERE `label` = 'Free-Range Eggs');

INSERT INTO `item` (label, quantity, location, expiry_date, status, confidence)
SELECT 'Romaine Lettuce', '1 head', 'Crisper', DATE_ADD(CURDATE(), INTERVAL 3 DAY), 'Fresh', 0.88
WHERE NOT EXISTS (SELECT 1 FROM `item` WHERE `label` = 'Romaine Lettuce');

-- Note: Omit sample inserts for RecipeSuggestion to avoid conflicts
-- when environments use a VARCHAR(36) id without default.
-- You can add recipes later via the app or with explicit ids.

-- Idempotent link insert (skip if already linked)
INSERT INTO `ItemRecipeLink` (item_id, recipe_id)
SELECT i.id, r.id
FROM `item` i
JOIN `RecipeSuggestion` r ON r.title = 'Garden Salad'
LEFT JOIN `ItemRecipeLink` l ON l.item_id = i.id AND l.recipe_id = r.id
WHERE i.label = 'Romaine Lettuce' AND l.id IS NULL
LIMIT 1;

-- Insert manually added item
INSERT INTO `item` (label, quantity, location, expiry_date, status, source)
VALUES ('Whole Milk', '2L', 'Door', '2025-11-28', 'Fresh', 'manual');

-- Insert camera-detected item
INSERT INTO `item` (label, quantity, location, added_date, expiry_date, status, source, confidence, camera_last_seen)
VALUES ('apple', '1 unit', 'Camera Detected', NOW(), NULL, 'Fresh', 'camera', 0.87, NOW());

-- Insert voice-added item
INSERT INTO `item` (label, quantity, location, added_date, status, source)
VALUES ('chicken', '20 kg', 'Freezer', NOW(), 'Fresh', 'voice');

-- Insert multiple items
INSERT INTO `item` (label, quantity, location, expiry_date, status)
VALUES 
  ('Free-Range Eggs', '12 pcs', 'Top Shelf', '2025-12-03', 'Fresh'),
  ('Romaine Lettuce', '1 head', 'Crisper', '2025-11-24', 'Fresh'),
  ('Cheddar Cheese', '500g', 'Middle Shelf', '2025-12-15', 'Fresh');



