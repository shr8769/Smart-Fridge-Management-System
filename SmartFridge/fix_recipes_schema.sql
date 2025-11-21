-- fix_recipes_schema.sql
-- Align `recipes` table with backend expectations (id is VARCHAR(36))

USE `smartfridge`;

-- Change id to VARCHAR(36) and ensure it is the primary key
ALTER TABLE `recipes`
  MODIFY COLUMN `id` VARCHAR(36) NOT NULL;

-- Reset primary key to id (no auto_increment for VARCHAR)
ALTER TABLE `recipes`
  DROP PRIMARY KEY,
  ADD PRIMARY KEY (`id`);

-- Ensure columns exist
ALTER TABLE `recipes`
  MODIFY COLUMN `title` TEXT NULL,
  MODIFY COLUMN `created_at` DATETIME NULL;
