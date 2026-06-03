'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiPost } from '../lib/api';
import { EquityCurve } from './EquityCurve';
import type { StrategyDefinition } from '../types/trading';

type BacktestResult = {
  symbol?: string;
  timeframe?: string;
  strategy?: string;
  strategy_label?: string;
  sample?: string;
  initial_capital?: number;
  final_equity?: number;
  signals_count?: number;
  blocked_signals_count?: number;
  metrics?: Record<string, any>;
  equity_curve?: Array<{ timestamp: string; equity: number; event?: string }>;
  trades?: any[];
  backtest_id?: string | null;
  persistence?: string;
};

type WalkForwardResult = {
  symbol?: string;
  timeframe?: string;
  strategy?: string;
  sample?: string;
  splits?: number;
  initial_capital?: number;
  final_equity?: number;
  windows?: any[];
  metrics?: Record<string, any>;
  equity_curve?: Array<{ timestamp: string; equity: number; event?: string }>;
};

type OptimizationResult = {
  strategy?: string;
  objective?: string;
  tested_combinations?: number;
  best?: any;
  ranking?: any[];
  optimization_id?: string | null;
  persistence?: string;
};

type MLDatasetResult = {
  row_count?: number;
  feature_columns?: string[];
  target_columns?: string[];
  rows?: any[];
  csv?: string;
  note?: string;
  dataset_id?: string | null;
  persistence?: string;
};

function number(value: unknown, digits = 2) {
  return Number(value ?? 0).toFixed(digits);
}

const FALLBACK_STRATEGIES: StrategyDefinition[] = [
  { name: 'trend_atr_v0.7', label: 'Trendfolge ATR', description: 'Trendfolge mit ATR Stop/Ziel.', family: 'trend_following', min_confidence: 65, max_risk_score: 70, default_max_hold_bars: 48 },
  { name: 'pullback_ema_v0.7', label: 'Pullback EMA21', description: 'Ruecksetzer zum EMA21 im Trend.', family: 'pullback', min_confidence: 58, max_risk_score: 72, default_max_hold_bars: 36 },
  { name: 'breakout_range_v0.7', label: 'Breakout Range', description: 'Ausbruch aus 20-Kerzen-Range.', family: 'breakout', min_confidence: 60, max_risk_score: 76, default_max_hold_bars: 32 },
  { name: 'mean_reversion_rsi_v0.7', label: 'Mean Reversion RSI', description: 'Antizyklischer RSI-Rebound.', family: 'mean_reversion', min_confidence: 35, max_risk_score: 82, default_max_hold_bars: 24 }
];

export function BacktestPanel({ defaultSymbol = 'BTC/USD', defaultTimeframe = '1h' }: { defaultSymbol?: string; defaultTimeframe?: string }) {
  const [symbol, setSymbol] = useState(defaultSymbol);
  const [timeframe, setTimeframe] = useState(defaultTimeframe);
  const [strategy, setStrategy] = useState('trend_atr_v0.7');
  const [limit, setLimit] = useState(420);
  const [capital, setCapital] = useState(10000);
  const [strategies, setStrategies] = useState<StrategyDefinition[]>(FALLBACK_STRATEGIES);
  const [result, setResult] = useState<BacktestResult>({});
  const [walkForward, setWalkForward] = useState<WalkForwardResult>({ windows: [] });
  const [compare, setCompare] = useState<any>({ items: [], ranking: [] });
  const [optimization, setOptimization] = useState<OptimizationResult>({ ranking: [] });
  const [mlDataset, setMlDataset] = useState<MLDatasetResult>({ rows: [] });
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  async function loadStrategies() {
    const data = await apiGet<{ items: StrategyDefinition[] }>('/api/backtest/strategies', { items: FALLBACK_STRATEGIES });
    setStrategies(data.items?.length ? data.items : FALLBACK_STRATEGIES);
  }

  async function runBacktest() {
    setLoading(true);
    setMessage('');
    const data = await apiPost<BacktestResult>('/api/backtest/run', {
      symbol,
      timeframe,
      strategy_name: strategy,
      limit,
      initial_capital: capital,
      risk_per_trade: 0.01,
      persist: true
    }, { metrics: {}, trades: [], equity_curve: [] });
    setResult(data);
    setMessage(data.backtest_id ? `Backtest gespeichert: ${data.backtest_id}` : `Backtest im ${data.persistence ?? 'memory'}-Modus ausgefuehrt`);
    await loadRuns();
    setLoading(false);
  }

  async function runCompare() {
    setLoading(true);
    const data = await apiPost<any>('/api/backtest/compare', {
      symbols: ['BTC/USD', 'ETH/USD', 'AAPL', 'SPY'],
      timeframes: ['1h', '4h'],
      strategies: strategies.map((item) => item.name),
      limit,
      initial_capital: capital
    }, { items: [], ranking: [] });
    setCompare(data);
    setLoading(false);
  }

  async function runWalkForward() {
    setLoading(true);
    const data = await apiPost<WalkForwardResult>('/api/backtest/walk-forward', {
      symbol,
      timeframe,
      strategy_name: strategy,
      limit: Math.max(limit, 720),
      initial_capital: capital,
      splits: 3
    }, { windows: [], metrics: {}, equity_curve: [] });
    setWalkForward(data);
    setLoading(false);
  }


  async function runOptimization() {
    setLoading(true);
    const data = await apiPost<OptimizationResult>('/api/backtest/optimize', {
      symbol,
      timeframe,
      strategy_name: strategy,
      limit,
      initial_capital: capital,
      risk_per_trade: 0.01,
      objective: 'robust_score',
      max_combinations: 48,
      persist: true
    }, { ranking: [] });
    setOptimization(data);
    setMessage(data.optimization_id ? `Optimierung gespeichert: ${data.optimization_id}` : `Optimierung im ${data.persistence ?? 'memory'}-Modus ausgefuehrt`);
    setLoading(false);
  }

  async function exportDataset() {
    setLoading(true);
    const data = await apiPost<MLDatasetResult>('/api/backtest/ml-dataset', {
      symbols: [symbol, 'ETH/USD', 'AAPL', 'SPY'],
      timeframes: [timeframe],
      strategies: strategies.map((item) => item.name),
      limit: Math.max(limit, 500),
      lookahead_bars: timeframe === '1h' ? 12 : 6,
      max_rows: 1500,
      include_csv: true,
      persist: true
    }, { rows: [], feature_columns: [], target_columns: [] });
    setMlDataset(data);
    setMessage(data.dataset_id ? `ML-Dataset gespeichert: ${data.dataset_id}` : `ML-Dataset im ${data.persistence ?? 'memory'}-Modus erzeugt`);
    setLoading(false);
  }

  async function loadRuns() {
    const data = await apiGet<any>('/api/backtest/runs?limit=12', { items: [] });
    setRuns(data.items ?? []);
  }

  useEffect(() => {
    loadStrategies();
    loadRuns();
  }, []);

  const metrics = result.metrics ?? {};
  const wfMetrics = walkForward.metrics ?? {};

  return (
    <div className="stack">
      {message && <section className="card">{message}</section>}

      <section className="card">
        <h2>Backtesting v0.8</h2>
        <p className="muted">Vergleicht mehrere regelbasierte Strategien mit KI-Filter. Das ist ein Simulator, keine Renditezusage.</p>
        <div className="row">
          <input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="BTC/USD, AAPL, SPY" />
          <select value={timeframe} onChange={(event) => setTimeframe(event.target.value)}>
            <option value="1m">1m</option>
            <option value="5m">5m</option>
            <option value="15m">15m</option>
            <option value="1h">1h</option>
            <option value="4h">4h</option>
            <option value="1D">1D</option>
          </select>
          <select value={strategy} onChange={(event) => setStrategy(event.target.value)}>
            {strategies.map((item) => <option key={item.name} value={item.name}>{item.label}</option>)}
          </select>
          <input type="number" value={limit} onChange={(event) => setLimit(Number(event.target.value))} min={120} max={1500} />
          <input type="number" value={capital} onChange={(event) => setCapital(Number(event.target.value))} min={1000} />
          <button className="primary" onClick={runBacktest} disabled={loading}>Backtest starten</button>
          <button onClick={runCompare} disabled={loading}>Strategien vergleichen</button>
          <button onClick={runWalkForward} disabled={loading}>Walk-forward</button>
          <button onClick={runOptimization} disabled={loading}>Parameter optimieren</button>
          <button onClick={exportDataset} disabled={loading}>ML-Dataset exportieren</button>
        </div>
      </section>

      <section className="card">
        <h2>Strategie-Katalog</h2>
        <div className="grid">
          {strategies.map((item) => (
            <div className="card" key={item.name}>
              <h3>{item.label}</h3>
              <p className="muted">{item.family}</p>
              <p>{item.description}</p>
              <p>Min. Confidence: {item.min_confidence} / Max. Risk: {item.max_risk_score}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="grid">
        <section className="card">
          <h2>Einzel-Backtest</h2>
          <div className="kpi">{number(metrics.return_percent, 2)}%</div>
          <p className="muted">Return</p>
          <p>Strategie: {result.strategy_label ?? result.strategy ?? '-'}</p>
          <p>Startkapital: {number(result.initial_capital, 2)}</p>
          <p>Endkapital: {number(result.final_equity, 2)}</p>
          <p>Trades: {metrics.total_trades ?? 0}</p>
          <p>Signale: {result.signals_count ?? 0}</p>
          <p>Blockierte Signale: {result.blocked_signals_count ?? 0}</p>
        </section>

        <section className="card">
          <h2>Qualität</h2>
          <p>Trefferquote: {number(metrics.win_rate_percent, 2)}%</p>
          <p>Profit Factor: {metrics.profit_factor ?? '-'}</p>
          <p>Expectancy/Trade: {number(metrics.expectancy_per_trade, 2)}</p>
          <p>Max. Drawdown: {number(metrics.max_drawdown_percent, 2)}%</p>
          <p>Ø Gewinn: {number(metrics.average_win, 2)}</p>
          <p>Ø Verlust: {number(metrics.average_loss, 2)}</p>
        </section>
      </div>

      <section className="card">
        <h2>Equity-Kurve</h2>
        <EquityCurve points={result.equity_curve ?? []} />
      </section>

      <section className="card">
        <h2>Trades</h2>
        <table>
          <thead><tr><th align="left">Zeit</th><th align="left">Strategie</th><th align="left">Side</th><th align="right">Entry</th><th align="right">Exit</th><th align="right">P/L</th><th align="left">Grund</th></tr></thead>
          <tbody>
            {(result.trades ?? []).slice(0, 30).map((trade, index) => (
              <tr key={`${trade.entry_time}-${index}`}>
                <td>{trade.entry_time}</td>
                <td>{trade.strategy}</td>
                <td>{trade.side}</td>
                <td align="right">{number(trade.entry_price, 4)}</td>
                <td align="right">{number(trade.exit_price, 4)}</td>
                <td align="right" className={Number(trade.pnl_amount ?? 0) >= 0 ? 'good' : 'bad'}>{number(trade.pnl_amount, 2)}</td>
                <td>{trade.exit_reason}</td>
              </tr>
            ))}
            {(result.trades ?? []).length === 0 && <tr><td colSpan={7}>Noch keine Backtest-Trades.</td></tr>}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>Strategie-/Asset-Vergleich</h2>
        <table>
          <thead><tr><th align="left">Asset</th><th align="left">TF</th><th align="left">Strategie</th><th align="right">Trades</th><th align="right">Return</th><th align="right">Winrate</th><th align="right">PF</th><th align="right">DD</th></tr></thead>
          <tbody>
            {(compare.ranking ?? []).slice(0, 30).map((item: any) => (
              <tr key={`${item.symbol}-${item.timeframe}-${item.strategy}`}>
                <td>{item.symbol}</td><td>{item.timeframe}</td><td>{item.strategy}</td><td align="right">{item.metrics.total_trades}</td><td align="right">{number(item.metrics.return_percent, 2)}%</td><td align="right">{number(item.metrics.win_rate_percent, 2)}%</td><td align="right">{item.metrics.profit_factor ?? '-'}</td><td align="right">{number(item.metrics.max_drawdown_percent, 2)}%</td>
              </tr>
            ))}
            {(compare.ranking ?? []).length === 0 && <tr><td colSpan={8}>Noch kein Vergleich ausgefuehrt.</td></tr>}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>Walk-forward / Out-of-sample</h2>
        <div className="grid">
          <div>
            <div className="kpi">{number(wfMetrics.return_percent, 2)}%</div>
            <p className="muted">Aggregierter Return</p>
            <p>Trades: {wfMetrics.total_trades ?? 0}</p>
            <p>Trefferquote: {number(wfMetrics.win_rate_percent, 2)}%</p>
            <p>Profit Factor: {wfMetrics.profit_factor ?? '-'}</p>
            <p>Max. Drawdown: {number(wfMetrics.max_drawdown_percent, 2)}%</p>
          </div>
          <EquityCurve points={walkForward.equity_curve ?? []} />
        </div>
        <table>
          <thead><tr><th align="left">Fenster</th><th align="left">Start</th><th align="left">Ende</th><th align="right">Trades</th><th align="right">Return</th><th align="right">PF</th><th align="right">DD</th></tr></thead>
          <tbody>
            {(walkForward.windows ?? []).map((item) => (
              <tr key={item.window}>
                <td>{item.window}</td><td>{item.test_start_time}</td><td>{item.test_end_time}</td><td align="right">{item.metrics.total_trades}</td><td align="right">{number(item.metrics.return_percent, 2)}%</td><td align="right">{item.metrics.profit_factor ?? '-'}</td><td align="right">{number(item.metrics.max_drawdown_percent, 2)}%</td>
              </tr>
            ))}
            {(walkForward.windows ?? []).length === 0 && <tr><td colSpan={7}>Noch kein Walk-forward-Test ausgefuehrt.</td></tr>}
          </tbody>
        </table>
      </section>


      <section className="card">
        <h2>Parameter-Optimierung</h2>
        <p className="muted">v0.7 testet Strategieparameter wie ATR-Stop, ATR-Ziel, Confidence-Filter und Haltedauer. Ranking erfolgt standardmaessig per Robust Score.</p>
        {optimization.best && (
          <div className="grid">
            <div>
              <div className="kpi">{number(optimization.best.score, 2)}</div>
              <p className="muted">Bester Score</p>
              <p>Strategie: {optimization.best.strategy}</p>
              <p>Return: {number(optimization.best.metrics?.return_percent, 2)}%</p>
              <p>Profit Factor: {optimization.best.metrics?.profit_factor ?? '-'}</p>
              <p>Max. Drawdown: {number(optimization.best.metrics?.max_drawdown_percent, 2)}%</p>
            </div>
            <pre>{JSON.stringify(optimization.best.params ?? {}, null, 2)}</pre>
          </div>
        )}
        <table>
          <thead><tr><th align="right">Rang</th><th align="right">Score</th><th align="right">Trades</th><th align="right">Return</th><th align="right">PF</th><th align="right">DD</th><th align="left">Parameter</th></tr></thead>
          <tbody>
            {(optimization.ranking ?? []).slice(0, 12).map((item, index) => (
              <tr key={`${index}-${item.score}`}>
                <td align="right">{index + 1}</td>
                <td align="right">{number(item.score, 2)}</td>
                <td align="right">{item.metrics?.total_trades ?? 0}</td>
                <td align="right">{number(item.metrics?.return_percent, 2)}%</td>
                <td align="right">{item.metrics?.profit_factor ?? '-'}</td>
                <td align="right">{number(item.metrics?.max_drawdown_percent, 2)}%</td>
                <td><code>{JSON.stringify(item.params ?? {})}</code></td>
              </tr>
            ))}
            {(optimization.ranking ?? []).length === 0 && <tr><td colSpan={7}>Noch keine Parameter-Optimierung ausgefuehrt.</td></tr>}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>ML-Trainingsdatensatz</h2>
        <p className="muted">Exportiert Features aus Kerzen, Indikatoren, KI-Prognosen und Strategie-Signalen. Zielvariable ist die spaetere Kursbewegung nach Lookahead-Bars.</p>
        <div className="grid">
          <div>
            <div className="kpi">{mlDataset.row_count ?? 0}</div>
            <p className="muted">Zeilen</p>
            <p>Features: {(mlDataset.feature_columns ?? []).join(', ') || '-'}</p>
            <p>Targets: {(mlDataset.target_columns ?? []).join(', ') || '-'}</p>
          </div>
          <div>
            <p>{mlDataset.note ?? 'Noch kein Dataset erzeugt.'}</p>
            {mlDataset.csv && <textarea readOnly value={mlDataset.csv.slice(0, 2500)} rows={10} />}
          </div>
        </div>
        <table>
          <thead><tr><th align="left">Zeit</th><th align="left">Asset</th><th align="left">Strategie</th><th align="right">RSI</th><th align="right">Conf.</th><th align="right">CRV</th><th align="right">Future %</th><th align="right">Label</th></tr></thead>
          <tbody>
            {(mlDataset.rows ?? []).slice(0, 20).map((row, index) => (
              <tr key={`${row.timestamp}-${index}`}>
                <td>{row.timestamp}</td><td>{row.symbol}</td><td>{row.strategy}</td><td align="right">{number(row.rsi, 2)}</td><td align="right">{number(row.confidence_score, 1)}</td><td align="right">{number(row.crv, 2)}</td><td align="right">{number(row.future_return_percent, 3)}%</td><td align="right">{row.target_label}</td>
              </tr>
            ))}
            {(mlDataset.rows ?? []).length === 0 && <tr><td colSpan={8}>Noch kein ML-Dataset erzeugt.</td></tr>}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>Gespeicherte Backtests</h2>
        <button onClick={loadRuns}>Aktualisieren</button>
        <table>
          <thead><tr><th align="left">Datum</th><th align="left">Asset</th><th align="left">TF</th><th align="left">Strategie</th><th align="right">Trades</th><th align="right">Return</th><th align="right">Winrate</th><th align="right">PF</th></tr></thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>{run.created_at}</td><td>{run.symbol}</td><td>{run.timeframe}</td><td>{run.strategy}</td><td align="right">{run.total_trades}</td><td align="right">{number(run.return_percent, 2)}%</td><td align="right">{number(run.win_rate_percent, 2)}%</td><td align="right">{run.profit_factor ?? '-'}</td>
              </tr>
            ))}
            {runs.length === 0 && <tr><td colSpan={8}>Keine gespeicherten Backtests gefunden.</td></tr>}
          </tbody>
        </table>
      </section>
    </div>
  );
}
