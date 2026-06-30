CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE bot_signals
    ADD COLUMN IF NOT EXISTS decision_mode TEXT DEFAULT 'rule',
    ADD COLUMN IF NOT EXISTS model_source TEXT DEFAULT 'rule',
    ADD COLUMN IF NOT EXISTS ml_model_id TEXT,
    ADD COLUMN IF NOT EXISTS ml_direction TEXT,
    ADD COLUMN IF NOT EXISTS ml_probability NUMERIC,
    ADD COLUMN IF NOT EXISTS decision_score NUMERIC,
    ADD COLUMN IF NOT EXISTS decision_details JSONB DEFAULT '{}'::jsonb;

ALTER TABLE paper_orders
    ADD COLUMN IF NOT EXISTS decision_mode TEXT DEFAULT 'rule',
    ADD COLUMN IF NOT EXISTS model_source TEXT DEFAULT 'rule',
    ADD COLUMN IF NOT EXISTS ml_model_id TEXT,
    ADD COLUMN IF NOT EXISTS ml_direction TEXT,
    ADD COLUMN IF NOT EXISTS ml_probability NUMERIC,
    ADD COLUMN IF NOT EXISTS decision_score NUMERIC,
    ADD COLUMN IF NOT EXISTS decision_details JSONB DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS bot_decision_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT,
    timeframe TEXT,
    strategy TEXT,
    decision_mode TEXT,
    model_source TEXT,
    ml_model_id TEXT,
    allowed BOOLEAN,
    decision_score NUMERIC,
    reason TEXT,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_paper_orders_decision_mode ON paper_orders(decision_mode);
CREATE INDEX IF NOT EXISTS idx_bot_signals_decision_mode ON bot_signals(decision_mode);
CREATE INDEX IF NOT EXISTS idx_bot_decision_audit_created_at ON bot_decision_audit(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bot_decision_audit_mode ON bot_decision_audit(decision_mode);
