CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE watchlist_items ADD COLUMN IF NOT EXISTS target_price NUMERIC;
CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_items_asset_unique ON watchlist_items(asset_id);

CREATE TABLE IF NOT EXISTS paper_cash_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_type TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    balance_after NUMERIC,
    note TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_paper_cash_transactions_created_at
ON paper_cash_transactions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_paper_orders_asset_status
ON paper_orders(asset_id, status);
