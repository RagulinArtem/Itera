-- Add streak shield and mood tracking
ALTER TABLE "Profiles" ADD COLUMN IF NOT EXISTS streak_shield_used_at date NULL;
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS mood smallint NULL;

-- Morning intentions
CREATE TABLE IF NOT EXISTS intentions (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES "Profiles"(id),
    intention_date date NOT NULL DEFAULT CURRENT_DATE,
    items text[] NOT NULL,
    created_at timestamptz DEFAULT now(),
    UNIQUE(user_id, intention_date)
);
