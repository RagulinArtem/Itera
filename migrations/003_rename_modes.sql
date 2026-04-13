-- Rename ai_mode values: manager -> focus, psychologist -> support
UPDATE "Profiles" SET ai_mode = 'focus' WHERE ai_mode = 'manager';
UPDATE "Profiles" SET ai_mode = 'support' WHERE ai_mode = 'psychologist';
