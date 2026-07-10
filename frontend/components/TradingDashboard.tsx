'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiDelete, apiGet, apiPatch, apiPost, q, getApiDisplayUrl } from '../lib/api';
import type { AssetAnalysis, InstrumentLookupResult, InternetAnalysisResult, Quote, SearchResult, StrategyDefinition, TradeRecommendation } from '../types/trading';
import { BotStatusCard } from './BotStatusCard';
import { CandleChart } from './CandleChart';
import { BacktestPanel } from './BacktestPanel';
import { MLPanel } from './MLPanel';
import { EquityCurve } from './EquityCurve';
import { MonitoringPanel } from './MonitoringPanel';

type View = 'dashboard' | 'analyse' | 'watchlist' | 'portfolio' | 'intelligence' | 'setup' | 'bot' | 'monitoring' | 'backtest' | 'ml';

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
  target_price?: number | null;
  quote?: Quote | null;
};

type AccountConfirmation = {
  title: string;
  detail: string;
  meta: string;
  tone: 'good' | 'bad' | 'neutral';
} | null;

const DEFAULT_ACCOUNT_ASSET_GROUPS = [
  {
    label: 'Krypto',
    symbols: ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD', 'XRP/USD', 'ADA/USD', 'DOGE/USD', 'AVAX/USD', 'LINK/USD', 'DOT/USD', 'LTC/USD', 'BCH/USD']
  },
  {
    label: 'Aktien USA',
    symbols: ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'GOOGL', 'META', 'AMD', 'NFLX', 'JPM', 'V', 'MA', 'DIS', 'WMT', 'COST', 'KO', 'PEP', 'CRM', 'ORCL']
  },
  {
    label: 'ETFs',
    symbols: ['SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VOO', 'ARKK', 'TLT', 'GLD', 'SLV', 'USO']
  },
  {
    label: 'Forex',
    symbols: ['EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD', 'NZD/USD', 'USD/CAD', 'EUR/GBP', 'EUR/JPY', 'GBP/JPY']
  },
  {
    label: 'Rohstoffe',
    symbols: ['XAU/USD', 'XAG/USD', 'WTI/USD', 'BRENT/USD', 'COPPER/USD', 'NATGAS/USD']
  }
];

const DEFAULT_ACCOUNT_ASSETS = DEFAULT_ACCOUNT_ASSET_GROUPS.flatMap((group) => group.symbols);
const ACCOUNT_TRADE_AMOUNTS = [250, 500, 1000, 2500, 5000, 10000];

const VIEW_LABELS: Record<View, string> = {
  dashboard: 'Start',
  analyse: 'Analyse',
  watchlist: 'Watchlist',
  portfolio: 'Konto',
  intelligence: 'Recherche',
  setup: 'Setup',
  bot: 'Bot',
  monitoring: 'Risiko',
  backtest: 'Tests',
  ml: 'Modelle'
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

function shortTime(value: unknown) {
  const raw = String(value ?? '');
  return raw ? raw.slice(0, 19).replace('T', ' ') : '-';
}

function positiveNumber(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function optionalNumber(value: string) {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function errorDetail(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

function apiErrorDetail(result: any) {
  return result?.error ? String(result.detail ?? 'Aktion wurde blockiert.') : '';
}

function apiFailureDetail(result: any, successStatuses: string[]) {
  const transportError = apiErrorDetail(result);
  if (transportError) return transportError;
  const status = String(result?.status ?? 'unbekannt');
  if (successStatuses.includes(status)) return '';
  if (status === 'not_found') return 'Position wurde nicht gefunden.';
  if (status === 'not_open') return 'Position ist nicht mehr offen.';
  return String(result?.detail ?? result?.reason ?? `Unerwarteter Status: ${status}`);
}

function simpleStatus(value: unknown) {
  if (value === 'online') return 'online';
  if (value === 'offline') return 'nicht verbunden';
  if (value === 'paper_only') return 'Paper-Trading';
  if (value === 'backend_not_reachable') return 'nicht erreichbar';
  return String(value ?? '-').replaceAll('_', ' ');
}

function setupStatusLabel(status: unknown) {
  if (status === 'ready') return 'Bereit';
  if (status === 'optional') return 'Optional';
  if (status === 'attention') return 'Prüfen';
  return 'Hinweis';
}

function setupStatusClass(status: unknown) {
  if (status === 'ready') return 'goodPill';
  if (status === 'optional') return 'warnPill';
  return 'badPill';
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
  const [systemStatus, setSystemStatus] = useState<any>({});
  const [cashLedger, setCashLedger] = useState<any[]>([]);
  const [setupGuide, setSetupGuide] = useState<any>({ items: [] });
  const [depositAmount, setDepositAmount] = useState('10000');
  const [withdrawAmount, setWithdrawAmount] = useState('1000');
  const [resetBalance, setResetBalance] = useState('10000');
  const [accountConfirmation, setAccountConfirmation] = useState<AccountConfirmation>(null);
  const [manualNotional, setManualNotional] = useState('1000');
  const [manualSide, setManualSide] = useState<'long' | 'short'>('long');
  const [manualStop, setManualStop] = useState('');
  const [manualTakeProfit, setManualTakeProfit] = useState('');
  const [watchNote, setWatchNote] = useState('');
  const [watchAlert, setWatchAlert] = useState('');
  const [watchTarget, setWatchTarget] = useState('');
  const [search, setSearch] = useState('btc');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [identifierQuery, setIdentifierQuery] = useState('US0378331005');
  const [identifierType, setIdentifierType] = useState('auto');
  const [identifierResult, setIdentifierResult] = useState<InstrumentLookupResult | null>(null);
  const [internetAnalysis, setInternetAnalysis] = useState<InternetAnalysisResult | null>(null);
  const [recommendation, setRecommendation] = useState<TradeRecommendation | null>(null);
  const [includeInternet, setIncludeInternet] = useState(true);
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
  const [busyLabel, setBusyLabel] = useState('');
  const [message, setMessage] = useState('');
  const [apiDisplay, setApiDisplay] = useState('Codespaces Proxy: /api/backend');
  const [diagnostics, setDiagnostics] = useState<any>({});

  const botCanTrade = useMemo(() => !bot.live_trading_enabled && bot.mode === 'paper', [bot]);
  const safeMode = !bot.live_trading_enabled && bot.mode === 'paper';
  const marketOnline = systemStatus.market_data?.status === 'online';
  const backendOnline = systemStatus.backend === 'online';
  const databaseOnline = systemStatus.database === 'online';
  const localFileStorage = Boolean(systemStatus.local_persistence?.enabled);
  const storageReady = databaseOnline || localFileStorage;
  const storageLabel = databaseOnline ? 'Datenbank aktiv' : localFileStorage ? 'Lokal gespeichert' : 'Nur dieser Testlauf';

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

  async function refreshCore() {
    const [botStatus, overviewData, watchlistData, snapshotData, signalsData, ordersData, riskData, strategyData, modelHealthData, modePerfData, configData, schedulerData, schedulerRunsData, auditData, equityData, statusData, ledgerData, setupData] = await Promise.all([
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
      apiGet<any>('/api/bot/equity-curve', { items: [] }),
      apiGet<any>('/api/ops/status', {}),
      apiGet<any>('/api/portfolio/paper/cash-ledger?limit=20', { items: [] }),
      apiGet<any>('/api/ops/setup-guide', { status: 'attention', items: [] })
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
    setSystemStatus(statusData ?? {});
    setCashLedger(ledgerData.items ?? []);
    setSetupGuide(setupData ?? { items: [] });
  }

  async function loadAnalysis(nextSymbol = symbol, nextTimeframe = timeframe, nextStrategy = strategyName, manageLoading = true) {
    if (manageLoading) {
      setLoading(true);
      setBusyLabel('Analyse wird geladen');
      setMessage('');
    }
    try {
      const cleanSymbol = nextSymbol.trim();
      if (!cleanSymbol) {
        setMessage('Bitte ein Asset eingeben.');
        return;
      }
      const data = await apiGet<AssetAnalysis>(
        `/api/market/analysis?symbol=${q(cleanSymbol)}&timeframe=${q(nextTimeframe)}&strategy_name=${q(nextStrategy)}&limit=220`,
        { ...EMPTY_ANALYSIS, symbol: cleanSymbol, timeframe: nextTimeframe }
      );
      setAnalysis(data);
      setSymbol(data.symbol ?? cleanSymbol);
      setTimeframe(data.timeframe ?? nextTimeframe);
      await loadRecommendation(data.symbol ?? cleanSymbol, data.timeframe ?? nextTimeframe, nextStrategy, false);
    } catch (error) {
      setMessage(`Analyse fehlgeschlagen: ${errorDetail(error)}`);
    } finally {
      if (manageLoading) {
        setBusyLabel('');
        setLoading(false);
      }
    }
  }

  async function runSearch() {
    const cleanSearch = search.trim();
    if (!cleanSearch) {
      setMessage('Bitte einen Suchbegriff eingeben.');
      return;
    }
    const data = await apiGet<{ results: SearchResult[] }>(`/api/market/assets/search?q=${q(cleanSearch)}`, { results: [] });
    setSearchResults(data.results ?? []);
  }

  async function lookupInstrument(nextQuery = identifierQuery, nextType = identifierType) {
    await runBusy('Instrument wird gesucht', async () => {
      const cleanQuery = nextQuery.trim();
      if (!cleanQuery) {
        setMessage('Bitte Ticker, ISIN, WKN oder Namen eingeben.');
        return;
      }
      const data = await apiGet<InstrumentLookupResult>(`/api/intelligence/instrument/lookup?query=${q(cleanQuery)}&query_type=${q(nextType)}`, { query: cleanQuery, query_type: nextType, provider: 'unavailable', online: false, results: [], warnings: ['Lookup nicht erreichbar'] });
      setIdentifierResult(data);
      setMessage(data.results?.length ? `${data.results.length} Treffer gefunden.` : 'Keine Treffer gefunden.');
    });
  }

  async function loadInternetAnalysis(nextSymbol = symbol) {
    await runBusy('Nachrichten werden geladen', async () => {
      const cleanSymbol = nextSymbol.trim();
      if (!cleanSymbol) {
        setMessage('Bitte ein Asset eingeben.');
        return;
      }
      const data = await apiGet<InternetAnalysisResult>(`/api/intelligence/internet-analysis?symbol=${q(cleanSymbol)}&max_items=8`, { symbol: cleanSymbol, online: false, headline_count: 0, sentiment_score: 0, sentiment_label: 'nicht verbunden', risk_flags: [], summary: 'Online-Analyse nicht erreichbar', articles: [] });
      setInternetAnalysis(data);
      setMessage(`${data.headline_count ?? data.articles?.length ?? 0} Nachrichten geladen.`);
    });
  }

  async function loadRecommendation(nextSymbol = symbol, nextTimeframe = timeframe, nextStrategy = strategyName, manageLoading = true) {
    if (manageLoading) {
      setLoading(true);
      setBusyLabel('Empfehlung wird geladen');
    }
    try {
      const cleanSymbol = nextSymbol.trim();
      if (!cleanSymbol) {
        setMessage('Bitte ein Asset eingeben.');
        return;
      }
      const data = await apiGet<TradeRecommendation>(`/api/intelligence/recommendation?symbol=${q(cleanSymbol)}&timeframe=${q(nextTimeframe)}&strategy_name=${q(nextStrategy)}&include_internet=${includeInternet ? 'true' : 'false'}`, { symbol: cleanSymbol, timeframe: nextTimeframe, strategy_name: nextStrategy, decision: { action: 'NO_TRADE', side: 'neutral', trade_decision: 'Nein', risk_level: 'unbekannt', risk_score_adjusted: 100, position_size_hint: 'keine Position', confidence_score: 0, long_probability: 0, short_probability: 0, neutral_probability: 1, blockers: ['Recommendation-Service nicht erreichbar'], reasons: [], checklist: [] }, prediction: EMPTY_ANALYSIS.prediction, signal_preview: null, data_quality: {}, online_analysis: null, explanation: 'Recommendation-Service nicht erreichbar', disclaimer: 'Keine Anlageberatung.' });
      setRecommendation(data);
      if (data.online_analysis) setInternetAnalysis(data.online_analysis);
      if (manageLoading) setMessage(`Empfehlung: ${data.decision.trade_decision}`);
    } catch (error) {
      setMessage(`Empfehlung fehlgeschlagen: ${errorDetail(error)}`);
    } finally {
      if (manageLoading) {
        setBusyLabel('');
        setLoading(false);
      }
    }
  }

  async function addToWatchlist(nextSymbol = symbol) {
    await runBusy('Watchlist wird gespeichert', async () => {
      const cleanSymbol = nextSymbol.trim();
      const alertPrice = optionalNumber(watchAlert);
      const targetPrice = optionalNumber(watchTarget);
      if (!cleanSymbol) {
        setMessage('Bitte ein Asset eingeben.');
        return;
      }
      if (alertPrice === undefined || targetPrice === undefined) {
        setMessage('Bitte Alarmkurs und Zielkurs als Zahl eingeben oder leer lassen.');
        return;
      }
      const result = await apiPost('/api/watchlist', {
        symbol: cleanSymbol,
        note: watchNote || 'Aus Analyse hinzugefuegt',
        alert_price: alertPrice,
        target_price: targetPrice
      }, { status: 'error' });
      setMessage(`Watchlist: ${(result as any).status ?? 'unbekannt'}`);
      await refreshCore();
    });
  }

  async function cashAction(kind: 'deposit' | 'withdraw' | 'reset') {
    const amount = kind === 'deposit' ? positiveNumber(depositAmount) : kind === 'withdraw' ? positiveNumber(withdrawAmount) : positiveNumber(resetBalance);
    if (amount == null) {
      setMessage('Bitte einen Betrag größer 0 eingeben.');
      return;
    }
    if (kind === 'reset' && typeof window !== 'undefined') {
      const confirmed = window.confirm('Paper-Konto wirklich zurücksetzen? Offene Paper-Orders werden storniert.');
      if (!confirmed) {
        setMessage('Reset abgebrochen.');
        return;
      }
    }
    await runBusy('Paper-Konto wird aktualisiert', async () => {
      const path = kind === 'deposit' ? '/api/portfolio/paper/deposit' : kind === 'withdraw' ? '/api/portfolio/paper/withdraw' : '/api/portfolio/paper/reset';
      const body = kind === 'deposit'
        ? { amount, note: 'Manuelle Einzahlung' }
        : kind === 'withdraw'
          ? { amount, note: 'Manuelle Auszahlung' }
          : { balance: amount, note: 'Paper-Konto Reset', cancel_open_orders: true };
      const result = await apiPost(path, body, { status: 'error' });
      const expectedStatus = kind === 'deposit' ? 'deposited' : kind === 'withdraw' ? 'withdrawn' : 'reset';
      const failureReason = apiFailureDetail(result, [expectedStatus]);
      if (failureReason) {
        setMessage(`Paper-Konto konnte nicht aktualisiert werden: ${failureReason}`);
        setAccountConfirmation({
          title: 'Kontobuchung fehlgeschlagen',
          detail: failureReason,
          meta: 'Keine Änderung gebucht',
          tone: 'bad'
        });
        return;
      }
      setMessage(`Paper-Konto: ${(result as any).status ?? 'ok'}${(result as any).detail ? ' - ' + (result as any).detail : ''}`);
      setAccountConfirmation({
        title: kind === 'deposit' ? 'Einzahlung gebucht' : kind === 'withdraw' ? 'Auszahlung gebucht' : 'Paper-Konto zurückgesetzt',
        detail: `${number(amount, 2)} · ${kind === 'reset' ? 'Offene Orders storniert' : 'Virtuelles Guthaben aktualisiert'}`,
        meta: shortTime(new Date().toISOString()),
        tone: kind === 'withdraw' ? 'neutral' : 'good'
      });
      await refreshCore();
    });
  }

  async function createManualOrder(sideOverride?: 'long' | 'short', actionLabel?: 'buy' | 'long' | 'short') {
    const cleanSymbol = symbol.trim();
    const notional = positiveNumber(manualNotional);
    const stopLoss = optionalNumber(manualStop);
    const takeProfit = optionalNumber(manualTakeProfit);
    const side = sideOverride ?? manualSide;
    if (!cleanSymbol) {
      setMessage('Bitte ein Asset eingeben.');
      return;
    }
    if (notional == null) {
      setMessage('Bitte einen Paper-Trade-Betrag größer 0 eingeben.');
      return;
    }
    if (stopLoss === undefined || takeProfit === undefined) {
      setMessage('Bitte Stop und Ziel als Zahl eingeben oder leer lassen.');
      return;
    }
    const actionText = actionLabel === 'buy' ? 'Kauf' : side === 'short' ? 'Short' : 'Long';
    if (typeof window !== 'undefined') {
      const details = [
        `${actionText} für ${cleanSymbol} eröffnen?`,
        `Betrag: ${number(notional, 2)}`,
        stopLoss != null ? `Stop-Loss: ${number(stopLoss, 4)}` : null,
        takeProfit != null ? `Take-Profit: ${number(takeProfit, 4)}` : null
      ].filter(Boolean).join('\n');
      if (!window.confirm(details)) {
        setMessage(`${actionText} abgebrochen.`);
        return;
      }
    }
    await runBusy('Paper-Trade wird eröffnet', async () => {
      const result = await apiPost('/api/portfolio/paper/manual-order', {
        symbol: cleanSymbol,
        side,
        notional_amount: notional,
        stop_loss: stopLoss,
        take_profit: takeProfit,
        note: actionLabel === 'buy' ? 'Manueller Kauf aus Konto' : side === 'long' ? 'Manueller Long-Trade aus Konto' : 'Manueller Short-Trade aus Konto'
      }, { status: 'error' });
      const blockedReason = apiFailureDetail(result, ['manual_order_opened']);
      if (blockedReason) {
        setMessage(`Trade blockiert: ${blockedReason}`);
        setAccountConfirmation({
          title: 'Trade blockiert',
          detail: `${cleanSymbol} · ${blockedReason}`,
          meta: 'Schutzregel',
          tone: 'bad'
        });
        return;
      }
      setManualSide(side);
      setMessage(`${actionText}: ${(result as any).status ?? 'unbekannt'}${(result as any).detail ? ' - ' + (result as any).detail : ''}`);
      setAccountConfirmation({
        title: `${actionText} eröffnet`,
        detail: `${cleanSymbol} · Positionswert ${number(notional, 2)}`,
        meta: `Status ${(result as any).status ?? 'ok'}`,
        tone: 'good'
      });
      await Promise.all([refreshCore(), loadAnalysis(cleanSymbol, timeframe, strategyName, false)]);
    });
  }

  async function closePaperOrder(orderId: string) {
    if (!orderId) return;
    const originalOrder = (portfolio.positions ?? []).find((item: any) => String(item.id) === orderId) ?? {};
    const originalSide = originalOrder.side === 'short' ? 'short' : 'long';
    const originalSymbol = originalOrder.symbol ?? 'Position';
    const referencePrice = Number(originalOrder.current_price ?? originalOrder.entry_price ?? 0);
    const positionValue = Math.abs(Number(originalOrder.quantity ?? 0) * referencePrice);
    if (typeof window !== 'undefined') {
      const actionText = originalSide === 'short' ? 'Short schließen' : 'Position verkaufen';
      const confirmed = window.confirm(`${actionText}?\nAsset: ${originalSymbol}\nWert grob: ${number(positionValue, 2)}`);
      if (!confirmed) {
        setMessage(`${actionText} abgebrochen.`);
        return;
      }
    }
    await runBusy('Position wird geschlossen', async () => {
      const result = await apiPost(`/api/bot/close-order/${q(orderId)}`, {
        reason: 'closed_manual'
      }, { status: 'error' });
      const blockedReason = apiFailureDetail(result, ['closed']);
      if (blockedReason) {
        setMessage(`Position konnte nicht geschlossen werden: ${blockedReason}`);
        setAccountConfirmation({
          title: 'Schließen fehlgeschlagen',
          detail: blockedReason,
          meta: 'Keine Position geschlossen',
          tone: 'bad'
        });
        await refreshCore();
        return;
      }
      setMessage(`Position schließen: ${(result as any).status ?? 'unbekannt'}${(result as any).detail ? ' - ' + (result as any).detail : ''}`);
      const closedOrder = (result as any).closed_order ?? {};
      const pnl = Number(closedOrder.pnl_amount ?? 0);
      const closedSide = closedOrder.side ?? originalOrder.side;
      const closedSymbol = closedOrder.symbol ?? originalOrder.symbol ?? 'Asset';
      setAccountConfirmation({
        title: closedSide === 'short' ? 'Short geschlossen' : 'Position verkauft',
        detail: `${closedSymbol} · Ergebnis ${number(pnl, 2)}`,
        meta: `Status ${(result as any).status ?? 'geschlossen'}`,
        tone: pnl >= 0 ? 'good' : 'bad'
      });
      await refreshCore();
    });
  }

  async function removeFromWatchlist(nextSymbol: string) {
    await runBusy('Watchlist wird aktualisiert', async () => {
      await apiDelete(`/api/watchlist/${q(nextSymbol)}`, { status: 'error' });
      await refreshCore();
      setMessage(`${nextSymbol} entfernt.`);
    });
  }

  async function runBotCycle(nextSymbol = symbol) {
    const cleanSymbol = nextSymbol.trim();
    if (!cleanSymbol) {
      setMessage('Bitte ein Asset eingeben.');
      return;
    }
    if (killSwitchActive) {
      setMessage('Schutzstopp ist aktiv. Erst lösen, dann testen.');
      return;
    }
    if (!botCanTrade) {
      setMessage('Bot-Test ist nur im Paper-Modus erlaubt.');
      return;
    }
    await runBusy('Paper-Bot testet Entscheidung', async () => {
      const result = await apiPost('/api/bot/run-cycle', {
        symbol: cleanSymbol,
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
      await Promise.all([refreshCore(), loadAnalysis(cleanSymbol, timeframe, strategyName, false)]);
    });
  }

  async function evaluateOrders() {
    await runBusy('Orders werden geprüft', async () => {
      const result = await apiPost('/api/bot/evaluate-open-orders', {}, { status: 'error' });
      setMessage(`Order-Auswertung: ${(result as any).status ?? 'ok'}`);
      await refreshCore();
    });
  }

  async function saveBotConfig(patch: any) {
    await runBusy('Bot-Einstellung wird gespeichert', async () => {
      const result = await apiPatch('/api/bot/config', patch, { status: 'error' });
      setMessage(`Konfiguration gespeichert: ${(result as any).persistence ?? (result as any).status ?? 'ok'}`);
      await refreshCore();
    });
  }

  async function schedulerAction(action: 'start' | 'stop' | 'run-once') {
    if (action !== 'stop' && killSwitchActive) {
      setMessage('Schutzstopp ist aktiv. Automatik bleibt blockiert.');
      return;
    }
    await runBusy(action === 'start' ? 'Paper-Bot startet' : action === 'stop' ? 'Paper-Bot pausiert' : 'Paper-Bot testet einmal', async () => {
      const result = await apiPost(`/api/bot/scheduler/${action}`, {}, { status: 'error' });
      setMessage(`Scheduler ${action}: ${(result as any).status ?? 'ok'}`);
      await refreshCore();
    });
  }

  async function resetKillSwitch() {
    await runBusy('Schutzstopp wird gelöst', async () => {
      const result = await apiPost('/api/bot/kill-switch/reset', {}, { status: 'error' });
      setMessage(`Kill-Switch Reset: ${(result as any).persistence ?? (result as any).status ?? 'ok'}`);
      await refreshCore();
    });
  }

  async function activateKillSwitch() {
    await runBusy('Schutzstopp wird aktiviert', async () => {
      const result = await apiPost('/api/bot/kill-switch', {}, { status: 'error' });
      setMessage((result as any).message ?? `Schutzstopp: ${(result as any).status ?? 'ok'}`);
      await refreshCore();
    });
  }

  useEffect(() => {
    setApiDisplay(getApiDisplayUrl());
    refreshCore();
    loadAnalysis('BTC/USD', '1h');
  }, []);

  async function runFullDiagnostics() {
    await runBusy('System wird geprüft', async () => {
      const data = await apiGet<any>(`/api/ops/full-diagnostics?symbol=${q(symbol)}&timeframe=${q(timeframe)}&strategy_name=${q(strategyName)}`, { status: 'error', checks: [] });
      setDiagnostics(data);
      setMessage(`Diagnose: ${data.status ?? 'unbekannt'}`);
    });
  }

  async function copySetupProfile(profile: any) {
    const text = (profile.env_lines ?? []).join('\n');
    let copied = false;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        copied = true;
      }
    } catch {
      copied = false;
    }
    if (!copied && typeof document !== 'undefined') {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', 'true');
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      try {
        copied = document.execCommand('copy');
      } catch {
        copied = false;
      }
      document.body.removeChild(textarea);
    }
    setMessage(copied ? `Setup-Vorlage kopiert: ${profile.title}. Danach .env speichern und App neu starten.` : `Kopieren nicht erlaubt. Vorlage sichtbar markieren: ${profile.title}`);
  }

  const hasAnalysis = (analysis.candles?.length ?? 0) > 0 || Boolean(recommendation);
  const hasPaperActivity = Number(portfolio.open_orders_count ?? 0) > 0 || orders.length > 0;
  const killSwitchActive = Boolean(botConfig.kill_switch_active);
  const schedulerRunning = schedulerStatus.status === 'running' || Boolean(schedulerStatus.thread_alive);
  const botEnabled = Boolean(botConfig.bot_enabled);
  const maxOpenTrades = Number(botConfig.max_open_trades ?? bot.max_open_trades ?? 3);
  const openTradeCount = Number(portfolio.open_orders_count ?? portfolio.positions?.length ?? 0);
  const latestDecision = decisionAudits[0];
  const latestOrder = orders[0];
  const latestSchedulerRun = schedulerRuns[0] ?? schedulerStatus.last_run;
  const botRiskTone = !safeMode ? 'danger' : killSwitchActive ? 'attention' : (riskEvents.length > 0 || openTradeCount >= maxOpenTrades ? 'attention' : 'ready');
  const botRiskLabel = !safeMode ? 'Bitte prüfen' : killSwitchActive ? 'Gestoppt' : (riskEvents.length > 0 || openTradeCount >= maxOpenTrades ? 'Aufmerksam' : 'Grün');
  const botStateTitle = killSwitchActive ? 'Schutzstopp aktiv' : schedulerRunning ? 'Paper-Bot läuft' : botEnabled ? 'Paper-Bot bereit' : 'Paper-Bot pausiert';
  const botStateDetail = killSwitchActive
    ? 'Neue Bot-Trades sind blockiert, bis der Schutzstopp gelöst wird.'
    : schedulerRunning
      ? 'Der Bot prüft Watchlist und offene Paper-Positionen automatisch.'
      : botEnabled
        ? 'Der Bot ist freigegeben, läuft aber noch nicht automatisch.'
        : 'Automatik ist aus. Ein manueller Testlauf ist weiterhin möglich.';
  const botPrimaryAction = killSwitchActive ? resetKillSwitch : schedulerRunning ? () => schedulerAction('stop') : () => schedulerAction('start');
  const botPrimaryLabel = killSwitchActive ? 'Schutzstopp lösen' : schedulerRunning ? 'Paper-Bot pausieren' : 'Paper-Bot starten';
  const latestDecisionLabel = latestDecision
    ? (latestDecision.allowed ? 'Trade erlaubt' : 'Trade blockiert')
    : latestOrder
      ? `Letzte Order: ${latestOrder.status}`
      : 'Noch keine Bot-Entscheidung';
  const latestDecisionDetail = latestDecision
    ? `${latestDecision.symbol ?? symbol} · ${latestDecision.reason ?? 'ohne Detailgrund'}`
    : latestOrder
      ? `${latestOrder.symbol ?? symbol} · ${latestOrder.side ?? '-'} · ${latestOrder.decision_mode ?? latestOrder.model_source ?? 'Paper'}`
      : 'Starte einen Testlauf, um die erste Entscheidung zu sehen.';
  const botSymbols = (botConfig.symbols ?? []).length ? botConfig.symbols : [symbol];
  const botTimeframes = (botConfig.timeframes ?? []).length ? botConfig.timeframes : [timeframe];
  const currentEquity = Number(portfolio.current_equity ?? 0);
  const startingBalance = Number(portfolio.starting_balance ?? currentEquity ?? 0);
  const cashBalance = Number(portfolio.cash_balance ?? 0);
  const availableCash = Number(portfolio.available_cash ?? cashBalance);
  const openNotional = Number(portfolio.open_notional ?? 0);
  const realizedPnl = Number(portfolio.total_realized_pnl ?? 0);
  const unrealizedPnl = Number(portfolio.total_unrealized_pnl ?? 0);
  const paperPnl = currentEquity - startingBalance;
  const paperPnlPercent = startingBalance ? (paperPnl / startingBalance) * 100 : 0;
  const usedCapitalPercent = currentEquity ? (openNotional / currentEquity) * 100 : 0;
  const portfolioPositions = portfolio.positions ?? [];
  const accountAssetOptions = (() => {
    const rawItems = [
      ...DEFAULT_ACCOUNT_ASSETS,
      ...overview.map((item) => item.symbol),
      ...watchlist.map((item) => item.symbol),
      ...portfolioPositions.map((item: any) => item.symbol),
      ...searchResults.map((item) => item.symbol),
      ...(botConfig.symbols ?? []),
      symbol
    ];
    const unique: string[] = [];
    for (const item of rawItems) {
      const clean = String(item ?? '').trim().toUpperCase();
      if (clean && !unique.includes(clean)) unique.push(clean);
    }
    return unique;
  })();
  const customAccountAssetOptions = accountAssetOptions.filter((item) => !DEFAULT_ACCOUNT_ASSETS.includes(item));
  const selectedSymbolKey = symbol.trim().toUpperCase();
  const selectedQuote = overview.find((item) => item.symbol === selectedSymbolKey) ?? watchlist.find((item) => item.symbol === selectedSymbolKey)?.quote ?? null;
  const selectedOpenPositions = portfolioPositions.filter((item: any) => String(item.symbol ?? '').trim().toUpperCase() === selectedSymbolKey);
  const selectedLongPositions = selectedOpenPositions.filter((item: any) => item.side !== 'short');
  const selectedShortPositions = selectedOpenPositions.filter((item: any) => item.side === 'short');
  const manualNotionalValue = positiveNumber(manualNotional);
  const selectedPriceValue = Number(selectedQuote?.price ?? 0);
  const estimatedQuantity = manualNotionalValue != null && selectedPriceValue > 0 ? manualNotionalValue / selectedPriceValue : null;
  const longPositionValue = selectedLongPositions.reduce((sum: number, item: any) => {
    const quantity = Number(item.quantity ?? 0);
    const price = Number(item.current_price ?? item.entry_price ?? 0);
    return sum + quantity * price;
  }, 0);
  const shortPositionValue = selectedShortPositions.reduce((sum: number, item: any) => {
    const quantity = Number(item.quantity ?? 0);
    const price = Number(item.current_price ?? item.entry_price ?? 0);
    return sum + quantity * price;
  }, 0);
  const amountAboveCash = manualNotionalValue != null && manualNotionalValue > availableCash;
  const manualTradeBlockers = [
    !botCanTrade ? 'Nur Paper-Modus erlaubt' : '',
    killSwitchActive ? 'Schutzstopp aktiv' : '',
    openTradeCount >= maxOpenTrades ? `Positionslimit ${openTradeCount}/${maxOpenTrades}` : '',
    manualNotionalValue == null ? 'Betrag prüfen' : '',
    amountAboveCash ? 'Zu wenig freier Cash' : ''
  ].filter(Boolean);
  const canOpenManualTrade = manualTradeBlockers.length === 0;
  const manualTradeStatusTitle = canOpenManualTrade ? 'Trade bereit' : 'Trade blockiert';
  const manualTradeStatusDetail = canOpenManualTrade
    ? `${selectedSymbolKey || 'Asset'} kann im Paper-Konto eröffnet werden.`
    : manualTradeBlockers.join(' · ');
  const accountActivityItems = [
    ...orders.map((item: any) => {
      const side = item.side === 'short' ? 'Short' : 'Long';
      const isOpen = item.status === 'open';
      const pnl = Number(item.pnl_amount ?? 0);
      const notional = Math.abs(Number(item.quantity ?? 0) * Number(item.entry_price ?? 0));
      return {
        id: `order-${item.id}`,
        timestamp: item.closed_at ?? item.opened_at ?? item.created_at,
        title: `${side} ${isOpen ? 'offen' : 'geschlossen'}`,
        detail: `${item.symbol ?? '-'} · ${number(item.quantity, 6)} zu ${number(item.entry_price, 4)}`,
        meta: item.status ?? 'Order',
        amount: isOpen ? number(notional, 2) : number(pnl, 2),
        tone: isOpen ? 'neutral' : pnl >= 0 ? 'good' : 'bad'
      };
    }),
    ...cashLedger.map((item: any, index: number) => ({
      id: `cash-${item.id ?? index}`,
      timestamp: item.created_at,
      title: item.transaction_type === 'deposit' ? 'Einzahlung' : item.transaction_type === 'withdraw' ? 'Auszahlung' : 'Konto geändert',
      detail: item.note ?? 'Paper-Konto',
      meta: 'Cash',
      amount: number(item.amount, 2),
      tone: Number(item.amount ?? 0) >= 0 ? 'good' : 'bad'
    }))
  ].sort((left, right) => String(right.timestamp ?? '').localeCompare(String(left.timestamp ?? ''))).slice(0, 6);
  async function closeSelectedSidePositions(side: 'long' | 'short') {
    const matches = side === 'short' ? selectedShortPositions : selectedLongPositions;
    const orderIds = matches.map((item: any) => item.id).filter(Boolean);
    if (orderIds.length === 0) {
      setMessage(side === 'short' ? `Keine offene Short-Position für ${selectedSymbolKey} gefunden.` : `Keine offene Long-Position für ${selectedSymbolKey} zum Verkaufen gefunden.`);
      return;
    }
    const closeValue = side === 'short' ? shortPositionValue : longPositionValue;
    if (typeof window !== 'undefined') {
      const actionText = side === 'short' ? 'Short-Positionen schließen' : 'Long-Positionen verkaufen';
      const confirmed = window.confirm(`${actionText}?\nAsset: ${selectedSymbolKey}\nPositionen: ${orderIds.length}\nWert grob: ${number(closeValue, 2)}`);
      if (!confirmed) {
        setMessage(`${actionText} abgebrochen.`);
        return;
      }
    }
    await runBusy(side === 'short' ? 'Short-Positionen werden geschlossen' : 'Long-Positionen werden verkauft', async () => {
      const closeResults = await Promise.all(orderIds.map((orderId: string) => apiPost(`/api/bot/close-order/${q(String(orderId))}`, {
        reason: side === 'short' ? 'closed_short_from_account' : 'sold_long_from_account'
      }, { status: 'error' })));
      const failures = closeResults
        .map((item: any) => apiFailureDetail(item, ['closed']))
        .filter(Boolean);
      if (failures.length > 0) {
        const closedCount = closeResults.length - failures.length;
        const failureReason = failures[0];
        setMessage(`${closedCount}/${orderIds.length} Position(en) geschlossen: ${failureReason}`);
        setAccountConfirmation({
          title: closedCount > 0 ? 'Teilweise geschlossen' : 'Schließen fehlgeschlagen',
          detail: `${closedCount}/${orderIds.length} erfolgreich · ${failureReason}`,
          meta: failures.length > 1 ? `${failures.length} Fehler` : '1 Fehler',
          tone: 'bad'
        });
        await refreshCore();
        return;
      }
      setMessage(side === 'short' ? `${orderIds.length} Short-Position(en) geschlossen.` : `${orderIds.length} Long-Position(en) verkauft.`);
      setAccountConfirmation({
        title: side === 'short' ? 'Shorts geschlossen' : 'Longs verkauft',
        detail: `${selectedSymbolKey} · ${orderIds.length} Position(en) · Wert grob ${number(closeValue, 2)}`,
        meta: shortTime(new Date().toISOString()),
        tone: 'good'
      });
      await refreshCore();
    });
  }
  const accountTone = openTradeCount >= maxOpenTrades ? 'attention' : paperPnl < 0 ? 'attention' : 'ready';
  const accountStatus = openTradeCount >= maxOpenTrades ? 'Positionslimit erreicht' : paperPnl < 0 ? 'Im Minus' : 'Im grünen Bereich';
  const analysisDecision = recommendation?.decision;
  const analysisAction = analysisDecision?.action ?? 'NO_TRADE';
  const analysisBlockers = analysisDecision?.blockers ?? [];
  const analysisReasons = analysisDecision?.reasons ?? [];
  const analysisChecklist = analysisDecision?.checklist ?? [];
  const analysisCanTest = Boolean(recommendation && ['LONG', 'SHORT'].includes(analysisAction) && analysisBlockers.length === 0 && botCanTrade && !killSwitchActive);
  const analysisTone = !recommendation
    ? 'attention'
    : analysisCanTest
      ? 'ready'
      : analysisAction === 'WATCH'
        ? 'attention'
        : 'danger';
  const analysisTitle = !recommendation
    ? 'Analyse laden'
    : analysisCanTest
      ? `${analysisAction === 'SHORT' ? 'Short' : 'Long'} im Paper-Test möglich`
      : analysisAction === 'WATCH'
        ? 'Beobachten statt handeln'
        : 'Kein Trade';
  const analysisDetail = recommendation?.explanation ?? 'Lade Kurs, Signal und Empfehlung für das ausgewählte Asset.';
  const analysisPrimaryLabel = !recommendation ? 'Analyse laden' : analysisCanTest ? 'Paper-Bot testen' : 'Zur Watchlist';
  const analysisPrimaryAction = !recommendation
    ? () => loadAnalysis(symbol, timeframe)
    : analysisCanTest
      ? () => runBotCycle(symbol)
      : () => addToWatchlist(symbol);
  const analysisRiskLabel = recommendation ? `${analysisDecision?.risk_level ?? 'unbekannt'} · ${number(analysisDecision?.risk_score_adjusted, 0)}/100` : `${number(analysis.prediction.risk_score, 0)}/100`;
  const analysisConfidence = recommendation ? analysisDecision?.confidence_score : analysis.prediction.confidence_score;
  const analysisDirection = recommendation ? analysisDecision?.side : analysis.prediction.direction;
  const watchlistCards = watchlist.map((item) => {
    const price = Number(item.quote?.price ?? 0);
    const change = Number(item.quote?.change_percent ?? 0);
    const alertPrice = item.alert_price == null ? null : Number(item.alert_price);
    const targetPrice = item.target_price == null ? null : Number(item.target_price);
    const alertDistance = alertPrice && price ? Math.abs((price - alertPrice) / price) * 100 : null;
    const targetDistance = targetPrice && price ? Math.abs((price - targetPrice) / price) * 100 : null;
    return {
      ...item,
      price,
      change,
      alertDistance,
      targetDistance,
      needsAttention: (alertDistance != null && alertDistance <= 3) || (targetDistance != null && targetDistance <= 3),
    };
  });
  const watchGainers = watchlistCards.filter((item) => item.change > 0).length;
  const watchLosers = watchlistCards.filter((item) => item.change < 0).length;
  const watchWithRules = watchlistCards.filter((item) => item.alert_price != null || item.target_price != null).length;
  const watchAttention = watchlistCards.filter((item) => item.needsAttention).length;
  const strongestWatch = [...watchlistCards].sort((a, b) => Math.abs(b.change) - Math.abs(a.change))[0];
  const activeOnlineAnalysis = internetAnalysis ?? recommendation?.online_analysis ?? null;
  const researchArticles = activeOnlineAnalysis?.articles ?? [];
  const researchRiskFlags = activeOnlineAnalysis?.risk_flags ?? [];
  const researchWarnings = [activeOnlineAnalysis?.warning, ...(identifierResult?.warnings ?? [])].filter((item): item is string => Boolean(item));
  const identifierHitCount = identifierResult?.results?.length ?? 0;
  const identifierProviderLabel = identifierResult?.provider ?? systemStatus.identifier_provider?.effective_provider ?? systemStatus.identifier_provider?.provider ?? 'Fallback';
  const researchProviderLabel = researchArticles[0]?.provider ?? (activeOnlineAnalysis?.online ? 'Online' : 'Fallback');
  const researchBlockers = analysisBlockers;
  const researchNeedsAttention = researchRiskFlags.length > 0 || researchWarnings.length > 0 || researchBlockers.length > 0;
  const researchTone = !activeOnlineAnalysis && !identifierResult && !recommendation ? 'attention' : researchNeedsAttention ? 'attention' : 'ready';
  const researchTitle = recommendation
    ? `${recommendation.decision.trade_decision} für ${recommendation.symbol}`
    : activeOnlineAnalysis
      ? `${activeOnlineAnalysis.sentiment_label} für ${activeOnlineAnalysis.symbol}`
      : `${symbol} recherchieren`;
  const researchDetail = recommendation?.explanation ?? activeOnlineAnalysis?.summary ?? 'Nachrichten, Instrumentensuche und Empfehlung an einem Ort.';
  const researchNextLabel = !activeOnlineAnalysis ? 'Nachrichten laden' : !recommendation ? 'Empfehlung laden' : 'Analyse öffnen';
  const researchNextAction = !activeOnlineAnalysis
    ? () => loadInternetAnalysis(symbol)
    : !recommendation
      ? () => loadRecommendation(symbol, timeframe, strategyName)
      : () => {
        setView('analyse');
        loadAnalysis(symbol, timeframe);
      };
  const dashboardMovers = [...overview]
    .sort((a, b) => Math.abs(Number(b.change_percent ?? 0)) - Math.abs(Number(a.change_percent ?? 0)))
    .slice(0, 4);
  const dashboardDataLabel = systemStatus.simulated_data ? 'Mock-Daten' : marketOnline ? 'Live-Daten' : 'Nicht verbunden';
  const dashboardBotLabel = killSwitchActive ? 'Gestoppt' : schedulerRunning ? 'Läuft' : botEnabled ? 'Bereit' : 'Pausiert';
  const dashboardBotDetail = latestDecision ? `${latestDecision.symbol ?? symbol} · ${latestDecision.allowed ? 'erlaubt' : 'blockiert'}` : latestOrder ? `${latestOrder.symbol ?? symbol} · ${latestOrder.status}` : 'Noch keine Entscheidung.';
  const nextStep = (() => {
    if (!backendOnline || !marketOnline || !storageReady) {
      return {
        tone: 'attention',
        title: 'System einmal prüfen',
        detail: 'Eine Verbindung oder Speicherung braucht Aufmerksamkeit.',
        actionLabel: 'System prüfen',
        action: runFullDiagnostics,
        disabled: loading,
        facts: [backendOnline ? 'API online' : 'API prüfen', marketOnline ? 'Marktdaten online' : 'Marktdaten prüfen', storageReady ? storageLabel : 'Speicherung prüfen']
      };
    }
    if (setupGuide.status === 'attention' || !safeMode) {
      return {
        tone: 'attention',
        title: 'Grundsetup abschließen',
        detail: setupGuide.summary ?? 'Sicherheitsmodus, Speicherung und Marktdaten prüfen.',
        actionLabel: 'Setup öffnen',
        action: () => setView('setup'),
        disabled: false,
        facts: ['Paper-Modus', storageLabel, systemStatus.market_data_provider ?? 'Marktdaten']
      };
    }
    if (!hasAnalysis) {
      return {
        tone: 'ready',
        title: `${symbol} analysieren`,
        detail: 'Kurs, Signal und Empfehlung für das aktuelle Asset laden.',
        actionLabel: 'Analyse starten',
        action: () => {
          setView('analyse');
          loadAnalysis(symbol, timeframe);
        },
        disabled: loading,
        facts: [symbol, timeframe, strategyName]
      };
    }
    if (watchlist.length === 0) {
      return {
        tone: 'ready',
        title: `${symbol} merken`,
        detail: 'Das aktuelle Asset in die Watchlist legen.',
        actionLabel: 'Zur Watchlist hinzufügen',
        action: () => addToWatchlist(symbol),
        disabled: loading,
        facts: ['Analyse geladen', symbol, 'Watchlist leer']
      };
    }
    if (!hasPaperActivity) {
      return {
        tone: 'ready',
        title: 'Paper-Konto testen',
        detail: 'Virtuelles Guthaben und simulierte Trades prüfen.',
        actionLabel: 'Paper-Konto öffnen',
        action: () => setView('portfolio'),
        disabled: false,
        facts: [`${watchlist.length} auf Watchlist`, 'Kein echtes Geld', 'Paper-only']
      };
    }
    return {
      tone: 'ready',
      title: 'Status aktualisieren',
      detail: 'Daten, Konto und Bot-Ergebnisse neu laden.',
      actionLabel: 'Aktualisieren',
      action: refreshCore,
      disabled: loading,
      facts: [`${watchlist.length} auf Watchlist`, `${orders.length} Orders`, storageLabel]
    };
  })();
  const guidedSteps = [
    {
      key: 'system',
      done: backendOnline && marketOnline && storageReady,
      title: 'System bereit',
      detail: storageReady ? 'API, Marktdaten und Speicherung sind geprüft.' : 'Prüfe, ob Daten und Speicherung bereit sind.',
      actionLabel: 'System prüfen',
      action: runFullDiagnostics,
      disabled: loading
    },
    {
      key: 'analysis',
      done: hasAnalysis,
      title: 'Asset analysieren',
      detail: `${symbol} mit Kurs, Signal und Empfehlung ansehen.`,
      actionLabel: 'Analyse öffnen',
      action: () => {
        setView('analyse');
        loadAnalysis(symbol, timeframe);
      },
      disabled: loading
    },
    {
      key: 'watchlist',
      done: watchlist.length > 0,
      title: 'Watchlist anlegen',
      detail: watchlist.length > 0 ? `${watchlist.length} Asset${watchlist.length === 1 ? '' : 's'} gespeichert.` : 'Ein beobachtetes Asset speichern.',
      actionLabel: watchlist.length > 0 ? 'Watchlist öffnen' : 'Asset merken',
      action: () => {
        if (watchlist.length > 0) setView('watchlist');
        else addToWatchlist(symbol);
      },
      disabled: loading
    },
    {
      key: 'paper',
      done: hasPaperActivity,
      title: 'Paper-Trade testen',
      detail: hasPaperActivity ? 'Es gibt bereits simulierte Trade-Aktivität.' : 'Optional einen simulierten Trade ohne echtes Geld öffnen.',
      actionLabel: 'Paper-Konto öffnen',
      action: () => setView('portfolio'),
      disabled: false
    }
  ];
  const completedGuidedSteps = guidedSteps.filter((step) => step.done).length;
  const diagnosticChecks = diagnostics?.checks ?? [];
  const diagnosticRequiredChecks = diagnosticChecks.filter((item: any) => item.name !== 'Internet-Analyse');
  const diagnosticOptionalChecks = diagnosticChecks.filter((item: any) => item.name === 'Internet-Analyse');
  const diagnosticOpenChecks = diagnosticRequiredChecks.filter((item: any) => !item.ok);
  const diagnosticReadyCount = diagnosticRequiredChecks.filter((item: any) => item.ok).length;
  const diagnosticsReady = diagnosticRequiredChecks.length > 0 && diagnosticOpenChecks.length === 0;
  const diagnosticsTitle = diagnosticsReady ? 'System bereit' : `${diagnosticOpenChecks.length} Punkt${diagnosticOpenChecks.length === 1 ? '' : 'e'} prüfen`;
  const messageLooksProblematic = message.toLowerCase().includes('error') || message.toLowerCase().includes('fehl') || message.toLowerCase().includes('problem');

  return (
    <main className="appShell">
      <header className="topBar">
        <div>
          <p className="eyebrow">Paper-Trading</p>
          <h1>Trading Cockpit</h1>
          <p className="muted">Analyse, Watchlist und Bot-Test ohne echtes Geld.</p>
        </div>
        <div className="statusPills" aria-label="Systemstatus">
          <span className={safeMode ? 'pill goodPill' : 'pill badPill'}>{safeMode ? 'Sicherer Modus' : 'Bitte prüfen'}</span>
          <span className={backendOnline ? 'pill goodPill' : 'pill badPill'}>API {backendOnline ? 'online' : 'offline'}</span>
          <span className={marketOnline ? 'pill goodPill' : 'pill badPill'}>Marktdaten {marketOnline ? 'online' : 'offline'}</span>
          <span className={storageReady ? 'pill goodPill' : 'pill warnPill'}>{storageLabel}</span>
          <details className="techDetails">
            <summary>Technik</summary>
            <p>API: {apiDisplay}</p>
            <p>Bot: {simpleStatus(bot.status)}</p>
            {systemStatus.local_persistence?.path && <p>Speicher: {systemStatus.local_persistence.path}</p>}
          </details>
        </div>
      </header>

      <nav className="tabs">
        {(['dashboard', 'analyse', 'watchlist', 'portfolio', 'intelligence', 'setup', 'bot', 'monitoring', 'backtest', 'ml'] as View[]).map((item) => (
          <button key={item} onClick={() => setView(item)} className={`tab ${view === item ? 'active' : ''}`}>
            {VIEW_LABELS[item]}
          </button>
        ))}
      </nav>

      <div className="quickActions">
        <button className="primary" onClick={() => setView('analyse')}>Analyse starten</button>
        <button onClick={() => setView('portfolio')}>Paper-Konto öffnen</button>
        <button onClick={() => setView('setup')}>Setup öffnen</button>
        <button onClick={runFullDiagnostics} disabled={loading}>System prüfen</button>
        <span className="muted">{busyLabel || (loading ? 'Lädt...' : 'Bereit')}</span>
      </div>

      {(message || busyLabel) && (
        <section className={`statusBanner ${messageLooksProblematic ? 'attention' : ''}`} role="status" aria-live="polite">
          <strong>{busyLabel || 'Status'}</strong>
          {message && <p>{message}</p>}
          {messageLooksProblematic && <p className="muted">System prüfen zeigt dir die nächsten Details.</p>}
        </section>
      )}

      {diagnosticChecks.length ? (
        <section className={`diagnosticsPanel ${diagnosticsReady ? '' : 'attention'}`} aria-label="Systemprüfung">
          <div className="guidedHeader">
            <div>
              <p className="eyebrow">Systemprüfung</p>
              <h2>{diagnosticsTitle}</h2>
              <p className="muted">
                {diagnosticsReady
                  ? 'Die wichtigsten Prüfungen für Paper-Trading sind bestanden.'
                  : 'Diese Punkte brauchen Aufmerksamkeit, bevor der Paper-Bot entspannt laufen sollte.'}
              </p>
            </div>
            <span className={`pill ${diagnosticsReady ? 'goodPill' : 'warnPill'}`}>{diagnostics.status ?? 'unbekannt'}</span>
          </div>

          <div className="diagnosticSummaryGrid">
            <article className="diagnosticMetricCard">
              <span className="muted">Bestanden</span>
              <strong>{diagnosticReadyCount}/{diagnosticRequiredChecks.length}</strong>
              <p>Wichtige Prüfungen</p>
            </article>
            <article className={`diagnosticMetricCard ${diagnosticOpenChecks.length ? 'attention' : ''}`}>
              <span className="muted">Offen</span>
              <strong>{diagnosticOpenChecks.length}</strong>
              <p>{diagnosticOpenChecks.length ? 'Bitte prüfen' : 'Keine offenen Pflichtpunkte'}</p>
            </article>
            <article className="diagnosticMetricCard">
              <span className="muted">Optional</span>
              <strong>{diagnosticOptionalChecks.filter((item: any) => item.ok).length}/{diagnosticOptionalChecks.length}</strong>
              <p>News/Recherche darf optional sein</p>
            </article>
            <article className="diagnosticMetricCard">
              <span className="muted">Asset</span>
              <strong>{symbol}</strong>
              <p>{timeframe} · {strategyName}</p>
            </article>
          </div>

          {diagnosticOpenChecks.length ? (
            <div className="checklistGrid">
              {diagnosticOpenChecks.map((item: any) => (
                <div key={item.name} className="checkItem blocked">
                  <strong>{item.name}</strong>
                  <span>{item.message}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="emptyState">
              <h3>Keine Pflichtprobleme gefunden</h3>
              <p className="muted">Optional kannst du News/Recherche oder bessere Datenanbieter im Setup erweitern.</p>
              <button onClick={() => setView('setup')}>Setup ansehen</button>
            </div>
          )}

          <details className="advancedSettings">
            <summary>Alle Prüfergebnisse anzeigen</summary>
            <div className="diagnosticList">
              {diagnosticChecks.map((item: any) => (
                <div key={item.name} className={`diagnosticRow ${item.ok ? 'passed' : 'blocked'}`}>
                  <strong>{item.ok ? 'OK' : 'Prüfen'} · {item.name}</strong>
                  <span>{item.message}</span>
                </div>
              ))}
            </div>
          </details>
        </section>
      ) : null}

      {view === 'dashboard' && (
        <div className="stack">
          <section className={`nextStepPanel ${nextStep.tone === 'attention' ? 'attention' : ''}`} aria-label="Naechster Schritt">
            <div>
              <p className="eyebrow">Gerade sinnvoll</p>
              <h2>{nextStep.title}</h2>
              <p className="muted">{nextStep.detail}</p>
              <div className="nextFacts">
                {nextStep.facts.map((fact) => <span key={fact}>{fact}</span>)}
              </div>
            </div>
            <button className="primary nextStepButton" onClick={nextStep.action} disabled={nextStep.disabled}>{nextStep.actionLabel}</button>
          </section>

          <section className="guidedStart" aria-label="Erste Schritte">
            <div className="guidedHeader">
              <div>
                <p className="eyebrow">Geführter Start</p>
                <h2>{marketOnline ? 'In vier Schritten zum sicheren Paper-Test' : 'Erst Verbindung prüfen'}</h2>
                <p className="muted">
                  {marketOnline
                    ? 'Alles bleibt im Paper-Modus. Folge den Schritten von links nach rechts oder springe direkt zur passenden Aktion.'
                    : 'Marktdaten sind noch nicht erreichbar. Beginne mit dem Systemcheck.'}
                </p>
              </div>
              <span className="progressPill">{completedGuidedSteps} von {guidedSteps.length} erledigt</span>
            </div>
            <div className="stepGrid">
              {guidedSteps.map((step, index) => (
                <article key={step.key} className={`stepCard ${step.done ? 'complete' : ''}`}>
                  <div className="stepTop">
                    <span className="stepMarker">{step.done ? 'OK' : index + 1}</span>
                    <span className={step.done ? 'stepState good' : 'stepState'}>{step.done ? 'Erledigt' : 'Offen'}</span>
                  </div>
                  <h3>{step.title}</h3>
                  <p className="muted">{step.detail}</p>
                  <button className={index === 0 || index === 1 ? 'primary stepAction' : 'stepAction'} onClick={step.action} disabled={step.disabled}>{step.actionLabel}</button>
                </article>
              ))}
            </div>
          </section>

          <div className="dashboardSummaryGrid">
            <article className={`dashboardMetricCard ${paperPnl < 0 ? 'attention' : ''}`}>
              <span className="muted">Paper-Konto</span>
              <strong>{number(currentEquity, 2)}</strong>
              <p className={paperPnl >= 0 ? 'good' : 'bad'}>{number(paperPnl, 2)} Gesamt P/L · {number(availableCash, 2)} frei</p>
              <button onClick={() => setView('portfolio')}>Konto öffnen</button>
            </article>

            <article className={`dashboardMetricCard ${botRiskTone === 'attention' || botRiskTone === 'danger' ? 'attention' : ''}`}>
              <span className="muted">Paper-Bot</span>
              <strong>{dashboardBotLabel}</strong>
              <p>{dashboardBotDetail}</p>
              <button onClick={() => setView('bot')}>Bot öffnen</button>
            </article>

            <article className={`dashboardMetricCard ${!marketOnline || systemStatus.simulated_data ? 'attention' : ''}`}>
              <span className="muted">Verbindung</span>
              <strong>{dashboardDataLabel}</strong>
              <p>{storageLabel} · {systemStatus.market_data_provider ?? 'Marktdaten'}</p>
              <button onClick={() => setView('setup')}>Setup ansehen</button>
            </article>

            <article className={`dashboardMetricCard ${riskEvents.length > 0 ? 'attention' : ''}`}>
              <span className="muted">Heute</span>
              <strong>{watchlist.length} im Blick</strong>
              <p>{openTradeCount} offen · {riskEvents.length} Risiko-Hinweise</p>
              <button onClick={() => setView(riskEvents.length ? 'monitoring' : 'watchlist')}>{riskEvents.length ? 'Risiko ansehen' : 'Watchlist öffnen'}</button>
            </article>
          </div>

          <section className="card">
            <div className="guidedHeader">
              <div>
                <p className="eyebrow">Markt</p>
                <h2>Auffällige Bewegungen</h2>
                <p className="muted">Die stärksten Tagesbewegungen aus der Übersicht, direkt analysierbar.</p>
              </div>
              <button onClick={refreshCore} disabled={loading}>Kurse aktualisieren</button>
            </div>
            {dashboardMovers.length ? (
              <div className="marketTileGrid">
                {dashboardMovers.map((item) => {
                  const change = Number(item.change_percent ?? 0);
                  const price = Number(item.price ?? 0);
                  return (
                    <article key={item.symbol} className={`marketTile ${change < 0 ? 'down' : ''}`}>
                      <div className="stepTop">
                        <h3>{item.symbol}</h3>
                        <span className={`pill ${change >= 0 ? 'goodPill' : 'badPill'}`}>{number(change, 2)}%</span>
                      </div>
                      <strong>{item.error ? '-' : number(price, item.symbol.includes('/') && price < 10 ? 5 : 2)}</strong>
                      <p className="muted">{item.provider ?? 'Provider unbekannt'}</p>
                      <button className="primary" onClick={() => { setView('analyse'); loadAnalysis(item.symbol); }}>Analysieren</button>
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className="emptyState">
                <h3>Noch kein Marktbild</h3>
                <p className="muted">Aktualisiere die Daten oder prüfe das Setup.</p>
                <button className="primary" onClick={refreshCore} disabled={loading}>Aktualisieren</button>
              </div>
            )}
          </section>

          <section className="card">
            <details className="advancedSettings">
              <summary>Technische Übersicht anzeigen</summary>
              <div className="grid">
                <BotStatusCard bot={bot as any} />
                <section>
                  <h3>Verbindungen</h3>
                  <p>App-API: {simpleStatus(systemStatus.backend)}</p>
                  <p>Speicherung: {storageLabel}</p>
                  <p>Datenquelle: {systemStatus.market_data_provider ?? '-'}</p>
                  <p>Marktdaten: {simpleStatus(systemStatus.market_data?.status)}</p>
                  <p>Recherche: {systemStatus.internet_analysis_provider?.internet_analysis_enabled ? 'verbunden' : 'nicht verbunden'}</p>
                  <p className="muted">{systemStatus.recommended_action ?? ''}</p>
                </section>
              </div>
              <div className="tableScroll" style={{ marginTop: 14 }}>
                <table>
                  <thead><tr><th align="left">Asset</th><th align="right">Kurs</th><th align="right">Tag %</th><th align="left">Provider</th><th /></tr></thead>
                  <tbody>
                    {overview.map((item) => (
                      <tr key={item.symbol}>
                        <td>{item.symbol}</td>
                        <td align="right">{item.error ? '-' : number(item.price, item.symbol.includes('/') && Number(item.price) < 10 ? 5 : 2)}</td>
                        <td align="right" className={Number(item.change_percent ?? 0) >= 0 ? 'good' : 'bad'}>{number(item.change_percent, 2)}%</td>
                        <td>{item.provider ?? '-'}</td>
                        <td align="right"><button onClick={() => { setView('analyse'); loadAnalysis(item.symbol); }}>Analysieren</button></td>
                      </tr>
                    ))}
                    {overview.length === 0 && <tr><td colSpan={5}>Noch keine Marktdaten geladen.</td></tr>}
                  </tbody>
                </table>
              </div>
            </details>
          </section>
        </div>
      )}

      {view === 'analyse' && (
        <div className="stack">
          <section className="card">
            <h2>Asset auswählen</h2>
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

          <section className={`analysisDecisionPanel ${analysisTone === 'danger' ? 'danger' : analysisTone === 'attention' ? 'attention' : ''}`}>
            <div>
              <p className="eyebrow">Entscheidung</p>
              <h2>{analysisTitle}</h2>
              <p className="muted">{analysisDetail}</p>
              <div className="analysisReasonList">
                {(analysisBlockers.length ? analysisBlockers : analysisReasons).slice(0, 3).map((item) => (
                  <span key={item} className={analysisBlockers.length ? 'bad' : ''}>{item}</span>
                ))}
                {!recommendation && <span>Wähle ein Asset und lade die Analyse.</span>}
              </div>
            </div>
            <div className="analysisActions">
              <button className="primary" onClick={analysisPrimaryAction} disabled={loading || (analysisCanTest && killSwitchActive)}>{analysisPrimaryLabel}</button>
              <button onClick={() => setView('portfolio')}>Konto ansehen</button>
              <button onClick={() => setView('intelligence')}>Recherche öffnen</button>
            </div>
          </section>

          <div className="analysisSummaryGrid">
            <article className="analysisMetricCard">
              <span className="muted">Kurs</span>
              <strong>{number(analysis.quote?.price, analysis.symbol.includes('/') && Number(analysis.quote?.price) < 10 ? 5 : 2)}</strong>
              <p className={Number(analysis.quote?.change_percent ?? 0) >= 0 ? 'good' : 'bad'}>{number(analysis.quote?.change_percent, 2)}% heute · {analysis.quote?.provider ?? '-'}</p>
            </article>
            <article className="analysisMetricCard">
              <span className="muted">Richtung</span>
              <strong>{String(analysisDirection ?? '-')}</strong>
              <p>Long {percent(analysis.prediction.probability_long)} · Short {percent(analysis.prediction.probability_short)}</p>
            </article>
            <article className={`analysisMetricCard ${Number(analysisDecision?.risk_score_adjusted ?? analysis.prediction.risk_score ?? 0) > bot.max_risk_score ? 'attention' : ''}`}>
              <span className="muted">Risiko</span>
              <strong>{analysisRiskLabel}</strong>
              <p>Confidence {number(analysisConfidence, 0)}/100</p>
            </article>
            <article className="analysisMetricCard">
              <span className="muted">Signal</span>
              <strong>{analysis.signal_preview ? analysis.signal_preview.signal_type.toUpperCase() : 'Keins'}</strong>
              <p>{analysis.signal_preview ? `CRV ${number(analysis.signal_preview.crv, 2)} · Score ${number(analysis.signal_preview.signal_score, 0)}` : 'Aktuell kein handelbares Signal.'}</p>
            </article>
          </div>

          {recommendation && (
            <section className="card">
              <div className="guidedHeader">
                <div>
                  <p className="eyebrow">Checkliste</p>
                  <h2>Warum diese Entscheidung?</h2>
                </div>
                <span className={`pill ${analysisCanTest ? 'goodPill' : analysisBlockers.length ? 'badPill' : 'warnPill'}`}>{recommendation.decision.trade_decision}</span>
              </div>
              <div className="checklistGrid">
                {analysisChecklist.map((item) => (
                  <div key={item.name} className={`checkItem ${item.passed ? 'passed' : 'blocked'}`}>
                    <strong>{item.passed ? 'OK' : 'Prüfen'} · {item.name}</strong>
                    <span>{item.value}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          <CandleChart candles={analysis.candles ?? []} />

          <section className="card">
            <details className="advancedSettings">
              <summary>Technische Details und Asset-Suche anzeigen</summary>
              <div className="grid">
                <section>
                  <h3>Technische Indikatoren</h3>
                  <div className="tableScroll">
                    <table>
                      <tbody>
                        {Object.entries(analysis.indicators ?? {}).map(([key, value]) => (
                          <tr key={key}><td>{key}</td><td align="right">{typeof value === 'number' ? number(value, 4) : String(value)}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>

                <section>
                  <h3>Asset-Suche</h3>
                  <div className="row">
                    <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="z. B. apple, btc, gold" />
                    <button onClick={runSearch}>Suchen</button>
                  </div>
                  <div className="tableScroll">
                    <table>
                      <tbody>
                        {searchResults.map((item) => (
                          <tr key={`${item.symbol}-${item.exchange ?? ''}`}>
                            <td><strong>{item.symbol}</strong><br /><span className="muted">{item.name}</span></td>
                            <td>{item.asset_type}</td>
                            <td align="right"><button onClick={() => { setSymbol(item.symbol); loadAnalysis(item.symbol, timeframe); }}>Laden</button></td>
                          </tr>
                        ))}
                        {searchResults.length === 0 && <tr><td colSpan={3}>Noch keine Suchergebnisse.</td></tr>}
                      </tbody>
                    </table>
                  </div>
                </section>
              </div>
            </details>
          </section>
        </div>
      )}


      {view === 'intelligence' && (
        <div className="stack">
          <section className={`researchHero ${researchTone === 'attention' ? 'attention' : ''}`}>
            <div>
              <p className="eyebrow">Recherche</p>
              <h2>{researchTitle}</h2>
              <p className="muted">{researchDetail}</p>
              <div className="botFactRow">
                <span>{symbol}</span>
                <span>{timeframe}</span>
                <span>{identifierProviderLabel}</span>
                <span>{includeInternet ? 'Internet an' : 'Internet aus'}</span>
              </div>
            </div>
            <div className="researchActions">
              <button className="primary" onClick={researchNextAction} disabled={loading}>{researchNextLabel}</button>
              <button onClick={() => lookupInstrument(identifierQuery || symbol, identifierType)} disabled={loading}>Instrument suchen</button>
              <button onClick={() => { setView('analyse'); loadAnalysis(symbol, timeframe); }} disabled={loading}>Analyse öffnen</button>
            </div>
          </section>

          <div className="researchSummaryGrid">
            <article className="researchMetricCard">
              <span className="muted">Nachrichten</span>
              <strong>{activeOnlineAnalysis?.headline_count ?? researchArticles.length}</strong>
              <p>{activeOnlineAnalysis?.sentiment_label ?? 'Noch nicht geladen'} · {researchProviderLabel}</p>
            </article>
            <article className={`researchMetricCard ${researchNeedsAttention ? 'attention' : ''}`}>
              <span className="muted">Hinweise</span>
              <strong>{researchRiskFlags.length + researchWarnings.length + researchBlockers.length}</strong>
              <p>{researchNeedsAttention ? 'Vor Trade prüfen' : 'Keine roten Hinweise'}</p>
            </article>
            <article className="researchMetricCard">
              <span className="muted">Suchtreffer</span>
              <strong>{identifierHitCount}</strong>
              <p>{identifierResult ? `Für ${identifierResult.query}` : 'Ticker, ISIN, WKN oder Name'}</p>
            </article>
            <article className="researchMetricCard">
              <span className="muted">Empfehlung</span>
              <strong>{recommendation?.decision.action ?? '-'}</strong>
              <p>{recommendation ? `${recommendation.decision.risk_level} · ${number(recommendation.decision.confidence_score, 0)}/100` : 'Noch offen'}</p>
            </article>
          </div>

          {(researchRiskFlags.length > 0 || researchWarnings.length > 0 || researchBlockers.length > 0) && (
            <section className="card">
              <div className="guidedHeader">
                <div>
                  <p className="eyebrow">Prüfen</p>
                  <h2>Wichtige Hinweise</h2>
                  <p className="muted">Diese Punkte sollten vor einem Paper-Test kurz gelesen werden.</p>
                </div>
                <span className="pill warnPill">{researchRiskFlags.length + researchWarnings.length + researchBlockers.length} Hinweise</span>
              </div>
              <div className="checklistGrid">
                {researchWarnings.map((item, idx) => (
                  <div key={`warning-${idx}`} className="checkItem blocked">
                    <strong>Hinweis</strong>
                    <span>{item}</span>
                  </div>
                ))}
                {researchRiskFlags.map((item) => (
                  <div key={item} className="checkItem blocked">
                    <strong>Nachrichten-Risiko</strong>
                    <span>{item}</span>
                  </div>
                ))}
                {researchBlockers.map((item) => (
                  <div key={item} className="checkItem blocked">
                    <strong>Trade-Blocker</strong>
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="card">
            <div className="guidedHeader">
              <div>
                <p className="eyebrow">Kontext</p>
                <h2>Nachrichten & Stimmung</h2>
                <p className="muted">{activeOnlineAnalysis ? activeOnlineAnalysis.summary : 'Lade Nachrichten, um Stimmung und aktuelle Risiken zu sehen.'}</p>
              </div>
              <button onClick={() => loadInternetAnalysis(symbol)} disabled={loading}>Nachrichten aktualisieren</button>
            </div>
            {researchArticles.length ? (
              <div className="articleGrid">
                {researchArticles.slice(0, 4).map((item, idx) => (
                  <article key={`${item.headline ?? 'headline'}-${idx}`} className="articleCard">
                    <div className="stepTop">
                      <span className="muted">{item.source ?? 'Quelle'}</span>
                      <span className="pill">{item.sentiment_label ?? item.provider ?? '-'}</span>
                    </div>
                    <h3>{item.headline ?? 'Ohne Überschrift'}</h3>
                    {item.summary && <p className="muted">{item.summary}</p>}
                    {item.url && <a href={item.url} target="_blank" rel="noreferrer">Quelle öffnen</a>}
                  </article>
                ))}
              </div>
            ) : (
              <div className="emptyState">
                <h3>Noch kein Nachrichtenbild</h3>
                <p className="muted">Für {symbol} wurden in dieser Sitzung noch keine Nachrichten geladen.</p>
                <button className="primary" onClick={() => loadInternetAnalysis(symbol)} disabled={loading}>Nachrichten laden</button>
              </div>
            )}
          </section>

          <section className="card">
            <details className="advancedSettings">
              <summary>Instrument suchen</summary>
              <div className="researchFormGrid">
                <label>Suchbegriff
                  <input value={identifierQuery} onChange={(event) => setIdentifierQuery(event.target.value)} placeholder="z. B. US0378331005, 865985, AAPL, Apple" />
                </label>
                <label>Typ
                  <select value={identifierType} onChange={(event) => setIdentifierType(event.target.value)}>
                    <option value="auto">Auto</option>
                    <option value="ticker">Ticker</option>
                    <option value="isin">ISIN</option>
                    <option value="wkn">WKN</option>
                    <option value="name">Name</option>
                  </select>
                </label>
                <div className="formAction">
                  <button className="primary" onClick={() => lookupInstrument()} disabled={loading}>Suchen</button>
                </div>
              </div>
              <p className="muted">Provider: {identifierProviderLabel}</p>
              {identifierResult && (
                <div className="tableScroll">
                  <table>
                    <thead><tr><th align="left">Symbol</th><th align="left">Name</th><th align="left">Typ</th><th align="left">Börse</th><th align="left">Währung</th><th /></tr></thead>
                    <tbody>
                      {(identifierResult.results ?? []).map((item, idx) => (
                        <tr key={`${item.symbol}-${idx}`}>
                          <td>{item.symbol}</td>
                          <td>{item.name ?? item.security_description ?? '-'}</td>
                          <td>{item.asset_type ?? item.market_sector ?? '-'}</td>
                          <td>{item.exchange ?? '-'}</td>
                          <td>{item.currency ?? '-'}</td>
                          <td align="right"><button onClick={() => { if (item.symbol) { setSymbol(item.symbol); setView('analyse'); loadAnalysis(item.symbol, timeframe); }}} disabled={!item.symbol}>Analysieren</button></td>
                        </tr>
                      ))}
                      {identifierResult.results.length === 0 && <tr><td colSpan={6}>Keine Treffer. {identifierResult.warnings?.join(' ')}</td></tr>}
                    </tbody>
                  </table>
                </div>
              )}
            </details>
          </section>

          <section className="card">
            <details className="advancedSettings">
              <summary>Empfehlung einstellen</summary>
              <div className="researchFormGrid">
                <label>Symbol
                  <input value={symbol} onChange={(event) => setSymbol(event.target.value)} />
                </label>
                <label>Zeitraum
                  <select value={timeframe} onChange={(event) => setTimeframe(event.target.value)}>
                    <option value="1h">1h</option><option value="4h">4h</option><option value="1D">1D</option>
                  </select>
                </label>
                <label>Strategie
                  <select value={strategyName} onChange={(event) => setStrategyName(event.target.value)}>
                    {(strategies.length ? strategies : [{ name: 'trend_atr_v0.7', label: 'Trendfolge ATR' } as any]).map((item) => <option key={item.name} value={item.name}>{item.label}</option>)}
                  </select>
                </label>
                <label className="checkboxLine">
                  <input type="checkbox" checked={includeInternet} onChange={(event) => setIncludeInternet(event.target.checked)} />
                  Internet-Kontext
                </label>
              </div>
              <div className="row" style={{ marginTop: 12 }}>
                <button className="primary" onClick={() => loadRecommendation(symbol, timeframe, strategyName)} disabled={loading}>Empfehlung laden</button>
                <button onClick={() => { setView('analyse'); loadAnalysis(symbol, timeframe); }} disabled={loading}>Analyse öffnen</button>
              </div>
              {recommendation && (
                <div className="recommendationGrid">
                  <article>
                    <span className="muted">Entscheidung</span>
                    <strong className={recommendation.decision.action === 'LONG' ? 'good' : recommendation.decision.action === 'SHORT' ? 'bad' : ''}>{recommendation.decision.action}</strong>
                    <p>{recommendation.decision.trade_decision} · Risiko: {recommendation.decision.risk_level}</p>
                    <p className="muted">{recommendation.decision.position_size_hint}</p>
                  </article>
                  <article>
                    <span className="muted">Gründe</span>
                    {(analysisReasons.length ? analysisReasons : ['Noch keine Gründe geladen.']).map((item) => <p key={item}>{item}</p>)}
                  </article>
                  <article>
                    <span className="muted">Checkliste</span>
                    {(analysisChecklist.length ? analysisChecklist : [{ name: 'Empfehlung', passed: false, value: 'Noch nicht geladen' }]).map((item) => (
                      <p key={item.name} className={item.passed ? 'good' : 'bad'}>{item.passed ? 'OK' : 'Prüfen'} · {item.name}: {item.value}</p>
                    ))}
                  </article>
                </div>
              )}
            </details>
          </section>

          <section className="card">
            <details className="advancedSettings">
              <summary>Nachrichtenliste anzeigen</summary>
              <div className="row">
                <button onClick={() => loadInternetAnalysis(symbol)} disabled={loading}>Online-Kontext für {symbol} laden</button>
              </div>
              {activeOnlineAnalysis ? (
                <>
                  <p><strong>{activeOnlineAnalysis.sentiment_label}</strong> · {activeOnlineAnalysis.headline_count} Treffer</p>
                  <p>{activeOnlineAnalysis.summary}</p>
                  <div className="tableScroll">
                    <table>
                      <thead><tr><th align="left">Quelle</th><th align="left">Headline</th><th align="left">Provider</th></tr></thead>
                      <tbody>
                        {researchArticles.map((item, idx) => <tr key={idx}><td>{item.source ?? '-'}</td><td>{item.headline ?? '-'}</td><td>{item.provider ?? '-'}</td></tr>)}
                        {researchArticles.length === 0 && <tr><td colSpan={3}>Keine Artikel im Ergebnis.</td></tr>}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : <p className="muted">Noch keine Online-Analyse geladen.</p>}
            </details>
          </section>
        </div>
      )}

      {view === 'setup' && (
        <div className="stack">
          <section className="setupHero">
            <div>
              <p className="eyebrow">Setup</p>
              <h2>Einrichtung ohne Technik-Suche</h2>
              <p className="muted">{setupGuide.summary ?? 'Status der wichtigsten Anbieter und Sicherheitsoptionen.'}</p>
            </div>
            <span className={`pill ${setupStatusClass(setupGuide.status)}`}>{setupStatusLabel(setupGuide.status)}</span>
          </section>

          <div className="setupGrid">
            {(setupGuide.items ?? []).map((item: any) => (
              <article key={item.key} className={`setupCard ${item.status === 'ready' ? 'ready' : item.status === 'attention' ? 'attention' : ''}`}>
                <div className="stepTop">
                  <h3>{item.title}</h3>
                  <span className={`pill ${setupStatusClass(item.status)}`}>{setupStatusLabel(item.status)}</span>
                </div>
                <p>{item.description}</p>
                <div className="setupMeta">
                  <span>Aktiv</span>
                  <strong>{item.active_value ?? '-'}</strong>
                </div>
                <div className="envList" aria-label={`${item.title} Variablen`}>
                  {(item.env_vars ?? []).map((envVar: string) => <code key={envVar}>{envVar}</code>)}
                </div>
                <p className="muted">{item.next_step}</p>
              </article>
            ))}
          </div>

          <section className="card">
            <h2>Setup-Vorlagen</h2>
            <p className="muted">Kopiere eine Vorlage in deine .env-Datei und ersetze Platzhalter wie DEIN_TWELVE_DATA_KEY durch deinen eigenen Key.</p>
            <div className="profileGrid">
              {(setupGuide.profiles ?? []).map((profile: any) => (
                <article key={profile.key} className="profileCard">
                  <div>
                    <h3>{profile.title}</h3>
                    <p className="muted">{profile.best_for}</p>
                  </div>
                  <p>{profile.description}</p>
                  <pre className="envBlock">{(profile.env_lines ?? []).join('\n')}</pre>
                  <button onClick={() => copySetupProfile(profile)}>Vorlage kopieren</button>
                </article>
              ))}
            </div>
          </section>

          <section className="card">
            <h2>Danach</h2>
            <div className="restartList">
              {(setupGuide.restart_steps ?? []).map((step: string, index: number) => (
                <div key={step} className="restartStep">
                  <span>{index + 1}</span>
                  <p>{step}</p>
                </div>
              ))}
            </div>
            <button onClick={refreshCore}>Setup-Status neu prüfen</button>
          </section>

          <section className="card">
            <h2>Sicherheit</h2>
            <p>API-Keys werden hier nicht angezeigt. Du siehst nur, ob ein Anbieter konfiguriert ist.</p>
            <p className="muted">{setupGuide.secret_note ?? ''}</p>
            <p className="muted">Dateien: {setupGuide.env_file ?? '.env'} und {setupGuide.env_example ?? '.env.example'}</p>
          </section>
        </div>
      )}

      {view === 'watchlist' && (
        <div className="stack">
          <section className={`watchHero ${watchAttention > 0 ? 'attention' : ''}`}>
            <div>
              <p className="eyebrow">Watchlist</p>
              <h2>{watchlist.length ? `${watchlist.length} Asset${watchlist.length === 1 ? '' : 's'} im Blick` : 'Noch keine Watchlist'}</h2>
              <p className="muted">{watchlist.length ? 'Beobachte Kurse, Tagesbewegungen und deine eigenen Alarm-/Zielmarken.' : 'Lege ein erstes Asset an, damit Analyse und Bot schneller starten können.'}</p>
              <div className="botFactRow">
                <span>{watchGainers} steigen</span>
                <span>{watchLosers} fallen</span>
                <span>{watchWithRules} mit Alarm/Ziel</span>
                <span>{watchAttention} nahe Marke</span>
              </div>
            </div>
            <div className="watchActions">
              <button className="primary" onClick={() => { setView('analyse'); loadAnalysis(strongestWatch?.symbol ?? symbol, timeframe); }} disabled={loading}>Auffälliges prüfen</button>
              <button onClick={refreshCore} disabled={loading}>Kurse aktualisieren</button>
              <button onClick={() => setView('bot')}>Bot ansehen</button>
            </div>
          </section>

          <div className="watchSummaryGrid">
            <article className="watchMetricCard">
              <span className="muted">Stärkste Bewegung</span>
              <strong>{strongestWatch?.symbol ?? '-'}</strong>
              <p className={Number(strongestWatch?.change ?? 0) >= 0 ? 'good' : 'bad'}>{number(strongestWatch?.change, 2)}% heute</p>
            </article>
            <article className="watchMetricCard">
              <span className="muted">Mit Regeln</span>
              <strong>{watchWithRules}</strong>
              <p>Alarm oder Ziel hinterlegt</p>
            </article>
            <article className={`watchMetricCard ${watchAttention > 0 ? 'attention' : ''}`}>
              <span className="muted">Nähe zu Marke</span>
              <strong>{watchAttention}</strong>
              <p>Innerhalb von 3% zu Alarm/Ziel</p>
            </article>
            <article className="watchMetricCard">
              <span className="muted">Speicherung</span>
              <strong>{storageLabel}</strong>
              <p>Watchlist bleibt lokal verfügbar</p>
            </article>
          </div>

          <section className="card">
            <div className="guidedHeader">
              <div>
                <p className="eyebrow">Assets</p>
                <h2>Beobachtete Werte</h2>
                <p className="muted">Ein Klick öffnet die Analyse, ohne durch Tabellen zu suchen.</p>
              </div>
              <button onClick={() => addToWatchlist(symbol)} disabled={loading}>Aktuelles Asset merken</button>
            </div>
            {watchlistCards.length ? (
              <div className="watchGrid">
                {watchlistCards.map((item) => (
                  <article key={item.id ?? item.symbol} className={`watchCard ${item.needsAttention ? 'attention' : ''}`}>
                    <div className="stepTop">
                      <h3>{item.symbol}</h3>
                      <span className={`pill ${item.change >= 0 ? 'goodPill' : 'badPill'}`}>{number(item.change, 2)}%</span>
                    </div>
                    <div className="kpi">{number(item.price, item.symbol.includes('/') && item.price < 10 ? 5 : 2)}</div>
                    <p className="muted">{item.name ?? item.note ?? 'Keine Notiz'}</p>
                    <div className="watchMarks">
                      <span>Alarm: <strong>{item.alert_price ?? '-'}</strong></span>
                      <span>Ziel: <strong>{item.target_price ?? '-'}</strong></span>
                    </div>
                    {item.needsAttention && <p className="bad">Nahe an Alarm oder Ziel.</p>}
                    <div className="row">
                      <button className="primary" onClick={() => { setView('analyse'); loadAnalysis(item.symbol); }}>Analysieren</button>
                      <button onClick={() => removeFromWatchlist(item.symbol)}>Entfernen</button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="emptyState">
                <h3>Lege dein erstes Asset an</h3>
                <p className="muted">Nutze z. B. BTC/USD, AAPL, SPY oder EUR/USD.</p>
                <button className="primary" onClick={() => addToWatchlist(symbol)} disabled={loading}>{symbol} merken</button>
              </div>
            )}
          </section>

          <section className="card">
            <details className="advancedSettings">
              <summary>Asset hinzufügen oder Details bearbeiten</summary>
              <div className="watchFormGrid">
                <label>Symbol
                  <input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="BTC/USD, AAPL, EUR/USD" />
                </label>
                <label>Notiz
                  <input value={watchNote} onChange={(event) => setWatchNote(event.target.value)} placeholder="z. B. Ausbruch beobachten" />
                </label>
                <label>Alarmkurs
                  <input value={watchAlert} onChange={(event) => setWatchAlert(event.target.value)} placeholder="optional" />
                </label>
                <label>Zielkurs
                  <input value={watchTarget} onChange={(event) => setWatchTarget(event.target.value)} placeholder="optional" />
                </label>
              </div>
              <div className="row" style={{ marginTop: 12 }}>
                <button className="primary" onClick={() => addToWatchlist(symbol)} disabled={loading}>Hinzufügen / Aktualisieren</button>
                <button onClick={refreshCore} disabled={loading}>Kurse aktualisieren</button>
              </div>
              <div className="tableScroll" style={{ marginTop: 14 }}>
                <table>
                  <thead><tr><th align="left">Asset</th><th align="right">Kurs</th><th align="right">Tag %</th><th align="right">Alarm</th><th align="right">Ziel</th><th align="left">Notiz</th><th /></tr></thead>
                  <tbody>
                    {watchlist.map((item) => (
                      <tr key={item.id ?? item.symbol}>
                        <td>{item.symbol}</td>
                        <td align="right">{number(item.quote?.price, item.symbol.includes('/') && Number(item.quote?.price) < 10 ? 5 : 2)}</td>
                        <td align="right" className={Number(item.quote?.change_percent ?? 0) >= 0 ? 'good' : 'bad'}>{number(item.quote?.change_percent, 2)}%</td>
                        <td align="right">{item.alert_price ?? '-'}</td>
                        <td align="right">{item.target_price ?? '-'}</td>
                        <td>{item.note ?? '-'}</td>
                        <td align="right" className="row" style={{ justifyContent: 'flex-end' }}>
                          <button onClick={() => { setView('analyse'); loadAnalysis(item.symbol); }}>Analysieren</button>
                          <button onClick={() => removeFromWatchlist(item.symbol)}>Entfernen</button>
                        </td>
                      </tr>
                    ))}
                    {watchlist.length === 0 && <tr><td colSpan={7}>Noch keine Watchlist-Einträge.</td></tr>}
                  </tbody>
                </table>
              </div>
            </details>
          </section>
        </div>
      )}

      {view === 'portfolio' && (
        <div className="stack">
          <section className={`accountHero ${accountTone === 'attention' ? 'attention' : ''}`}>
            <div>
              <p className="eyebrow">Paper-Konto</p>
              <h2>{number(currentEquity, 2)} virtuelles Kapital</h2>
              <p className="muted">Alles hier ist simuliert. Echte Ausführung bleibt gesperrt.</p>
              <div className="botFactRow">
                <span>{accountStatus}</span>
                <span>{openTradeCount}/{maxOpenTrades} offene Trades</span>
                <span>{number(usedCapitalPercent, 1)}% gebunden</span>
                <span>{storageLabel}</span>
              </div>
            </div>
            <div className="accountActions">
              <button className="primary" onClick={() => { setView('analyse'); loadAnalysis(symbol, timeframe); }} disabled={loading}>Asset prüfen</button>
              <button onClick={evaluateOrders} disabled={loading}>Orders prüfen</button>
              <button onClick={refreshCore} disabled={loading}>Aktualisieren</button>
            </div>
          </section>

          <section className="accountTradePanel">
            <div>
              <p className="eyebrow">Handeln</p>
              <h2>{symbol} kaufen oder verkaufen</h2>
              <p className="muted">Wähle ein Asset aus der Liste, gib den Paper-Betrag ein und eröffne Long oder Short. Bestehende Positionen kannst du direkt schließen.</p>
              <div className="botFactRow">
                <span>{selectedQuote?.price ? `Kurs ${number(selectedQuote.price, selectedQuote.symbol?.includes('/') && Number(selectedQuote.price) < 10 ? 5 : 2)}` : 'Kurs beim Öffnen geladen'}</span>
                <span>{selectedLongPositions.length} Long · {selectedShortPositions.length} Short</span>
                <span>{number(availableCash, 2)} frei</span>
              </div>
            </div>

            <div className="accountTradeGrid">
              <label>Asset-Gesamtliste
                <select value={selectedSymbolKey} onChange={(event) => setSymbol(event.target.value)}>
                  {DEFAULT_ACCOUNT_ASSET_GROUPS.map((group) => (
                    <optgroup key={group.label} label={group.label}>
                      {group.symbols.map((item) => <option key={`${group.label}-${item}`} value={item}>{item}</option>)}
                    </optgroup>
                  ))}
                  {customAccountAssetOptions.length > 0 && (
                    <optgroup label="Deine Liste & Suche">
                      {customAccountAssetOptions.map((item) => <option key={`custom-${item}`} value={item}>{item}</option>)}
                    </optgroup>
                  )}
                </select>
              </label>
              <label>Oder Symbol direkt eingeben
                <input value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} placeholder="z. B. BTC/USD, AAPL, XAU/USD" />
              </label>
              <label>Positionswert
                <input value={manualNotional} onChange={(event) => setManualNotional(event.target.value)} inputMode="decimal" />
              </label>
              <label>Stop-Loss optional
                <input value={manualStop} onChange={(event) => setManualStop(event.target.value)} placeholder="leer = automatisch" inputMode="decimal" />
              </label>
              <label>Take-Profit optional
                <input value={manualTakeProfit} onChange={(event) => setManualTakeProfit(event.target.value)} placeholder="leer = automatisch" inputMode="decimal" />
              </label>
              <label>Asset suchen
                <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="z. B. apple, gold, btc" />
              </label>
            </div>

            <div className="amountQuickButtons" aria-label="Schnellbeträge">
              {ACCOUNT_TRADE_AMOUNTS.map((amount) => (
                <button
                  key={amount}
                  type="button"
                  className={manualNotionalValue === amount ? 'active' : ''}
                  onClick={() => setManualNotional(String(amount))}
                >
                  {number(amount, 0)}
                </button>
              ))}
            </div>

            <div className="tradePreviewStrip">
              <div>
                <span>Auswahl</span>
                <strong>{selectedSymbolKey || '-'}</strong>
              </div>
              <div>
                <span>Betrag</span>
                <strong>{manualNotionalValue != null ? number(manualNotionalValue, 2) : 'prüfen'}</strong>
              </div>
              <div>
                <span>Menge grob</span>
                <strong>{estimatedQuantity != null ? number(estimatedQuantity, selectedSymbolKey.includes('/') ? 6 : 4) : 'nach Kurs'}</strong>
              </div>
              <div>
                <span>Verkauf möglich</span>
                <strong>{selectedLongPositions.length > 0 ? `${selectedLongPositions.length} Long · ${number(longPositionValue, 2)}` : 'nein'}</strong>
              </div>
              <div>
                <span>Short schließen</span>
                <strong>{selectedShortPositions.length > 0 ? `${selectedShortPositions.length} Short · ${number(shortPositionValue, 2)}` : 'nein'}</strong>
              </div>
            </div>

            {amountAboveCash && (
              <p className="tradeHint bad">Der Betrag liegt über dem freien Paper-Cash. Reduziere den Positionswert oder buche zuerst Paper-Cash ein.</p>
            )}

            <div className={`manualTradeStatus ${canOpenManualTrade ? 'ready' : 'blocked'}`}>
              <div>
                <span>{canOpenManualTrade ? 'Bereit' : 'Blockiert'}</span>
                <strong>{manualTradeStatusTitle}</strong>
                <p>{manualTradeStatusDetail}</p>
              </div>
              <span className={canOpenManualTrade ? 'pill goodPill' : 'pill badPill'}>{openTradeCount}/{maxOpenTrades} offen</span>
            </div>

            <div className="accountTradeActions">
              <button className="primary" onClick={() => createManualOrder('long', 'buy')} disabled={loading || !canOpenManualTrade} title={manualTradeStatusDetail}>Kaufen</button>
              <button className="danger" onClick={() => closeSelectedSidePositions('long')} disabled={loading || selectedLongPositions.length === 0} title={selectedLongPositions.length === 0 ? 'Keine offene Long-Position für dieses Asset' : 'Alle Long-Positionen dieses Assets verkaufen'}>
                Verkaufen
              </button>
              <button onClick={() => createManualOrder('long', 'long')} disabled={loading || !canOpenManualTrade} title={manualTradeStatusDetail}>Long öffnen</button>
              <button onClick={() => createManualOrder('short', 'short')} disabled={loading || !canOpenManualTrade} title={manualTradeStatusDetail}>Short öffnen</button>
              <button onClick={() => closeSelectedSidePositions('short')} disabled={loading || selectedShortPositions.length === 0} title={selectedShortPositions.length === 0 ? 'Keine offene Short-Position für dieses Asset' : 'Alle Short-Positionen dieses Assets schließen'}>
                Short schließen
              </button>
              <button onClick={runSearch} disabled={loading}>Asset suchen</button>
              <button onClick={() => loadAnalysis(symbol, timeframe)} disabled={loading}>Kurs prüfen</button>
            </div>

            {accountConfirmation && (
              <div className={`accountConfirmation ${accountConfirmation.tone}`}>
                <div>
                  <span>{accountConfirmation.meta}</span>
                  <strong>{accountConfirmation.title}</strong>
                  <p>{accountConfirmation.detail}</p>
                </div>
                <button type="button" onClick={() => setAccountConfirmation(null)}>Ausblenden</button>
              </div>
            )}

            {searchResults.length > 0 && (
              <div className="assetChoiceList">
                {searchResults.slice(0, 8).map((item) => (
                  <button key={`${item.symbol}-${item.exchange ?? ''}`} onClick={() => setSymbol(item.symbol.toUpperCase())}>
                    <strong>{item.symbol}</strong>
                    <span>{item.name ?? item.asset_type ?? 'Asset'}</span>
                  </button>
                ))}
              </div>
            )}

            {selectedOpenPositions.length > 0 && (
              <div className="selectedPositionList">
                {selectedOpenPositions.map((item: any) => (
                  <div key={item.id ?? `${item.symbol}-${item.entry_price}`} className="selectedPositionRow">
                    <div>
                      <strong>{item.side === 'short' ? 'Short' : 'Long'} · {number(item.quantity, 6)}</strong>
                      <span className={Number(item.unrealized_pnl_amount ?? 0) >= 0 ? 'good' : 'bad'}>
                        {number(item.unrealized_pnl_amount, 2)} offen · Entry {number(item.entry_price, 4)}
                      </span>
                    </div>
                    <button className="danger" onClick={() => closePaperOrder(String(item.id))} disabled={loading}>
                      {item.side === 'short' ? 'Short schließen' : 'Verkaufen'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          <div className="accountSummaryGrid">
            <article className="accountMetricCard">
              <span className="muted">Verfügbar</span>
              <strong>{number(availableCash, 2)}</strong>
              <p>Freies virtuelles Guthaben</p>
            </article>
            <article className="accountMetricCard">
              <span className="muted">Gebunden</span>
              <strong>{number(openNotional, 2)}</strong>
              <p>In offenen Paper-Positionen</p>
            </article>
            <article className={`accountMetricCard ${paperPnl < 0 ? 'attention' : ''}`}>
              <span className="muted">Gesamt P/L</span>
              <strong className={paperPnl >= 0 ? 'good' : 'bad'}>{number(paperPnl, 2)}</strong>
              <p>{number(paperPnlPercent, 2)}% seit Start</p>
            </article>
            <article className="accountMetricCard">
              <span className="muted">Heute sichtbar</span>
              <strong>{orders.length}</strong>
              <p>Letzte Paper-Orders</p>
            </article>
          </div>

          <section className="accountActivityPanel">
            <div className="guidedHeader">
              <div>
                <p className="eyebrow">Konto-Verlauf</p>
                <h2>Letzte Aktivitäten</h2>
                <p className="muted">Käufe, Verkäufe, Short-Schließungen und Cash-Bewegungen auf einen Blick.</p>
              </div>
              <button onClick={refreshCore} disabled={loading}>Aktualisieren</button>
            </div>
            {accountActivityItems.length > 0 ? (
              <div className="accountActivityList">
                {accountActivityItems.map((item) => (
                  <article key={item.id} className="accountActivityItem">
                    <div>
                      <span className="muted">{shortTime(item.timestamp)} · {item.meta}</span>
                      <strong>{item.title}</strong>
                      <p>{item.detail}</p>
                    </div>
                    <span className={`activityAmount ${item.tone === 'good' ? 'good' : item.tone === 'bad' ? 'bad' : ''}`}>{item.amount}</span>
                  </article>
                ))}
              </div>
            ) : (
              <div className="emptyState">
                <h3>Noch keine Aktivität</h3>
                <p className="muted">Sobald du im Paper-Konto kaufst, verkaufst oder Guthaben bewegst, erscheint es hier.</p>
              </div>
            )}
          </section>

          <section className="card">
            <div className="guidedHeader">
              <div>
                <p className="eyebrow">Positionen</p>
                <h2>Offene Paper-Positionen</h2>
                <p className="muted">Schneller Blick auf Richtung, Stop, Ziel und aktuelles Ergebnis.</p>
              </div>
              <span className={openTradeCount >= maxOpenTrades ? 'pill warnPill' : 'pill goodPill'}>{openTradeCount} offen</span>
            </div>
            {portfolioPositions.length ? (
              <div className="positionGrid">
                {portfolioPositions.slice(0, 6).map((item: any) => (
                  <article key={item.id ?? `${item.symbol}-${item.entry_price}`} className="positionCard">
                    <div className="stepTop">
                      <h3>{item.symbol}</h3>
                      <span className={`pill ${item.side === 'short' ? 'warnPill' : 'goodPill'}`}>{item.side ?? '-'}</span>
                    </div>
                    <div className={Number(item.unrealized_pnl_amount ?? item.pnl_amount ?? 0) >= 0 ? 'kpi good' : 'kpi bad'}>
                      {number(item.unrealized_pnl_amount ?? item.pnl_amount, 2)}
                    </div>
                    <div className="setupMeta">
                      <span>Entry</span>
                      <strong>{number(item.entry_price, 4)}</strong>
                      <span>Aktuell</span>
                      <strong>{number(item.current_price ?? item.entry_price, 4)}</strong>
                      <span>Stop</span>
                      <strong>{number(item.stop_loss, 4)}</strong>
                      <span>Ziel</span>
                      <strong>{number(item.take_profit, 4)}</strong>
                    </div>
                    <div className="positionActions">
                      <button className="danger" onClick={() => closePaperOrder(String(item.id))} disabled={loading}>
                        {item.side === 'short' ? 'Short schließen' : 'Verkaufen'}
                      </button>
                      <button onClick={() => { setSymbol(item.symbol); loadAnalysis(item.symbol, timeframe); }} disabled={loading}>Prüfen</button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="emptyState">
                <h3>Keine offenen Positionen</h3>
                <p className="muted">Wähle oben ein Asset und eröffne einen simulierten Long- oder Short-Trade.</p>
                <button className="primary" onClick={() => createManualOrder('long')} disabled={loading || !canOpenManualTrade} title={manualTradeStatusDetail}>Ersten Kauf testen</button>
              </div>
            )}
          </section>

          <section className="card">
            <details className="advancedSettings">
              <summary>Virtuelles Guthaben verwalten</summary>
              <div className="accountForms">
                <div className="formBlock">
                  <h3>Virtuelles Guthaben</h3>
                  <label>Einzahlung
                    <input value={depositAmount} onChange={(event) => setDepositAmount(event.target.value)} />
                  </label>
                  <button className="primary" onClick={() => cashAction('deposit')} disabled={loading}>Einzahlen</button>
                  <label>Auszahlung
                    <input value={withdrawAmount} onChange={(event) => setWithdrawAmount(event.target.value)} />
                  </label>
                  <button onClick={() => cashAction('withdraw')} disabled={loading}>Auszahlen</button>
                  <label>Konto resetten auf
                    <input value={resetBalance} onChange={(event) => setResetBalance(event.target.value)} />
                  </label>
                  <button onClick={() => cashAction('reset')} disabled={loading}>Paper-Konto resetten</button>
                </div>
              </div>
            </details>
          </section>

          <section className="card">
            <details className="advancedSettings">
              <summary>Historie anzeigen</summary>
              <h3>Cash-Ledger</h3>
              <div className="tableScroll">
                <table>
                  <thead><tr><th align="left">Zeit</th><th align="left">Typ</th><th align="right">Betrag</th><th align="right">Saldo danach</th><th align="left">Notiz</th></tr></thead>
                  <tbody>
                    {cashLedger.map((item, index) => <tr key={item.id ?? index}><td>{String(item.created_at ?? '').slice(0, 19)}</td><td>{item.transaction_type}</td><td align="right">{number(item.amount, 2)}</td><td align="right">{number(item.balance_after, 2)}</td><td>{item.note ?? '-'}</td></tr>)}
                    {cashLedger.length === 0 && <tr><td colSpan={5}>Noch keine Ein-/Auszahlungen.</td></tr>}
                  </tbody>
                </table>
              </div>
              <h3>Paper-Orders</h3>
              <div className="tableScroll">
                <table>
                  <thead><tr><th align="left">Asset</th><th align="left">Richtung</th><th align="left">Quelle</th><th align="right">Menge</th><th align="right">Entry</th><th align="right">Stop</th><th align="right">Ziel</th><th align="left">Status</th></tr></thead>
                  <tbody>
                    {orders.map((item) => <tr key={item.id}><td>{item.symbol}</td><td>{item.side}</td><td>{item.decision_mode ?? item.model_source ?? '-'}</td><td align="right">{number(item.quantity, 6)}</td><td align="right">{number(item.entry_price, 4)}</td><td align="right">{number(item.stop_loss, 4)}</td><td align="right">{number(item.take_profit, 4)}</td><td>{item.status}</td></tr>)}
                    {orders.length === 0 && <tr><td colSpan={8}>Noch keine Paper-Orders.</td></tr>}
                  </tbody>
                </table>
              </div>
            </details>
          </section>
        </div>
      )}


      {view === 'bot' && (
        <div className="stack">
          <section className={`botControlPanel ${botRiskTone === 'danger' ? 'danger' : botRiskTone === 'attention' ? 'attention' : ''}`}>
            <div>
              <p className="eyebrow">Paper-Bot</p>
              <h2>{botStateTitle}</h2>
              <p className="muted">{botStateDetail}</p>
              <div className="botFactRow">
                <span>Echtes Geld: {bot.live_trading_enabled ? 'aktiv' : 'gesperrt'}</span>
                <span>{botSymbols.length} Asset{botSymbols.length === 1 ? '' : 's'}</span>
                <span>{botTimeframes.join(', ')}</span>
                <span>{botConfig.persistence ?? 'lokal'}</span>
              </div>
            </div>
            <div className="botMainActions">
              <button className="primary botPrimaryButton" onClick={botPrimaryAction} disabled={loading}>{botPrimaryLabel}</button>
              <button onClick={() => schedulerAction('run-once')} disabled={loading || killSwitchActive}>Einmal testen</button>
              <button className="danger" onClick={activateKillSwitch} disabled={loading || killSwitchActive}>Sofort stoppen</button>
            </div>
          </section>

          <div className="botOverviewGrid">
            <article className="botInfoCard">
              <span className="muted">Automatik</span>
              <strong>{schedulerRunning ? 'Läuft' : botEnabled ? 'Bereit' : 'Aus'}</strong>
              <p>{latestSchedulerRun ? `Letzter Lauf: ${String(latestSchedulerRun.created_at ?? latestSchedulerRun.status ?? '').slice(0, 19)}` : 'Noch kein automatischer Lauf.'}</p>
            </article>
            <article className={`botInfoCard ${botRiskTone === 'attention' ? 'attention' : botRiskTone === 'danger' ? 'danger' : ''}`}>
              <span className="muted">Risiko-Ampel</span>
              <strong>{botRiskLabel}</strong>
              <p>{openTradeCount}/{maxOpenTrades} offene Trades · {percent(botConfig.max_risk_per_trade ?? bot.max_risk_per_trade)} je Trade</p>
            </article>
            <article className="botInfoCard">
              <span className="muted">Letzte Entscheidung</span>
              <strong>{latestDecisionLabel}</strong>
              <p>{latestDecisionDetail}</p>
            </article>
            <article className="botInfoCard">
              <span className="muted">Modus</span>
              <strong>{decisionMode === 'rule' ? 'Regeln' : decisionMode === 'ml' ? 'ML-Filter' : 'Ensemble'}</strong>
              <p>{strategyName} · {timeframe}</p>
            </article>
          </div>

          <section className="card">
            <div className="guidedHeader">
              <div>
                <p className="eyebrow">Schnelltest</p>
                <h2>Eine Bot-Entscheidung prüfen</h2>
                <p className="muted">Lädt eine Paper-Entscheidung für das aktuelle Asset und wertet offene Orders aus.</p>
              </div>
              <span className={botCanTrade && !killSwitchActive ? 'pill goodPill' : 'pill warnPill'}>{botCanTrade && !killSwitchActive ? 'Test bereit' : 'Blockiert'}</span>
            </div>
            <div className="botTestGrid">
              <label>Asset
                <input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="BTC/USD, AAPL, SPY" />
              </label>
              <label>Zeitrahmen
                <select value={timeframe} onChange={(event) => setTimeframe(event.target.value)}>
                  <option value="1m">1m</option>
                  <option value="5m">5m</option>
                  <option value="15m">15m</option>
                  <option value="1h">1h</option>
                  <option value="4h">4h</option>
                  <option value="1D">1D</option>
                </select>
              </label>
              <label>Entscheidung
                <select value={decisionMode} onChange={(event) => setDecisionMode(event.target.value)}>
                  <option value="rule">Regeln</option>
                  <option value="ml">ML-Filter</option>
                  <option value="ensemble">Ensemble</option>
                </select>
              </label>
              <label>Modell optional
                <input value={modelId} onChange={(event) => setModelId(event.target.value)} placeholder="leer = neuestes Modell" />
              </label>
            </div>
            <div className="row" style={{ marginTop: 12 }}>
              <button className="primary" onClick={() => runBotCycle(symbol)} disabled={loading || !botCanTrade || killSwitchActive}>Testlauf für {symbol}</button>
              <button onClick={evaluateOrders} disabled={loading}>Offene Orders prüfen</button>
              <button onClick={() => setView('monitoring')}>Risiko ansehen</button>
            </div>
          </section>

          <BotStatusCard bot={bot as any} />

          <section className="card">
            <details className="advancedSettings">
              <summary>Feinsteuerung anzeigen</summary>
              <div className="grid">
                <label>Bot aktiv
                  <select value={String(botConfig.bot_enabled ?? false)} onChange={(event) => saveBotConfig({ bot_enabled: event.target.value === 'true' })}>
                    <option value="false">Nein</option>
                    <option value="true">Ja, Paper-only</option>
                  </select>
                </label>
                <label>Intervall Sekunden
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
                <label>Validierung erzwingen
                  <select value={String(botConfig.enforce_validation_gate ?? false)} onChange={(event) => setBotConfig({ ...botConfig, enforce_validation_gate: event.target.value === 'true' })}>
                    <option value="false">Nein</option>
                    <option value="true">Ja, Bot blockieren wenn nicht freigegeben</option>
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
                <button className="primary" onClick={() => saveBotConfig(botConfig)}>Einstellungen speichern</button>
                <button onClick={() => schedulerAction('start')} disabled={loading}>Automatik starten</button>
                <button onClick={() => schedulerAction('stop')} disabled={loading}>Automatik stoppen</button>
                <button onClick={resetKillSwitch} disabled={loading}>Schutzstopp lösen</button>
              </div>
              <p className="muted">Automatik: {schedulerStatus.status ?? 'unbekannt'} · Speicher: {botConfig.persistence ?? 'memory'} · Schutzstopp: {killSwitchActive ? 'aktiv' : 'aus'}</p>
            </details>
          </section>

          <section className="card">
            <h2>Equity-Kurve</h2>
            <EquityCurve points={(equityCurve ?? []).map((item: any, index: number) => ({ timestamp: item.timestamp ?? `P${index}`, equity: Number(item.equity ?? 0), event: item.symbol }))} />
          </section>

          <section className="card">
            <h2>Bot-Protokoll</h2>
            <div className="grid">
              <div className="tableScroll">
                <table>
                  <thead><tr><th align="left">Zeit</th><th align="left">Asset</th><th align="left">Modus</th><th align="left">Erlaubt</th><th align="left">Grund</th></tr></thead>
                  <tbody>
                    {decisionAudits.map((item) => <tr key={item.id}><td>{String(item.created_at ?? '').slice(0, 19)}</td><td>{item.symbol}</td><td>{item.decision_mode}</td><td>{item.allowed ? 'Ja' : 'Nein'}</td><td>{item.reason}</td></tr>)}
                    {decisionAudits.length === 0 && <tr><td colSpan={5}>Noch keine Bot-Entscheidungen protokolliert.</td></tr>}
                  </tbody>
                </table>
              </div>
              <div className="tableScroll">
                <table>
                  <thead><tr><th align="left">Zeit</th><th align="left">Quelle</th><th align="left">Status</th><th align="left">Assets</th></tr></thead>
                  <tbody>
                    {schedulerRuns.map((item) => <tr key={item.id ?? item.created_at}><td>{String(item.created_at ?? '').slice(0, 19)}</td><td>{item.source}</td><td>{item.status}</td><td>{(item.symbols ?? []).join(', ')}</td></tr>)}
                    {schedulerRuns.length === 0 && <tr><td colSpan={4}>Noch keine automatischen Läufe.</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <section className="card">
            <h2>ML-/Ensemble-Status</h2>
            <p>Status: {modelHealth.status ?? 'unbekannt'}</p>
            <p>Health: {modelHealth.health?.healthy ? 'ok' : (modelHealth.health?.reason ?? modelHealth.reason ?? 'kein Modell')}</p>
            <p>Aktuelles Modell: {modelHealth.health?.model_id ?? modelHealth.selected_model?.model_id ?? '-'}</p>
            <h3>Performance nach Entscheidungsmodus</h3>
            <div className="tableScroll">
              <table>
                <thead><tr><th align="left">Modus</th><th align="right">Orders</th><th align="right">Winrate</th><th align="right">PF</th><th align="right">P/L</th></tr></thead>
                <tbody>
                  {performanceByMode.map((item) => <tr key={item.decision_mode}><td>{item.decision_mode}</td><td align="right">{item.total_orders}</td><td align="right">{number(item.win_rate_percent, 1)}%</td><td align="right">{item.profit_factor ?? '-'}</td><td align="right">{number(item.total_realized_pnl, 2)}</td></tr>)}
                  {performanceByMode.length === 0 && <tr><td colSpan={5}>Noch keine Modus-Auswertung.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card">
            <h2>Offene Positionen</h2>
            <div className="tableScroll">
              <table>
                <thead><tr><th align="left">Asset</th><th align="left">Richtung</th><th align="right">Entry</th><th align="right">Aktuell</th><th align="right">Stop</th><th align="right">Ziel</th><th align="right">Unreal. P/L</th></tr></thead>
                <tbody>
                  {(portfolio.positions ?? []).map((item: any) => (
                    <tr key={item.id}><td>{item.symbol}</td><td>{item.side}</td><td align="right">{number(item.entry_price, 4)}</td><td align="right">{number(item.current_price, 4)}</td><td align="right">{number(item.stop_loss, 4)}</td><td align="right">{number(item.take_profit, 4)}</td><td align="right">{number(item.unrealized_pnl_amount, 2)}</td></tr>
                  ))}
                  {(portfolio.positions ?? []).length === 0 && <tr><td colSpan={7}>Keine offenen Paper-Positionen.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card">
            <h2>Letzte Orders</h2>
            <div className="tableScroll">
              <table>
                <thead><tr><th align="left">Asset</th><th align="left">Richtung</th><th align="left">Modus</th><th align="right">Entry</th><th align="right">Stop</th><th align="right">Ziel</th><th align="right">P/L</th><th align="left">Status</th></tr></thead>
                <tbody>
                  {orders.map((item) => <tr key={item.id}><td>{item.symbol}</td><td>{item.side}</td><td>{item.decision_mode ?? '-'}</td><td align="right">{number(item.entry_price, 4)}</td><td align="right">{number(item.stop_loss, 4)}</td><td align="right">{number(item.take_profit, 4)}</td><td align="right">{item.pnl_amount == null ? '-' : number(item.pnl_amount, 2)}</td><td>{item.status}</td></tr>)}
                  {orders.length === 0 && <tr><td colSpan={8}>Noch keine Paper-Orders.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card">
            <h2>Letzte Signale & Risiko-Events</h2>
            <div className="grid">
              <div className="tableScroll">
                <table>
                  <tbody>
                    {signals.map((item) => <tr key={item.id}><td>{item.symbol}</td><td>{item.signal_type}</td><td>{number(item.signal_score, 0)}</td><td>{item.status}</td></tr>)}
                    {signals.length === 0 && <tr><td>Keine aktuellen Signale.</td></tr>}
                  </tbody>
                </table>
              </div>
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
