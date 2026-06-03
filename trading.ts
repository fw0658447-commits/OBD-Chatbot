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
