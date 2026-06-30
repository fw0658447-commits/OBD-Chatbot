'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiPost } from '../lib/api';

type MLTrainResult = {
  model_id?: string;
  model_type?: string;
  row_count?: number;
  train_rows?: number;
  test_rows?: number;
  metrics?: any;
  rule_baseline_metrics?: any;
  trading_metrics?: any;
  rule_trading_metrics?: any;
  feature_importance?: Array<{ feature: string; importance: number }>;
  prediction_preview?: any[];
  db_id?: string | null;
  persistence?: string;
};

function number(value: unknown, digits = 4) {
  return Number(value ?? 0).toFixed(digits);
}

export function MLPanel({ defaultSymbol = 'BTC/USD', defaultTimeframe = '1h' }: { defaultSymbol?: string; defaultTimeframe?: string }) {
  const [symbol, setSymbol] = useState(defaultSymbol);
  const [timeframe, setTimeframe] = useState(defaultTimeframe);
  const [modelType, setModelType] = useState('random_forest');
  const [limit, setLimit] = useState(650);
  const [result, setResult] = useState<MLTrainResult>({});
  const [assetPrediction, setAssetPrediction] = useState<any>({});
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  async function loadModels() {
    const data = await apiGet<any>('/api/ml/models?limit=10', { items: [], database_items: [] });
    setModels(data.items?.length ? data.items : (data.database_items ?? []));
  }

  async function trainModel() {
    setLoading(true);
    setMessage('');
    const data = await apiPost<MLTrainResult>('/api/ml/train', {
      symbols: [symbol, 'ETH/USD', 'AAPL', 'SPY'],
      timeframes: [timeframe],
      strategies: ['trend_atr_v0.7', 'pullback_ema_v0.7', 'breakout_range_v0.7'],
      limit,
      lookahead_bars: timeframe === '1h' ? 12 : 6,
      max_rows: 3000,
      model_type: modelType,
      persist: true
    }, { metrics: {}, rule_baseline_metrics: {}, feature_importance: [] });
    setResult(data);
    setMessage(data.model_id ? `Modell trainiert: ${data.model_id}` : 'Training fehlgeschlagen oder Backend nicht erreichbar');
    await loadModels();
    setLoading(false);
  }

  async function predictAsset(modelId?: string) {
    setLoading(true);
    const data = await apiPost<any>('/api/ml/predict-asset', {
      model_id: modelId || result.model_id || undefined,
      symbol,
      timeframe,
      strategy_name: 'trend_atr_v0.7',
      limit: 240
    }, { ml_prediction: null });
    setAssetPrediction(data);
    setLoading(false);
  }

  async function compareRuleVsML() {
    setLoading(true);
    const data = await apiPost<MLTrainResult>('/api/ml/compare-rule-vs-ml', {
      symbols: [symbol, 'ETH/USD', 'AAPL', 'SPY'],
      timeframes: [timeframe],
      strategies: ['trend_atr_v0.7', 'pullback_ema_v0.7'],
      limit,
      lookahead_bars: timeframe === '1h' ? 12 : 6,
      max_rows: 2500,
      model_type: modelType
    }, { ml_metrics: {}, rule_baseline_metrics: {}, feature_importance: [] } as any);
    setResult({
      model_id: (data as any).model_id,
      model_type: (data as any).model_type,
      row_count: (data as any).row_count,
      test_rows: (data as any).test_rows,
      metrics: (data as any).ml_metrics,
      rule_baseline_metrics: (data as any).rule_baseline_metrics,
      trading_metrics: (data as any).ml_trading_metrics,
      rule_trading_metrics: (data as any).rule_trading_metrics,
      feature_importance: (data as any).feature_importance
    });
    setMessage((data as any).interpretation ?? 'Vergleich abgeschlossen');
    await loadModels();
    setLoading(false);
  }

  useEffect(() => { loadModels(); }, []);

  const mlAccuracy = result.metrics?.accuracy;
  const ruleAccuracy = result.rule_baseline_metrics?.accuracy;
  const prediction = assetPrediction.ml_prediction;

  return (
    <div className="stack">
      {message && <section className="card">{message}</section>}

      <section className="card">
        <h2>ML-Modell v0.8</h2>
        <p className="muted">Trainiert ein Baseline-Modell auf den v0.7-Features und vergleicht es gegen die bisherige Regel-KI. Live-Trading bleibt gesperrt.</p>
        <div className="row">
          <input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="BTC/USD" />
          <select value={timeframe} onChange={(event) => setTimeframe(event.target.value)}>
            <option value="1h">1h</option>
            <option value="4h">4h</option>
            <option value="1D">1D</option>
          </select>
          <select value={modelType} onChange={(event) => setModelType(event.target.value)}>
            <option value="random_forest">Random Forest</option>
            <option value="logistic_regression">Logistic Regression</option>
          </select>
          <input type="number" min={180} max={2500} value={limit} onChange={(event) => setLimit(Number(event.target.value))} />
          <button className="primary" onClick={trainModel} disabled={loading}>Modell trainieren</button>
          <button onClick={compareRuleVsML} disabled={loading}>Regel vs. ML vergleichen</button>
          <button onClick={() => predictAsset()} disabled={loading}>Asset prognostizieren</button>
        </div>
      </section>

      <div className="grid">
        <section className="card">
          <h2>Modellmetriken</h2>
          <div className="kpi">{number(mlAccuracy, 3)}</div>
          <p className="muted">ML Accuracy</p>
          <p>Regelmodell Accuracy: {number(ruleAccuracy, 3)}</p>
          <p>Zeilen: {result.row_count ?? 0}</p>
          <p>Train/Test: {result.train_rows ?? '-'} / {result.test_rows ?? '-'}</p>
          <p>Persistenz: {result.persistence ?? 'memory'}</p>
        </section>

        <section className="card">
          <h2>Trading-Vergleich</h2>
          <p>ML Trades: {result.trading_metrics?.trades ?? 0}</p>
          <p>ML Winrate: {number(result.trading_metrics?.win_rate_percent, 2)}%</p>
          <p>ML Profit Factor: {result.trading_metrics?.profit_factor ?? '-'}</p>
          <p>Regel Trades: {result.rule_trading_metrics?.trades ?? 0}</p>
          <p>Regel Winrate: {number(result.rule_trading_metrics?.win_rate_percent, 2)}%</p>
          <p>Regel Profit Factor: {result.rule_trading_metrics?.profit_factor ?? '-'}</p>
        </section>

        <section className="card">
          <h2>Aktuelle ML-Prognose</h2>
          {prediction ? (
            <>
              <p><strong>{prediction.prediction_direction}</strong></p>
              <p>Short: {number(prediction.probabilities?.short, 4)}</p>
              <p>Neutral: {number(prediction.probabilities?.neutral, 4)}</p>
              <p>Long: {number(prediction.probabilities?.long, 4)}</p>
              <p className="muted">Modell: {prediction.model_id}</p>
            </>
          ) : <p>Noch keine Asset-Prognose.</p>}
        </section>
      </div>

      <section className="card">
        <h2>Feature Importance</h2>
        <table>
          <thead><tr><th align="left">Feature</th><th align="right">Wichtigkeit</th></tr></thead>
          <tbody>
            {(result.feature_importance ?? []).slice(0, 12).map((item) => (
              <tr key={item.feature}><td>{item.feature}</td><td align="right">{number(item.importance, 6)}</td></tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>Modellversionen</h2>
        <table>
          <thead><tr><th align="left">Model ID</th><th align="left">Typ</th><th align="right">Accuracy</th><th align="right">Zeilen</th></tr></thead>
          <tbody>
            {models.map((item) => (
              <tr key={item.model_id}>
                <td>{item.model_id}</td>
                <td>{item.model_type}</td>
                <td align="right">{number(item.metrics?.accuracy, 3)}</td>
                <td align="right">{item.row_count ?? '-'}</td>
              </tr>
            ))}
            {models.length === 0 && <tr><td colSpan={4}>Noch keine Modelle trainiert.</td></tr>}
          </tbody>
        </table>
      </section>
    </div>
  );
}
