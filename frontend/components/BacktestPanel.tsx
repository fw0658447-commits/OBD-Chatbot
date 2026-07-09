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

function errorDetail(error: unknown) {
  return error instanceof Error ? error.message : String(error);
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
  const [busyLabel, setBusyLabel] = useState('');
  const [message, setMessage] = useState('');

  async function loadStrategies() {
    const data = await apiGet<{ items: StrategyDefinition[] }>('/api/backtest/strategies', { items: FALLBACK_STRATEGIES });
    setStrategies(data.items?.length ? data.items : FALLBACK_STRATEGIES);
  }

  async function runBusy(label: string, task: () => Promise<void>) {
    setLoading(true);
    setBusyLabel(label);
    try {
      await task();
    } catch (error) {
      setMessage(`Aktion fehlgeschlagen: ${errorDetail(error)}`);
    } finally {
      setBusyLabel('');
      setLoading(false);
    }
  }

  function validateTestSettings() {
    if (!symbol.trim()) {
      setMessage('Bitte ein Asset eingeben.');
      return false;
    }
    if (!Number.isFinite(limit) || limit < 120) {
      setMessage('Bitte mindestens 120 Kerzen wählen.');
      return false;
    }
    if (!Number.isFinite(capital) || capital < 1000) {
      setMessage('Bitte mindestens 1000 Startkapital eingeben.');
      return false;
    }
    return true;
  }

  async function runBacktest() {
    if (!validateTestSettings()) return;
    await runBusy('Test läuft', async () => {
      setMessage('');
      const cleanSymbol = symbol.trim();
      const data = await apiPost<BacktestResult>('/api/backtest/run', {
        symbol: cleanSymbol,
        timeframe,
        strategy_name: strategy,
        limit,
        initial_capital: capital,
        risk_per_trade: 0.01,
        persist: true
      }, { metrics: {}, trades: [], equity_curve: [] });
      setResult(data);
      setMessage(data.backtest_id ? `Backtest gespeichert: ${data.backtest_id}` : `Backtest im ${data.persistence ?? 'memory'}-Modus ausgeführt`);
      await loadRuns();
    });
  }

  async function runCompare() {
    if (!validateTestSettings()) return;
    await runBusy('Strategien werden verglichen', async () => {
      const data = await apiPost<any>('/api/backtest/compare', {
        symbols: ['BTC/USD', 'ETH/USD', 'AAPL', 'SPY'],
        timeframes: ['1h', '4h'],
        strategies: strategies.map((item) => item.name),
        limit,
        initial_capital: capital
      }, { items: [], ranking: [] });
      setCompare(data);
      setMessage(`${data.ranking?.length ?? 0} Vergleichsergebnisse geladen.`);
    });
  }

  async function runWalkForward() {
    if (!validateTestSettings()) return;
    await runBusy('Stabilität wird geprüft', async () => {
      const data = await apiPost<WalkForwardResult>('/api/backtest/walk-forward', {
        symbol: symbol.trim(),
        timeframe,
        strategy_name: strategy,
        limit: Math.max(limit, 720),
        initial_capital: capital,
        splits: 3
      }, { windows: [], metrics: {}, equity_curve: [] });
      setWalkForward(data);
      setMessage(`${data.windows?.length ?? 0} Stabilitätsfenster geprüft.`);
    });
  }


  async function runOptimization() {
    if (!validateTestSettings()) return;
    await runBusy('Parameter werden geprüft', async () => {
      const data = await apiPost<OptimizationResult>('/api/backtest/optimize', {
        symbol: symbol.trim(),
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
      setMessage(data.optimization_id ? `Optimierung gespeichert: ${data.optimization_id}` : `Optimierung im ${data.persistence ?? 'memory'}-Modus ausgeführt`);
    });
  }

  async function exportDataset() {
    if (!validateTestSettings()) return;
    await runBusy('ML-Daten werden erzeugt', async () => {
      const data = await apiPost<MLDatasetResult>('/api/backtest/ml-dataset', {
        symbols: [symbol.trim(), 'ETH/USD', 'AAPL', 'SPY'],
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
    });
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
  const compareRanking = compare.ranking ?? [];
  const optimizationRanking = optimization.ranking ?? [];
  const selectedStrategy = strategies.find((item) => item.name === strategy) ?? strategies[0] ?? FALLBACK_STRATEGIES[0];
  const hasBacktestResult = Boolean(result.strategy || result.strategy_label || result.backtest_id || result.final_equity);
  const returnPercent = Number(metrics.return_percent ?? 0);
  const wfReturnPercent = Number(wfMetrics.return_percent ?? 0);
  const testTone = !hasBacktestResult ? 'attention' : returnPercent >= 0 ? 'ready' : 'attention';
  const testTitle = !hasBacktestResult
    ? 'Ersten Testlauf starten'
    : returnPercent >= 0
      ? 'Testlauf positiv'
      : 'Testlauf im Minus';
  const bestCompare = compareRanking[0];
  const bestOptimization = optimization.best ?? optimizationRanking[0];
  const datasetRows = Number(mlDataset.row_count ?? 0);
  const messageLooksProblematic = message.toLowerCase().includes('fehl') || message.toLowerCase().includes('error') || message.toLowerCase().includes('problem');

  return (
    <div className="stack">
      {(message || busyLabel) && (
        <section className={`statusBanner ${messageLooksProblematic ? 'attention' : ''}`} role="status" aria-live="polite">
          <strong>{busyLabel || 'Status'}</strong>
          {message && <p>{message}</p>}
        </section>
      )}

      <section className={`testHero ${testTone === 'attention' ? 'attention' : ''}`}>
        <div>
          <p className="eyebrow">Strategie-Test</p>
          <h2>{testTitle}</h2>
          <p className="muted">Simuliere eine Strategie mit altem Kursverlauf. Das ist ein Test, keine Renditezusage.</p>
          <div className="botFactRow">
            <span>{symbol}</span>
            <span>{timeframe}</span>
            <span>{selectedStrategy.label}</span>
            <span>{number(capital, 0)} Startkapital</span>
          </div>
        </div>
        <div className="testActions">
          <button className="primary" onClick={runBacktest} disabled={loading}>Test starten</button>
          <button onClick={runCompare} disabled={loading}>Strategien vergleichen</button>
          <button onClick={runOptimization} disabled={loading}>Parameter prüfen</button>
        </div>
      </section>

      <section className="card">
        <details className="advancedSettings" open={!hasBacktestResult}>
          <summary>Test-Einstellungen ändern</summary>
          <div className="testFormGrid">
            <label>Asset
              <input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="BTC/USD, AAPL, SPY" />
            </label>
            <label>Zeitraum
              <select value={timeframe} onChange={(event) => setTimeframe(event.target.value)}>
                <option value="1m">1m</option>
                <option value="5m">5m</option>
                <option value="15m">15m</option>
                <option value="1h">1h</option>
                <option value="4h">4h</option>
                <option value="1D">1D</option>
              </select>
            </label>
            <label>Strategie
              <select value={strategy} onChange={(event) => setStrategy(event.target.value)}>
                {strategies.map((item) => <option key={item.name} value={item.name}>{item.label}</option>)}
              </select>
            </label>
            <label>Kerzen
              <input type="number" value={limit} onChange={(event) => setLimit(Number(event.target.value))} min={120} max={1500} />
            </label>
            <label>Startkapital
              <input type="number" value={capital} onChange={(event) => setCapital(Number(event.target.value))} min={1000} />
            </label>
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <button className="primary" onClick={runBacktest} disabled={loading}>Test starten</button>
            <button onClick={runCompare} disabled={loading}>Strategien vergleichen</button>
            <button onClick={runWalkForward} disabled={loading}>Stabilität prüfen</button>
            <button onClick={runOptimization} disabled={loading}>Parameter prüfen</button>
            <button onClick={exportDataset} disabled={loading}>ML-Daten erzeugen</button>
          </div>
        </details>
      </section>

      <section className="card">
        <div className="guidedHeader">
          <div>
            <p className="eyebrow">Strategien</p>
            <h2>Wählbare Testideen</h2>
            <p className="muted">Jede Karte beschreibt kurz, wann die Strategie typischerweise arbeitet.</p>
          </div>
          <span className="pill">{strategies.length} Strategien</span>
        </div>
        <div className="strategyGrid">
          {strategies.map((item) => (
            <article className={`strategyCard ${item.name === strategy ? 'active' : ''}`} key={item.name}>
              <h3>{item.label}</h3>
              <p className="muted">{item.family}</p>
              <p>{item.description}</p>
              <div className="botFactRow">
                <span>Confidence {item.min_confidence}</span>
                <span>Risiko max. {item.max_risk_score}</span>
              </div>
              <button className={item.name === strategy ? 'primary' : ''} onClick={() => setStrategy(item.name)}>{item.name === strategy ? 'Ausgewählt' : 'Auswählen'}</button>
            </article>
          ))}
        </div>
      </section>

      <div className="testSummaryGrid">
        <article className={`testMetricCard ${returnPercent < 0 ? 'attention' : ''}`}>
          <span className="muted">Einzel-Test</span>
          <strong className={returnPercent >= 0 ? 'good' : 'bad'}>{number(returnPercent, 2)}%</strong>
          <p>{metrics.total_trades ?? 0} Trades · {result.strategy_label ?? selectedStrategy.label}</p>
        </article>
        <article className="testMetricCard">
          <span className="muted">Qualität</span>
          <strong>{metrics.profit_factor ?? '-'}</strong>
          <p>PF · {number(metrics.win_rate_percent, 2)}% Treffer</p>
        </article>
        <article className={`testMetricCard ${wfReturnPercent < 0 ? 'attention' : ''}`}>
          <span className="muted">Stabilität</span>
          <strong className={wfReturnPercent >= 0 ? 'good' : 'bad'}>{number(wfReturnPercent, 2)}%</strong>
          <p>{wfMetrics.total_trades ?? 0} Walk-forward Trades</p>
        </article>
        <article className="testMetricCard">
          <span className="muted">Beste Variante</span>
          <strong>{bestCompare?.symbol ?? bestOptimization?.strategy ?? '-'}</strong>
          <p>{bestCompare ? `${bestCompare.timeframe} · ${bestCompare.strategy}` : bestOptimization ? `Score ${number(bestOptimization.score, 2)}` : 'Noch kein Vergleich'}</p>
        </article>
      </div>

      <section className="card">
        <h2>Equity-Kurve</h2>
        <EquityCurve points={result.equity_curve ?? []} />
      </section>

      <section className="card">
        <details className="advancedSettings">
          <summary>Einzelne Test-Trades anzeigen</summary>
          <div className="tableScroll">
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
          </div>
        </details>
      </section>

      <section className="card">
        <details className="advancedSettings">
          <summary>Strategie-/Asset-Vergleich anzeigen</summary>
          <div className="tableScroll">
            <table>
              <thead><tr><th align="left">Asset</th><th align="left">TF</th><th align="left">Strategie</th><th align="right">Trades</th><th align="right">Return</th><th align="right">Winrate</th><th align="right">PF</th><th align="right">DD</th></tr></thead>
              <tbody>
                {compareRanking.slice(0, 30).map((item: any) => (
                  <tr key={`${item.symbol}-${item.timeframe}-${item.strategy}`}>
                    <td>{item.symbol}</td><td>{item.timeframe}</td><td>{item.strategy}</td><td align="right">{item.metrics.total_trades}</td><td align="right">{number(item.metrics.return_percent, 2)}%</td><td align="right">{number(item.metrics.win_rate_percent, 2)}%</td><td align="right">{item.metrics.profit_factor ?? '-'}</td><td align="right">{number(item.metrics.max_drawdown_percent, 2)}%</td>
                  </tr>
                ))}
                {compareRanking.length === 0 && <tr><td colSpan={8}>Noch kein Vergleich ausgeführt.</td></tr>}
              </tbody>
            </table>
          </div>
        </details>
      </section>

      <section className="card">
        <details className="advancedSettings">
          <summary>Stabilitätsprüfung anzeigen</summary>
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
          <div className="tableScroll">
            <table>
              <thead><tr><th align="left">Fenster</th><th align="left">Start</th><th align="left">Ende</th><th align="right">Trades</th><th align="right">Return</th><th align="right">PF</th><th align="right">DD</th></tr></thead>
              <tbody>
                {(walkForward.windows ?? []).map((item) => (
                  <tr key={item.window}>
                    <td>{item.window}</td><td>{item.test_start_time}</td><td>{item.test_end_time}</td><td align="right">{item.metrics.total_trades}</td><td align="right">{number(item.metrics.return_percent, 2)}%</td><td align="right">{item.metrics.profit_factor ?? '-'}</td><td align="right">{number(item.metrics.max_drawdown_percent, 2)}%</td>
                  </tr>
                ))}
                {(walkForward.windows ?? []).length === 0 && <tr><td colSpan={7}>Noch kein Walk-forward-Test ausgeführt.</td></tr>}
              </tbody>
            </table>
          </div>
        </details>
      </section>


      <section className="card">
        <details className="advancedSettings">
          <summary>Parameter-Optimierung anzeigen</summary>
          <p className="muted">Testet mehrere Strategieparameter und sortiert nach Robustheit.</p>
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
          <div className="tableScroll">
            <table>
              <thead><tr><th align="right">Rang</th><th align="right">Score</th><th align="right">Trades</th><th align="right">Return</th><th align="right">PF</th><th align="right">DD</th><th align="left">Parameter</th></tr></thead>
              <tbody>
                {optimizationRanking.slice(0, 12).map((item, index) => (
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
                {optimizationRanking.length === 0 && <tr><td colSpan={7}>Noch keine Parameter-Optimierung ausgeführt.</td></tr>}
              </tbody>
            </table>
          </div>
        </details>
      </section>

      <section className="card">
        <details className="advancedSettings">
          <summary>ML-Trainingsdaten anzeigen</summary>
          <p className="muted">Erzeugt Daten für spätere Modelltests aus Kerzen, Indikatoren und Strategie-Signalen.</p>
          <div className="grid">
            <div>
              <div className="kpi">{datasetRows}</div>
              <p className="muted">Zeilen</p>
              <p>Features: {(mlDataset.feature_columns ?? []).join(', ') || '-'}</p>
              <p>Targets: {(mlDataset.target_columns ?? []).join(', ') || '-'}</p>
            </div>
            <div>
              <p>{mlDataset.note ?? 'Noch kein Dataset erzeugt.'}</p>
              {mlDataset.csv && <textarea readOnly value={mlDataset.csv.slice(0, 2500)} rows={10} />}
            </div>
          </div>
          <div className="tableScroll">
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
          </div>
        </details>
      </section>

      <section className="card">
        <details className="advancedSettings">
          <summary>Gespeicherte Tests anzeigen</summary>
          <button onClick={loadRuns}>Aktualisieren</button>
          <div className="tableScroll" style={{ marginTop: 12 }}>
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
          </div>
        </details>
      </section>
    </div>
  );
}
