export type Candle = {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

export type Quote = {
  symbol: string;
  price: number;
  change?: number;
  change_percent?: number;
  timestamp?: string;
  provider?: string;
  error?: string;
};

export type Prediction = {
  symbol: string;
  timeframe: string;
  horizon: string;
  direction: 'long' | 'short' | 'neutral' | string;
  probability_long: number;
  probability_short: number;
  probability_neutral: number;
  expected_return_percent?: number;
  confidence_score: number;
  risk_score: number;
  model_version: string;
  explanation?: string;
};

export type SignalPreview = {
  signal_type: string;
  signal_score: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  crv: number;
  reason?: string;
  strategy?: string;
} | null;

export type AssetAnalysis = {
  symbol: string;
  timeframe: string;
  quote: Quote;
  candles: Candle[];
  indicators: Record<string, number | boolean | string>;
  prediction: Prediction;
  signal_preview: SignalPreview;
  strategy_name?: string;
  available_strategies?: StrategyDefinition[];
  persistence: string;
};

export type SearchResult = {
  symbol: string;
  name?: string;
  asset_type?: string;
  exchange?: string;
  currency?: string;
};

export type StrategyDefinition = {
  name: string;
  label: string;
  description: string;
  family: string;
  min_confidence: number;
  max_risk_score: number;
  default_max_hold_bars: number;
  default_params?: Record<string, any>;
  optimization_grid?: Record<string, any[]>;
};

export type InstrumentLookupResult = {
  query: string;
  query_type: string;
  provider: string;
  online: boolean;
  results: Array<{
    symbol?: string;
    name?: string;
    asset_type?: string;
    exchange?: string;
    currency?: string;
    figi?: string;
    composite_figi?: string;
    market_sector?: string;
    security_description?: string;
    source?: string;
  }>;
  warnings?: string[];
};

export type InternetAnalysisResult = {
  symbol: string;
  online: boolean;
  headline_count: number;
  sentiment_score: number;
  sentiment_label: string;
  risk_flags: string[];
  summary: string;
  warning?: string | null;
  articles: Array<{
    source?: string;
    headline?: string;
    summary?: string;
    url?: string;
    datetime?: string | number;
    provider?: string;
    sentiment_score?: number | null;
    sentiment_label?: string;
  }>;
};

export type TradeRecommendation = {
  symbol: string;
  timeframe: string;
  strategy_name: string;
  decision: {
    action: 'LONG' | 'SHORT' | 'WATCH' | 'NO_TRADE' | string;
    side: string;
    trade_decision: string;
    risk_level: string;
    risk_score_adjusted: number;
    position_size_hint: string;
    confidence_score: number;
    long_probability: number;
    short_probability: number;
    neutral_probability: number;
    blockers: string[];
    reasons: string[];
    checklist: Array<{ name: string; passed: boolean; value: string }>;
  };
  prediction: Prediction;
  signal_preview: SignalPreview;
  data_quality: Record<string, any>;
  online_analysis?: InternetAnalysisResult | null;
  explanation: string;
  disclaimer: string;
};
