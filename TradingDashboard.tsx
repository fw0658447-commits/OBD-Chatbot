'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiDelete, apiGet, apiPatch, apiPost, q } from '../lib/api';
import type { AssetAnalysis, Quote, SearchResult, StrategyDefinition } from '../types/trading';
import { BotControls } from './BotControls';
import { BotStatusCard } from './BotStatusCard';
import { CandleChart } from './CandleChart';
import { BacktestPanel } from './BacktestPanel';
import { MLPanel } from './MLPanel';
import { EquityCurve } from './EquityCurve';
import { MonitoringPanel } from './MonitoringPanel';

type View = 'dashboard' | 'analyse' | 'watchlist' | 'bot' | 'monitoring' | 'backtest' | 'ml';

type BotStatus = {
  status: string;
  mode: string;
  live_trading_enabled: boolean;
  max_risk_per_trade: number;
  max_daily_loss: number;
  max_open_trades: number;
  min_crv: number;
  min_confidence_score: number;
  max_risk_score: number;
  supported_decision_modes?: string[];
  default_decision_mode?: string;
};

type WatchlistItem = {
  id?: string;
  symbol: string;
  name?: string;
  note?: string | null;
  alert_price?: number | null;
  quote?: Quote | null;
};

const EMPTY_BOT: BotStatus = {
  status: 'backend_not_reachable',
  mode: 'paper',
  live_trading_enabled: false,
  max_risk_per_trade: 0.01,
  max_daily_loss: 0.02,
  max_open_trades: 3,
  min_crv: 2,
  min_confidence_score: 65,
  max_risk_score: 70,
  supported_decision_modes: ['rule', 'ml', 'ensemble'],
  default_decision_mode: 'rule'
};

const EMPTY_ANALYSIS: AssetAnalysis = {
  symbol: 'BTC/USD',
  timeframe: '1h',
  quote: { symbol: 'BTC/USD', price: 0, provider: 'none' },
  candles: [],
  indicators: {},
  prediction: {
    symbol: 'BTC/USD',
    timeframe: '1h',
    horizon: 'next_1h',
    direction: 'neutral',
    probability_long: 0,
    probability_short: 0,
    probability_neutral: 1,
    confidence_score: 0,
    risk_score: 0,
    model_version: 'none'
  },
  signal_preview: null,
  persistence: 'memory'
};

function percent(value: unknown) {
  return `${(Number(value ?? 0) * 100).toFixed(1)}%`;
}

function number(value: unknown, digits = 2) {
  return Number(value ?? 0).toFixed(digits);
}

export function TradingDashboard() {
  const [view, setView] = useState<View>('dashboard');
  const [bot, setBot] = useState<BotStatus>(EMPTY_BOT);
  const [symbol, setSymbol] = useState('BTC/USD');
  const [timeframe, setTimeframe] = useState('1h');
  const [strategyName, setStrategyName] = useState('trend_atr_v0.7');
  const [decisionMode, setDecisionMode] = useState('rule');
  const [modelId, setModelId] = useState('');
  const [modelHealth, setModelHealth] = useState<any>({});
  const [performanceByMode, setPerformanceByMode] = useState<any[]>([]);
  const [strategies, setStrategies] = useState<StrategyDefinition[]>([]);
  const [analysis, setAnalysis] = useState<AssetAnalysis>(EMPTY_ANALYSIS);
  const [overview, setOverview] = useState<Quote[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [search, setSearch] = useState('btc');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [portfolio, setPortfolio] = useState<any>({ positions: [] });
  const [performance, setPerformance] = useState<any>({});
  const [signals, setSignals] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [riskEvents, setRiskEvents] = useState<any[]>([]);
  const [botConfig, setBotConfig] = useState<any>({});
  const [schedulerStatus, setSchedulerStatus] = useState<any>({});
  const [schedulerRuns, setSchedulerRuns] = useState<any[]>([]);
  const [decisionAudits, setDecisionAudits] = useState<any[]>([]);
  const [equityCurve, setEquityCurve] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const botCanTrade = useMemo(() => !bot.live_trading_enabled && bot.mode === 'paper', [bot]);

  async function refreshCore() {
    const [botStatus, overviewData, watchlistData, snapshotData, signalsData, ordersData, riskData, strategyData, modelHealthData, modePerfData, configData, schedulerData, schedulerRunsData, auditData, equityData] = await Promise.all([
      apiGet<BotStatus>('/api/bot/status', EMPTY_BOT),
      apiGet<{ items: Quote[] }>('/api/market/overview', { items: [] }),
      apiGet<{ items: WatchlistItem[] }>('/api/watchlist', { items: [] }),
      apiGet<any>('/api/bot/portfolio-snapshot', { portfolio: { positions: [] }, performance: {} }),
      apiGet<any>('/api/bot/signals?limit=10', { items: [] }),
      apiGet<any>('/api/bot/orders?limit=10', { items: [] }),
      apiGet<any>('/api/bot/risk-events?limit=5', { items: [] }),
      apiGet<{ items: StrategyDefinition[] }>('/api/backtest/strategies', { items: [] }),
      apiGet<any>('/api/bot/model-health', {}),
      apiGet<any>('/api/bot/performance-by-mode', { items: [] }),
      apiGet<any>('/api/bot/config', {}),
      apiGet<any>('/api/bot/scheduler/status', {}),
      apiGet<any>('/api/bot/scheduler/runs?limit=5', { items: [] }),
      apiGet<any>('/api/bot/decision-audits?limit=20', { items: [] }),
      apiGet<any>('/api/bot/equity-curve', { items: [] })
    ]);
    setBot(botStatus);
    setOverview(overviewData.items ?? []);
    setWatchlist(watchlistData.items ?? []);
    setPortfolio(snapshotData.portfolio ?? { positions: [] });
    setPerformance(snapshotData.performance ?? {});
    setSignals(signalsData.items ?? []);
    setOrders(ordersData.items ?? []);
    setRiskEvents(riskData.items ?? []);
    if ((strategyData.items ?? []).length) setStrategies(strategyData.items ?? []);
    setModelHealth(modelHealthData ?? {});
    setPerformanceByMode(modePerfData.items ?? []);
    setBotConfig(configData ?? {});
    setSchedulerStatus(schedulerData ?? {});
    setSchedulerRuns(schedulerRunsData.items ?? []);
    setDecisionAudits(auditData.items ?? []);
    setEquityCurve(equityData.items ?? []);
  }

  async function loadAnalysis(nextSymbol = symbol, nextTimeframe = timeframe, nextStrategy = strategyName) {
    setLoading(true);
    setMessage('');
    const data = await apiGet<AssetAnalysis>(
      `/api/market/analysis?symbol=${q(nextSymbol)}&timeframe=${q(nextTimeframe)}&strategy_name=${q(nextStrategy)}&limit=220`,
      { ...EMPTY_ANALYSIS, symbol: nextSymbol, timeframe: nextTimeframe }
    );
    setAnalysis(data);
    setSymbol(data.symbol ?? nextSymbol);
    setTimeframe(data.timeframe ?? nextTimeframe);
    setLoading(false);
  }

  async function runSearch() {
    const data = await apiGet<{ results: SearchResult[] }>(`/api/market/assets/search?q=${q(search)}`, { results: [] });
    setSearchResults(data.results ?? []);
  }

  async function addToWatchlist(nextSymbol = symbol) {
    const result = await apiPost('/api/watchlist', { symbol: nextSymbol, note: 'Aus Analyse hinzugefuegt' }, { status: 'error' });
    setMessage(`Watchlist: ${(result as any).status ?? 'unbekannt'}`);
    await refreshCore();
  }

  async function removeFromWatchlist(nextSymbol: string) {
    await apiDelete(`/api/watchlist/${q(nextSymbol)}`, { status: 'error' });
    await refreshCore();
  }

  async function runBotCycle(nextSymbol = symbol) {
    setLoading(true);
    const result = await apiPost('/api/bot/run-cycle', {
      symbol: nextSymbol,
      timeframe,
      portfolio_value: Number(portfolio.current_equity ?? 10000),
      open_trades_count: Number(portfolio.open_orders_count ?? 0),
      daily_pnl_percent: 0,
      strategy_name: strategyName,
      decision_mode: decisionMode,
      model_id: modelId || null,
      min_ml_probability: 0.52,
      min_model_profit_factor: 1.0,
      min_model_win_rate: 45,
      allow_degraded_fallback: true
    }, { status: 'error' });
    setMessage(`Bot-Cycle: ${(result as any).status ?? 'unbekannt'}`);
    await Promise.all([refreshCore(), loadAnalysis(nextSymbol, timeframe)]);
    setLoading(false);
  }

  async function evaluateOrders() {
    setLoading(true);
    const result = await apiPost('/api/bot/evaluate-open-orders', {}, { status: 'error' });
    setMessage(`Order-Auswertung: ${(result as any).status ?? 'ok'}`);
    await refreshCore();
    setLoading(false);
  }

  async function saveBotConfig(patch: any) {
    setLoading(true);
    const result = await apiPatch('/api/bot/config', patch, { status: 'error' });
    setMessage(`Konfiguration gespeichert: ${(result as any).persistence ?? (result as any).status ?? 'ok'}`);
    await refreshCore();
    setLoading(false);
  }

  async function schedulerAction(action: 'start' | 'stop' | 'run-once') {
    setLoading(true);
    const result = await apiPost(`/api/bot/scheduler/${action}`, {}, { status: 'error' });
    setMessage(`Scheduler ${action}: ${(result as any).status ?? 'ok'}`);
    await refreshCore();
    setLoading(false);
  }

  async function resetKillSwitch() {
    setLoading(true);
    const result = await apiPost('/api/bot/kill-switch/reset', {}, { status: 'error' });
    setMessage(`Kill-Switch Reset: ${(result as any).persistence ?? (result as any).status ?? 'ok'}`);
    await refreshCore();
    setLoading(false);
  }

  useEffect(() => {
    refreshCore();
    loadAnalysis('BTC/USD', '1h');
  }, []);

  return (
    <main>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <div>
          <h1>Trading Cockpit MVP v1.2</h1>
          <p className="muted">Validierungs- und Monitoring-Version mit Release-Gates, Alerts, Daily Report und optionaler harter Bot-Sperre. Live-Trading bleibt gesperrt.</p>
        </div>
        <div className="code muted">API: http://localhost:8000</div>
      </div>

      <nav className="tabs">
        {(['dashboard', 'analyse', 'watchlist', 'bot', 'monitoring', 'backtest', 'ml'] as View[]).map((item) => (
          <button key={item} onClick={() => setView(item)} className={`tab ${view === item ? 'active' : ''}`}>
            {item === 'dashboard' ? 'Dashboard' : item === 'analyse' ? 'Analyse' : item === 'watchlist' ? 'Watchlist' : item === 'bot' ? 'Bot Center' : item === 'monitoring' ? 'Monitoring' : item === 'backtest' ? 'Backtesting' : 'ML-Modell'}
          </button>
        ))}
      </nav>

      {message && <section className="card" style={{ marginBottom: 16 }}>{message}</section>}

      {view === 'dashboard' && (
        <div className="stack">
          <div className="grid">
            <section className="card">
              <h2>Paper Portfolio</h2>
              <div className="kpi">{number(portfolio.current_equity, 2)}</div>
              <p className="muted">Equity</p>
              <p>Cash: {number(portfolio.cash_balance, 2)}</p>
              <p>Realisierte P/L: {number(portfolio.total_realized_pnl, 2)}</p>
              <p>Unrealisierte P/L: {number(portfolio.total_unrealized_pnl, 2)}</p>
            </section>

            <section className="card">
              <h2>Bot Performance</h2>
              <div className="kpi">{number(performance.win_rate_percent, 1)}%</div>
              <p className="muted">Trefferquote</p>
              <p>Geschlossene Trades: {performance.closed_orders ?? 0}</p>
              <p>Profit Factor: {performance.profit_factor ?? '-'}</p>
              <p>Expectancy/Trade: {number(performance.expectancy_per_trade, 2)}</p>
            </section>

            <BotStatusCard bot={bot as any} />
          </div>

          <section className="card">
            <h2>Marktüberblick</h2>
            <table>
              <thead><tr><th align="left">Asset</th><th align="right">Kurs</th><th align="right">Tag %</th><th align="left">Provider</th><th /></tr></thead>
              <tbody>
                {overview.map((item) => (
                  <tr key={item.symbol}>
                    <td>{item.symbol}</td>
                    <td align="right">{item.error ? '-' : number(item.price, item.symbol.includes('/') && item.price < 10 ? 5 : 2)}</td>
                    <td align="right" className={Number(item.change_percent ?? 0) >= 0 ? 'good' : 'bad'}>{number(item.change_percent, 2)}%</td>
                    <td>{item.provider ?? '-'}</td>
                    <td align="right"><button onClick={() => { setView('analyse'); loadAnalysis(item.symbol); }}>Analysieren</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      )}

      {view === 'analyse' && (
        <div className="stack">
          <section className="card">
            <h2>Asset-Analyse</h2>
            <div className="row">
              <input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="BTC/USD, AAPL, EUR/USD" />
              <select value={timeframe} onChange={(event) => { setTimeframe(event.target.value); loadAnalysis(symbol, event.target.value); }}>
                <option value="1m">1m</option>
                <option value="5m">5m</option>
                <option value="15m">15m</option>
                <option value="1h">1h</option>
                <option value="4h">4h</option>
                <option value="1D">1D</option>
              </select>
              <select value={strategyName} onChange={(event) => { setStrategyName(event.target.value); loadAnalysis(symbol, timeframe, event.target.value); }}>
                {(strategies.length ? strategies : [{ name: 'trend_atr_v0.7', label: 'Trendfolge ATR' } as any]).map((item) => <option key={item.name} value={item.name}>{item.label}</option>)}
              </select>
              <button className="primary" onClick={() => loadAnalysis(symbol, timeframe)} disabled={loading}>Analyse laden</button>
              <button onClick={() => addToWatchlist(symbol)}>Zur Watchlist</button>
              <button onClick={() => runBotCycle(symbol)} disabled={loading || !botCanTrade}>Paper-Bot testen</button>
            </div>
          </section>

          <div className="grid">
            <section className="card">
              <h2>{analysis.symbol}</h2>
              <div className="kpi">{number(analysis.quote?.price, analysis.symbol.includes('/') && Number(analysis.quote?.price) < 10 ? 5 : 2)}</div>
              <p className={Number(analysis.quote?.change_percent ?? 0) >= 0 ? 'good' : 'bad'}>{number(analysis.quote?.change_percent, 2)}% Tagesveraenderung</p>
              <p className="muted">Provider: {analysis.quote?.provider ?? '-'}</p>
            </section>

            <section className="card">
              <h2>KI-Prognose</h2>
              <p><strong>Richtung:</strong> {analysis.prediction.direction}</p>
              <p>Long: {percent(analysis.prediction.probability_long)}</p>
              <p>Short: {percent(analysis.prediction.probability_short)}</p>
              <p>Neutral: {percent(analysis.prediction.probability_neutral)}</p>
              <p>Confidence: {number(analysis.prediction.confidence_score, 0)} / 100</p>
              <p>Risk Score: {number(analysis.prediction.risk_score, 0)} / 100</p>
            </section>

            <section className="card">
              <h2>Signal-Vorschau</h2>
              {analysis.signal_preview ? (
                <>
                  <p><strong>{analysis.signal_preview.signal_type.toUpperCase()}</strong> Score {number(analysis.signal_preview.signal_score, 0)}</p>
                  <p>Entry: {number(analysis.signal_preview.entry_price, 4)}</p>
                  <p>Stop: {number(analysis.signal_preview.stop_loss, 4)}</p>
                  <p>Ziel: {number(analysis.signal_preview.take_profit, 4)}</p>
                  <p>CRV: {number(analysis.signal_preview.crv, 2)}</p>
                  <p>Strategie: {analysis.signal_preview.strategy ?? analysis.strategy_name ?? strategyName}</p>
                </>
              ) : <p>Kein handelbares Signal nach aktueller Strategie.</p>}
            </section>
          </div>

          <CandleChart candles={analysis.candles ?? []} />

          <div className="grid">
            <section className="card">
              <h2>Technische Indikatoren</h2>
              <table>
                <tbody>
                  {Object.entries(analysis.indicators ?? {}).map(([key, value]) => (
                    <tr key={key}><td>{key}</td><td align="right">{typeof value === 'number' ? number(value, 4) : String(value)}</td></tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="card">
              <h2>Asset-Suche</h2>
              <div className="row">
                <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="z. B. apple, btc, gold" />
                <button onClick={runSearch}>Suchen</button>
              </div>
              <table>
                <tbody>
                  {searchResults.map((item) => (
                    <tr key={`${item.symbol}-${item.exchange ?? ''}`}>
                      <td><strong>{item.symbol}</strong><br /><span className="muted">{item.name}</span></td>
                      <td>{item.asset_type}</td>
                      <td align="right"><button onClick={() => { setSymbol(item.symbol); loadAnalysis(item.symbol, timeframe); }}>Laden</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>
        </div>
      )}

      {view === 'watchlist' && (
        <section className="card">
          <h2>Watchlist</h2>
          <div className="row" style={{ marginBottom: 12 }}>
            <input value={symbol} onChange={(event) => setSymbol(event.target.value)} />
            <button className="primary" onClick={() => addToWatchlist(symbol)}>Hinzufuegen</button>
            <button onClick={refreshCore}>Aktualisieren</button>
          </div>
          <table>
            <thead><tr><th align="left">Asset</th><th align="right">Kurs</th><th align="right">Tag %</th><th align="left">Notiz</th><th /></tr></thead>
            <tbody>
              {watchlist.map((item) => (
                <tr key={item.id ?? item.symbol}>
                  <td>{item.symbol}</td>
                  <td align="right">{number(item.quote?.price, item.symbol.includes('/') && Number(item.quote?.price) < 10 ? 5 : 2)}</td>
                  <td align="right" className={Number(item.quote?.change_percent ?? 0) >= 0 ? 'good' : 'bad'}>{number(item.quote?.change_percent, 2)}%</td>
                  <td>{item.note ?? '-'}</td>
                  <td align="right" className="row" style={{ justifyContent: 'flex-end' }}>
                    <button onClick={() => { setView('analyse'); loadAnalysis(item.symbol); }}>Analysieren</button>
                    <button onClick={() => removeFromWatchlist(item.symbol)}>Entfernen</button>
                  </td>
                </tr>
              ))}
              {watchlist.length === 0 && <tr><td colSpan={5}>Noch keine Watchlist-Eintraege.</td></tr>}
            </tbody>
          </table>
        </section>
      )}

      {view === 'bot' && (
        <div className="stack">
          <div className="grid">
            <BotStatusCard bot={bot as any} />
            <section className="card"><BotControls /></section>
            <section className="card">
              <h2>Direktaktionen</h2>
              <div className="stack">
                <label>Bot-Entscheidung</label>
                <select value={decisionMode} onChange={(event) => setDecisionMode(event.target.value)}>
                  <option value="rule">Rule-only</option>
                  <option value="ml">ML-Filter</option>
                  <option value="ensemble">Ensemble</option>
                </select>
                <input value={modelId} onChange={(event) => setModelId(event.target.value)} placeholder="optional model_id; leer = neuestes Modell" />
                <button className="primary" onClick={() => runBotCycle(symbol)} disabled={loading || !botCanTrade}>Bot-Cycle fuer {symbol}</button>
                <button onClick={evaluateOrders} disabled={loading}>Offene Orders auswerten</button>
              </div>
            </section>
          </div>

          <section className="card">
            <h2>v1.0 Bot-Konfiguration</h2>
            <div className="grid">
              <label>Bot aktiv
                <select value={String(botConfig.bot_enabled ?? false)} onChange={(event) => saveBotConfig({ bot_enabled: event.target.value === 'true' })}>
                  <option value="false">Nein</option>
                  <option value="true">Ja, Paper-only</option>
                </select>
              </label>
              <label>Scheduler-Intervall Sekunden
                <input value={botConfig.scheduler_interval_seconds ?? 60} onChange={(event) => setBotConfig({ ...botConfig, scheduler_interval_seconds: Number(event.target.value) })} />
              </label>
              <label>Symbole
                <input value={(botConfig.symbols ?? []).join(',')} onChange={(event) => setBotConfig({ ...botConfig, symbols: event.target.value.split(',').map((x: string) => x.trim()).filter(Boolean) })} />
              </label>
              <label>Timeframes
                <input value={(botConfig.timeframes ?? []).join(',')} onChange={(event) => setBotConfig({ ...botConfig, timeframes: event.target.value.split(',').map((x: string) => x.trim()).filter(Boolean) })} />
              </label>
              <label>Risiko pro Trade
                <input value={botConfig.max_risk_per_trade ?? 0.01} onChange={(event) => setBotConfig({ ...botConfig, max_risk_per_trade: Number(event.target.value) })} />
              </label>
              <label>Max. Tagesverlust
                <input value={botConfig.max_daily_loss ?? 0.02} onChange={(event) => setBotConfig({ ...botConfig, max_daily_loss: Number(event.target.value) })} />
              </label>
              <label>Max. offene Trades
                <input value={botConfig.max_open_trades ?? 3} onChange={(event) => setBotConfig({ ...botConfig, max_open_trades: Number(event.target.value) })} />
              </label>
              <label>Mindest-CRV
                <input value={botConfig.min_crv ?? 2} onChange={(event) => setBotConfig({ ...botConfig, min_crv: Number(event.target.value) })} />
              </label>
              <label>Validation Gate erzwingen
                <select value={String(botConfig.enforce_validation_gate ?? false)} onChange={(event) => setBotConfig({ ...botConfig, enforce_validation_gate: event.target.value === 'true' })}>
                  <option value="false">Nein</option>
                  <option value="true">Ja, Bot blockieren wenn nicht released</option>
                </select>
              </label>
              <label>Min. geschlossene Trades
                <input value={botConfig.min_closed_trades_for_release ?? 100} onChange={(event) => setBotConfig({ ...botConfig, min_closed_trades_for_release: Number(event.target.value) })} />
              </label>
              <label>Min. Profit Factor
                <input value={botConfig.min_profit_factor_for_release ?? 1.15} onChange={(event) => setBotConfig({ ...botConfig, min_profit_factor_for_release: Number(event.target.value) })} />
              </label>
              <label>Max. Drawdown %
                <input value={botConfig.max_drawdown_percent_for_release ?? 12} onChange={(event) => setBotConfig({ ...botConfig, max_drawdown_percent_for_release: Number(event.target.value) })} />
              </label>
            </div>
            <div className="row" style={{ marginTop: 12 }}>
              <button className="primary" onClick={() => saveBotConfig(botConfig)}>Konfiguration speichern</button>
              <button onClick={() => schedulerAction('start')} disabled={loading}>Scheduler starten</button>
              <button onClick={() => schedulerAction('stop')} disabled={loading}>Scheduler stoppen</button>
              <button onClick={() => schedulerAction('run-once')} disabled={loading}>Scheduler einmal ausfuehren</button>
              <button onClick={resetKillSwitch} disabled={loading}>Kill-Switch zuruecksetzen</button>
            </div>
            <p className="muted">Scheduler: {schedulerStatus.status ?? 'unbekannt'} | Persistence: {botConfig.persistence ?? 'memory'} | Kill-Switch: {String(botConfig.kill_switch_active ?? false)}</p>
          </section>

          <section className="card">
            <h2>Equity-Kurve</h2>
            <EquityCurve points={(equityCurve ?? []).map((item: any, index: number) => ({ timestamp: item.timestamp ?? `P${index}`, equity: Number(item.equity ?? 0), event: item.symbol }))} />
          </section>

          <section className="card">
            <h2>Decision-Audits & Scheduler-Laeufe</h2>
            <div className="grid">
              <table>
                <thead><tr><th align="left">Zeit</th><th align="left">Asset</th><th align="left">Modus</th><th align="left">Erlaubt</th><th align="left">Grund</th></tr></thead>
                <tbody>
                  {decisionAudits.map((item) => <tr key={item.id}><td>{String(item.created_at ?? '').slice(0, 19)}</td><td>{item.symbol}</td><td>{item.decision_mode}</td><td>{String(item.allowed)}</td><td>{item.reason}</td></tr>)}
                  {decisionAudits.length === 0 && <tr><td colSpan={5}>Noch keine Decision-Audits.</td></tr>}
                </tbody>
              </table>
              <table>
                <thead><tr><th align="left">Zeit</th><th align="left">Quelle</th><th align="left">Status</th><th align="left">Symbole</th></tr></thead>
                <tbody>
                  {schedulerRuns.map((item) => <tr key={item.id ?? item.created_at}><td>{String(item.created_at ?? '').slice(0, 19)}</td><td>{item.source}</td><td>{item.status}</td><td>{(item.symbols ?? []).join(', ')}</td></tr>)}
                  {schedulerRuns.length === 0 && <tr><td colSpan={4}>Noch keine Scheduler-Laeufe.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card">
            <h2>ML-/Ensemble-Status</h2>
            <p>Status: {modelHealth.status ?? 'unbekannt'}</p>
            <p>Health: {modelHealth.health?.healthy ? 'ok' : (modelHealth.health?.reason ?? modelHealth.reason ?? 'kein Modell')}</p>
            <p>Aktuelles Modell: {modelHealth.health?.model_id ?? modelHealth.selected_model?.model_id ?? '-'}</p>
            <h3>Performance nach Entscheidungsmodus</h3>
            <table>
              <thead><tr><th align="left">Modus</th><th align="right">Orders</th><th align="right">Winrate</th><th align="right">PF</th><th align="right">P/L</th></tr></thead>
              <tbody>
                {performanceByMode.map((item) => <tr key={item.decision_mode}><td>{item.decision_mode}</td><td align="right">{item.total_orders}</td><td align="right">{number(item.win_rate_percent, 1)}%</td><td align="right">{item.profit_factor ?? '-'}</td><td align="right">{number(item.total_realized_pnl, 2)}</td></tr>)}
                {performanceByMode.length === 0 && <tr><td colSpan={5}>Noch keine Modus-Auswertung.</td></tr>}
              </tbody>
            </table>
          </section>

          <section className="card">
            <h2>Offene Positionen</h2>
            <table>
              <thead><tr><th align="left">Asset</th><th align="left">Richtung</th><th align="right">Entry</th><th align="right">Aktuell</th><th align="right">Stop</th><th align="right">Ziel</th><th align="right">Unreal. P/L</th></tr></thead>
              <tbody>
                {(portfolio.positions ?? []).map((item: any) => (
                  <tr key={item.id}><td>{item.symbol}</td><td>{item.side}</td><td align="right">{number(item.entry_price, 4)}</td><td align="right">{number(item.current_price, 4)}</td><td align="right">{number(item.stop_loss, 4)}</td><td align="right">{number(item.take_profit, 4)}</td><td align="right">{number(item.unrealized_pnl_amount, 2)}</td></tr>
                ))}
                {(portfolio.positions ?? []).length === 0 && <tr><td colSpan={7}>Keine offenen Paper-Positionen.</td></tr>}
              </tbody>
            </table>
          </section>

          <section className="card">
            <h2>Letzte Orders</h2>
            <table>
              <thead><tr><th align="left">Asset</th><th align="left">Richtung</th><th align="left">Modus</th><th align="right">Entry</th><th align="right">Stop</th><th align="right">Ziel</th><th align="right">P/L</th><th align="left">Status</th></tr></thead>
              <tbody>
                {orders.map((item) => <tr key={item.id}><td>{item.symbol}</td><td>{item.side}</td><td>{item.decision_mode ?? '-'}</td><td align="right">{number(item.entry_price, 4)}</td><td align="right">{number(item.stop_loss, 4)}</td><td align="right">{number(item.take_profit, 4)}</td><td align="right">{item.pnl_amount == null ? '-' : number(item.pnl_amount, 2)}</td><td>{item.status}</td></tr>)}
              </tbody>
            </table>
          </section>

          <section className="card">
            <h2>Letzte Signale & Risiko-Events</h2>
            <div className="grid">
              <table>
                <tbody>{signals.map((item) => <tr key={item.id}><td>{item.symbol}</td><td>{item.signal_type}</td><td>{number(item.signal_score, 0)}</td><td>{item.status}</td></tr>)}</tbody>
              </table>
              <ul>{riskEvents.map((item) => <li key={item.id}>{item.severity}: {item.message}</li>)}</ul>
            </div>
          </section>
        </div>
      )}


      {view === 'monitoring' && (
        <MonitoringPanel />
      )}


      {view === 'backtest' && (
        <BacktestPanel defaultSymbol={symbol} defaultTimeframe={timeframe} />
      )}


      {view === 'ml' && (
        <MLPanel defaultSymbol={symbol} defaultTimeframe={timeframe} />
      )}
    </main>
  );
}
