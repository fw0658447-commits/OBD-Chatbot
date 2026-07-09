'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiPatch, apiPost } from '../lib/api';

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

type AutomationPair = {
  symbol: string;
  timeframe: string;
};

type AutomationCurrentRun = {
  id?: string;
  status?: string;
  source?: string;
  phase?: string;
  started_at?: string;
  finished_at?: string;
  completed_steps?: number;
  total_steps?: number;
  cancel_requested?: boolean;
  current_item?: {
    type?: string;
    model_type?: string;
    limit?: number;
    lookahead_bars?: number;
    symbol?: string;
    timeframe?: string;
    strategy?: string;
    objective?: string;
  } | null;
};

type AutomationRunPlan = {
  search_profile?: string;
  effective_search_profile?: string;
  profile_reason?: string;
  model_tests?: number;
  asset_tests?: number;
  strategy_tests?: number;
  objective_tests?: number;
  optimization_tests?: number;
  total_steps?: number;
  estimated_parameter_tests?: number;
};

type AutomationRun = {
  id?: string;
  status?: string;
  source?: string;
  started_at?: string;
  finished_at?: string;
  selected_pairs?: AutomationPair[];
  model?: {
    model_id?: string;
    model_type?: string;
    row_count?: number;
    accuracy?: number;
    rule_accuracy?: number;
    profit_factor?: number | null;
    win_rate_percent?: number;
  } | null;
  bot_model_update?: {
    enabled?: boolean;
    status?: string;
    model_id?: string;
    strategy_name?: string;
    recommended_params?: Record<string, unknown>;
    decision_mode?: string;
    persistence?: string;
    detail?: string;
    reason?: string;
    quality_gate?: {
      enabled?: boolean;
      passed?: boolean;
      reason?: string;
      checks?: Array<{ name?: string; passed?: boolean; actual?: number | null; minimum?: number | null }>;
    };
  } | null;
  model_candidates?: Array<{
    model_id?: string;
    model_type?: string;
    score?: number;
    accuracy?: number;
    candidate?: { model_type?: string; limit?: number; lookahead_bars?: number };
  }>;
  champion?: {
    status?: string;
    score?: number;
    model_id?: string;
    model_type?: string;
    symbol?: string;
    timeframe?: string;
    strategy?: string;
    objective?: string;
    metrics?: {
      return_percent?: number;
      profit_factor?: number | null;
      win_rate_percent?: number;
    };
  };
  asset_expansion?: {
    enabled?: boolean;
    seed_symbols?: string[];
    active_symbols?: string[];
    active_count?: number;
  };
  optimizations?: Array<{
    symbol?: string;
    timeframe?: string;
    strategy?: string;
    best_score?: number;
    tested_combinations?: number;
    metrics?: {
      return_percent?: number;
      profit_factor?: number | null;
      win_rate_percent?: number;
      max_drawdown_percent?: number;
      trades?: number;
    };
  }>;
  best?: {
    symbol?: string;
    timeframe?: string;
    strategy?: string;
    best_score?: number;
    metrics?: {
      return_percent?: number;
      profit_factor?: number | null;
      win_rate_percent?: number;
      max_drawdown_percent?: number;
      trades?: number;
    };
  } | null;
  run_plan?: AutomationRunPlan;
  errors?: Array<{ stage?: string; detail?: string; symbol?: string; timeframe?: string; strategy?: string }>;
};

type AutomationStatus = {
  status?: string;
  thread_alive?: boolean;
  started_at?: string | null;
  paper_only?: boolean;
  live_trading_enabled?: boolean;
  config?: any;
  asset_expansion?: {
    enabled?: boolean;
    seed_symbols?: string[];
    active_symbols?: string[];
    active_count?: number;
    max_auto_assets?: number;
  };
  bot_model?: {
    model_id?: string | null;
    decision_mode?: string;
    persistence?: string;
    live_trading_enabled?: boolean;
  };
  current_run?: AutomationCurrentRun | null;
  run_plan?: AutomationRunPlan;
  next_pairs?: AutomationPair[];
  last_run?: AutomationRun | null;
  recent_runs?: AutomationRun[];
};

function number(value: unknown, digits = 4) {
  return Number(value ?? 0).toFixed(digits);
}

function errorDetail(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

function textList(value: string) {
  return value
    .replaceAll('\n', ',')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function numberList(value: string) {
  return textList(value)
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item));
}

function pairText(pairs?: AutomationPair[]) {
  if (!pairs?.length) return '-';
  return pairs.map((pair) => `${pair.symbol} ${pair.timeframe}`).join(' · ');
}

function statusText(status?: string) {
  if (status === 'completed') return 'Fertig';
  if (status === 'completed_with_warnings') return 'Mit Hinweisen';
  if (status === 'failed') return 'Fehlgeschlagen';
  if (status === 'busy') return 'Läuft gerade';
  if (status === 'starting') return 'Startet';
  if (status === 'started') return 'Gestartet';
  if (status === 'running') return 'Läuft';
  if (status === 'cancelling') return 'Stoppt';
  if (status === 'cancelled') return 'Gestoppt';
  if (status === 'skipped') return 'Pausiert';
  if (status === 'updated') return 'Aktualisiert';
  if (status === 'blocked') return 'Blockiert';
  return status || '-';
}

function currentItemText(item?: AutomationCurrentRun['current_item']) {
  if (!item) return 'Bereitet den nächsten Test vor';
  if (item.type === 'model') {
    return `${item.model_type?.replaceAll('_', ' ') ?? 'Modell'} · ${item.limit ?? '-'} Kerzen · Lookahead ${item.lookahead_bars ?? '-'}`;
  }
  if (item.type === 'optimization') {
    return `${item.symbol ?? '-'} ${item.timeframe ?? ''} · ${item.strategy ?? '-'} · ${item.objective ?? '-'}`;
  }
  return 'Lauf aktiv';
}

const AUTOMATION_PROFILE_PRESETS = {
  auto: {
    label: 'Auto',
    description: 'Wählt selbst'
  },
  fast: {
    label: 'Schnell',
    description: 'Kompakter Lauf',
    patch: {
      interval_minutes: 180,
      assets_per_run: 1,
      max_auto_assets: 6,
      max_model_candidates: 2,
      model_type_candidates: ['random_forest'],
      training_limit_candidates: [360, 560],
      lookahead_candidates: [6, 12],
      optimization_limit: 260,
      max_combinations: 8,
      full_strategy_search: false,
      strategies_per_asset: 1,
      auto_objective_search: false,
      optimization_objectives: ['robust_score'],
      min_model_accuracy: 0.5,
      min_model_win_rate_percent: 40,
      min_model_profit_factor: 0
    }
  },
  balanced: {
    label: 'Ausgewogen',
    description: 'Standardlauf',
    patch: {
      interval_minutes: 360,
      assets_per_run: 2,
      max_auto_assets: 12,
      max_model_candidates: 4,
      model_type_candidates: ['random_forest', 'logistic_regression'],
      training_limit_candidates: [420, 560, 720],
      lookahead_candidates: [6, 12, 24],
      optimization_limit: 360,
      max_combinations: 14,
      full_strategy_search: true,
      strategies_per_asset: 2,
      auto_objective_search: true,
      optimization_objectives: ['robust_score', 'profit_factor', 'return_percent'],
      min_model_accuracy: 0.5,
      min_model_win_rate_percent: 40,
      min_model_profit_factor: 0
    }
  },
  deep: {
    label: 'Gründlich',
    description: 'Breiter Lauf',
    patch: {
      interval_minutes: 720,
      assets_per_run: 3,
      max_auto_assets: 18,
      max_model_candidates: 8,
      model_type_candidates: ['random_forest', 'logistic_regression'],
      training_limit_candidates: [360, 560, 720, 960],
      lookahead_candidates: [6, 12, 24, 36],
      optimization_limit: 520,
      max_combinations: 28,
      full_strategy_search: true,
      strategies_per_asset: 3,
      auto_objective_search: true,
      optimization_objectives: ['robust_score', 'profit_factor', 'return_percent'],
      min_model_accuracy: 0.52,
      min_model_win_rate_percent: 42,
      min_model_profit_factor: 0
    }
  }
} as const;

type AutomationProfileId = keyof typeof AUTOMATION_PROFILE_PRESETS;

export function MLPanel({ defaultSymbol = 'BTC/USD', defaultTimeframe = '1h' }: { defaultSymbol?: string; defaultTimeframe?: string }) {
  const [symbol, setSymbol] = useState(defaultSymbol);
  const [timeframe, setTimeframe] = useState(defaultTimeframe);
  const [modelType, setModelType] = useState('random_forest');
  const [limit, setLimit] = useState(650);
  const [result, setResult] = useState<MLTrainResult>({});
  const [assetPrediction, setAssetPrediction] = useState<any>({});
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyLabel, setBusyLabel] = useState('');
  const [message, setMessage] = useState('');
  const [automationStatus, setAutomationStatus] = useState<AutomationStatus | null>(null);
  const [autoSearchProfile, setAutoSearchProfile] = useState<AutomationProfileId>('balanced');
  const [autoSymbols, setAutoSymbols] = useState('BTC/USD, ETH/USD, AAPL, SPY');
  const [autoTimeframes, setAutoTimeframes] = useState('1h');
  const [autoStrategies, setAutoStrategies] = useState('trend_atr_v0.7, pullback_ema_v0.7, breakout_range_v0.7');
  const [autoInterval, setAutoInterval] = useState(360);
  const [autoAssetsPerRun, setAutoAssetsPerRun] = useState(2);
  const [autoMaxCombinations, setAutoMaxCombinations] = useState(14);
  const [autoModelType, setAutoModelType] = useState('random_forest');
  const [autoModelCandidates, setAutoModelCandidates] = useState('random_forest, logistic_regression');
  const [autoTrainingLimits, setAutoTrainingLimits] = useState('420, 560, 720');
  const [autoLookaheads, setAutoLookaheads] = useState('6, 12, 24');
  const [autoOptimizationObjectives, setAutoOptimizationObjectives] = useState('robust_score, profit_factor, return_percent');
  const [autoMaxModelCandidates, setAutoMaxModelCandidates] = useState(4);
  const [autoLimit, setAutoLimit] = useState(560);
  const [autoOptimizationLimit, setAutoOptimizationLimit] = useState(360);
  const [autoExpandAssets, setAutoExpandAssets] = useState(true);
  const [autoAssetUniverse, setAutoAssetUniverse] = useState('BTC/USD, ETH/USD, SOL/USD, BNB/USD, XRP/USD, AAPL, MSFT, NVDA, TSLA, SPY, QQQ, IWM, EUR/USD, GBP/USD, USD/JPY, XAU/USD, XAG/USD');
  const [autoMaxAssets, setAutoMaxAssets] = useState(12);
  const [autoFullStrategySearch, setAutoFullStrategySearch] = useState(true);
  const [autoObjectiveSearch, setAutoObjectiveSearch] = useState(true);
  const [autoUpdateBotModel, setAutoUpdateBotModel] = useState(true);
  const [autoUpdateBotStrategy, setAutoUpdateBotStrategy] = useState(true);
  const [autoQualityGateEnabled, setAutoQualityGateEnabled] = useState(true);
  const [autoRequireBeatsRule, setAutoRequireBeatsRule] = useState(true);
  const [autoMinAccuracy, setAutoMinAccuracy] = useState(0.5);
  const [autoMinWinRate, setAutoMinWinRate] = useState(40);
  const [autoMinProfitFactor, setAutoMinProfitFactor] = useState(0);

  async function loadModels() {
    const data = await apiGet<any>('/api/ml/models?limit=10', { items: [], database_items: [] });
    setModels(data.items?.length ? data.items : (data.database_items ?? []));
  }

  async function loadAutomation() {
    const data = await apiGet<AutomationStatus>('/api/ml/automation/status', {
      status: 'stopped',
      config: {},
      next_pairs: [],
      recent_runs: [],
      last_run: null,
      paper_only: true,
      live_trading_enabled: false
    });
    setAutomationStatus(data);
    const config = data.config ?? {};
    if (config.search_profile && AUTOMATION_PROFILE_PRESETS[config.search_profile as AutomationProfileId]) {
      setAutoSearchProfile(config.search_profile as AutomationProfileId);
    }
    if (Array.isArray(config.symbols)) setAutoSymbols(config.symbols.join(', '));
    if (Array.isArray(config.timeframes)) setAutoTimeframes(config.timeframes.join(', '));
    if (Array.isArray(config.strategies)) setAutoStrategies(config.strategies.join(', '));
    if (Array.isArray(config.model_type_candidates)) setAutoModelCandidates(config.model_type_candidates.join(', '));
    if (Array.isArray(config.training_limit_candidates)) setAutoTrainingLimits(config.training_limit_candidates.join(', '));
    if (Array.isArray(config.lookahead_candidates)) setAutoLookaheads(config.lookahead_candidates.join(', '));
    if (Array.isArray(config.optimization_objectives)) setAutoOptimizationObjectives(config.optimization_objectives.join(', '));
    if (Array.isArray(config.asset_universe)) setAutoAssetUniverse(config.asset_universe.join(', '));
    if (Number.isFinite(Number(config.interval_minutes))) setAutoInterval(Number(config.interval_minutes));
    if (Number.isFinite(Number(config.assets_per_run))) setAutoAssetsPerRun(Number(config.assets_per_run));
    if (Number.isFinite(Number(config.max_auto_assets))) setAutoMaxAssets(Number(config.max_auto_assets));
    if (Number.isFinite(Number(config.max_model_candidates))) setAutoMaxModelCandidates(Number(config.max_model_candidates));
    if (Number.isFinite(Number(config.max_combinations))) setAutoMaxCombinations(Number(config.max_combinations));
    if (config.model_type) setAutoModelType(String(config.model_type));
    if (Number.isFinite(Number(config.limit))) setAutoLimit(Number(config.limit));
    if (Number.isFinite(Number(config.optimization_limit))) setAutoOptimizationLimit(Number(config.optimization_limit));
    if (typeof config.auto_expand_assets === 'boolean') setAutoExpandAssets(config.auto_expand_assets);
    if (typeof config.full_strategy_search === 'boolean') setAutoFullStrategySearch(config.full_strategy_search);
    if (typeof config.auto_objective_search === 'boolean') setAutoObjectiveSearch(config.auto_objective_search);
    if (typeof config.auto_update_bot_model === 'boolean') setAutoUpdateBotModel(config.auto_update_bot_model);
    if (typeof config.auto_update_bot_strategy === 'boolean') setAutoUpdateBotStrategy(config.auto_update_bot_strategy);
    if (typeof config.quality_gate_enabled === 'boolean') setAutoQualityGateEnabled(config.quality_gate_enabled);
    if (typeof config.quality_require_beats_rule === 'boolean') setAutoRequireBeatsRule(config.quality_require_beats_rule);
    if (Number.isFinite(Number(config.min_model_accuracy))) setAutoMinAccuracy(Number(config.min_model_accuracy));
    if (Number.isFinite(Number(config.min_model_win_rate_percent))) setAutoMinWinRate(Number(config.min_model_win_rate_percent));
    if (Number.isFinite(Number(config.min_model_profit_factor))) setAutoMinProfitFactor(Number(config.min_model_profit_factor));
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

  function validateModelSettings() {
    if (!symbol.trim()) {
      setMessage('Bitte ein Asset eingeben.');
      return false;
    }
    if (!Number.isFinite(limit) || limit < 180) {
      setMessage('Bitte mindestens 180 Kerzen wählen.');
      return false;
    }
    return true;
  }

  async function trainModel() {
    if (!validateModelSettings()) return;
    await runBusy('Modell wird trainiert', async () => {
      setMessage('');
      const data = await apiPost<MLTrainResult>('/api/ml/train', {
        symbols: [symbol.trim(), 'ETH/USD', 'AAPL', 'SPY'],
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
    });
  }

  async function predictAsset(modelId?: string) {
    if (!validateModelSettings()) return;
    await runBusy('Prognose wird geladen', async () => {
      const data = await apiPost<any>('/api/ml/predict-asset', {
        model_id: modelId || result.model_id || undefined,
        symbol: symbol.trim(),
        timeframe,
        strategy_name: 'trend_atr_v0.7',
        limit: 240
      }, { ml_prediction: null });
      setAssetPrediction(data);
      setMessage(data.ml_prediction ? 'Prognose geladen.' : 'Noch keine Prognose verfügbar.');
    });
  }

  async function compareRuleVsML() {
    if (!validateModelSettings()) return;
    await runBusy('Regeln und Modell werden verglichen', async () => {
      const data = await apiPost<MLTrainResult>('/api/ml/compare-rule-vs-ml', {
        symbols: [symbol.trim(), 'ETH/USD', 'AAPL', 'SPY'],
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
    });
  }

  function automationPayload() {
    return {
      search_profile: autoSearchProfile,
      symbols: textList(autoSymbols),
      timeframes: textList(autoTimeframes),
      strategies: textList(autoStrategies),
      interval_minutes: autoInterval,
      assets_per_run: autoAssetsPerRun,
      auto_expand_assets: autoExpandAssets,
      asset_universe: textList(autoAssetUniverse),
      max_auto_assets: autoMaxAssets,
      max_combinations: autoMaxCombinations,
      model_type: autoModelType,
      model_type_candidates: textList(autoModelCandidates),
      training_limit_candidates: numberList(autoTrainingLimits),
      lookahead_candidates: numberList(autoLookaheads),
      max_model_candidates: autoMaxModelCandidates,
      limit: autoLimit,
      optimization_limit: autoOptimizationLimit,
      full_strategy_search: autoFullStrategySearch,
      optimization_objectives: textList(autoOptimizationObjectives),
      auto_objective_search: autoObjectiveSearch,
      auto_update_bot_model: autoUpdateBotModel,
      auto_update_bot_strategy: autoUpdateBotStrategy,
      quality_gate_enabled: autoQualityGateEnabled,
      quality_require_beats_rule: autoRequireBeatsRule,
      min_model_accuracy: autoMinAccuracy,
      min_model_win_rate_percent: autoMinWinRate,
      min_model_profit_factor: autoMinProfitFactor
    };
  }

  async function applyAutomationProfile(profile: AutomationProfileId) {
    setAutoSearchProfile(profile);
    await runBusy('Suchprofil wird gespeichert', async () => {
      const data = await apiPatch<AutomationStatus>('/api/ml/automation/config', {
        search_profile: profile,
        apply_search_profile: true,
        auto_expand_assets: true
      }, { status: 'error', config: {} });
      setAutomationStatus(data);
      setMessage((data as any).error ? `Profil fehlgeschlagen: ${(data as any).detail}` : `Suchprofil ${AUTOMATION_PROFILE_PRESETS[profile].label} aktiv.`);
      await loadAutomation();
    });
  }

  async function saveAutomationConfig() {
    await runBusy('Automatik wird gespeichert', async () => {
      const data = await apiPatch<AutomationStatus>('/api/ml/automation/config', automationPayload(), { status: 'error', config: {} });
      setAutomationStatus(data);
      setMessage((data as any).error ? `Speichern fehlgeschlagen: ${(data as any).detail}` : 'Automatik-Einstellungen gespeichert.');
    });
  }

  async function automationCommand(action: 'start' | 'stop' | 'run' | 'cancel') {
    const label = action === 'run'
      ? 'Optimierung läuft'
      : action === 'start'
        ? 'Automatik wird gestartet'
        : action === 'cancel'
          ? 'Lauf wird gestoppt'
          : 'Automatik wird pausiert';
    await runBusy(label, async () => {
      if (action !== 'stop' && action !== 'cancel') {
        await apiPatch<AutomationStatus>('/api/ml/automation/config', automationPayload(), { status: 'error', config: {} });
      }
      const path = action === 'run' ? '/api/ml/automation/run-background' : `/api/ml/automation/${action}`;
      const data = await apiPost<any>(path, action === 'run' ? { config_patch: automationPayload() } : {}, { status: 'error' });
      if (data.error) {
        setMessage(`Automatik fehlgeschlagen: ${data.detail}`);
        return;
      }
      if (action === 'run') {
        setMessage(data.status === 'busy' ? 'Es läuft bereits eine Optimierung.' : 'Optimierung im Hintergrund gestartet.');
      } else if (action === 'cancel') {
        setMessage('Lauf wird gestoppt.');
      } else {
        setMessage(action === 'start' ? 'Automatik gestartet.' : 'Automatik pausiert.');
      }
      await loadAutomation();
      await loadModels();
    });
  }

  useEffect(() => { loadModels(); loadAutomation(); }, []);

  const mlAccuracy = result.metrics?.accuracy;
  const ruleAccuracy = result.rule_baseline_metrics?.accuracy;
  const prediction = assetPrediction.ml_prediction;
  const hasModelResult = Boolean(result.model_id || result.metrics || result.trading_metrics);
  const mlAccuracyNumber = Number(mlAccuracy ?? 0);
  const ruleAccuracyNumber = Number(ruleAccuracy ?? 0);
  const modelTone = !hasModelResult ? 'attention' : mlAccuracyNumber >= ruleAccuracyNumber ? 'ready' : 'attention';
  const modelTitle = !hasModelResult
    ? 'Modell trainieren'
    : mlAccuracyNumber >= ruleAccuracyNumber
      ? 'ML schlägt Regelmodell'
      : 'Regelmodell bleibt stärker';
  const latestModel = models[0];
  const topFeature = result.feature_importance?.[0];
  const messageLooksProblematic = message.toLowerCase().includes('fehl') || message.toLowerCase().includes('error') || message.toLowerCase().includes('problem');
  const automationRunning = automationStatus?.status === 'running';
  const currentAutomationRun = automationStatus?.current_run;
  const currentCompleted = Number(currentAutomationRun?.completed_steps ?? 0);
  const currentTotal = Number(currentAutomationRun?.total_steps ?? 0);
  const currentProgressPercent = currentTotal > 0 ? Math.min(100, Math.round((currentCompleted / currentTotal) * 100)) : 0;
  const lastAutoRun = automationStatus?.last_run;
  const autoRunPlan = automationStatus?.run_plan ?? lastAutoRun?.run_plan;
  const autoBest = lastAutoRun?.best;
  const autoModel = lastAutoRun?.model;
  const autoChampion = lastAutoRun?.champion;
  const activeAutoAssetCount = automationStatus?.asset_expansion?.active_count ?? lastAutoRun?.asset_expansion?.active_count ?? textList(autoSymbols).length;
  const modelCandidateCount = lastAutoRun?.model_candidates?.length ?? 0;
  const botModelUpdate = lastAutoRun?.bot_model_update;
  const qualityGate = botModelUpdate?.quality_gate;
  const activeBotModelId = botModelUpdate?.model_id ?? automationStatus?.bot_model?.model_id;
  const autoWarnings = lastAutoRun?.errors ?? [];
  const autoTone = automationRunning || currentAutomationRun || lastAutoRun?.status === 'completed' ? 'ready' : 'attention';
  const activeProfile = AUTOMATION_PROFILE_PRESETS[autoSearchProfile] ?? AUTOMATION_PROFILE_PRESETS.balanced;
  const effectiveProfileId = (autoRunPlan?.effective_search_profile ?? autoSearchProfile) as AutomationProfileId;
  const effectiveProfile = AUTOMATION_PROFILE_PRESETS[effectiveProfileId] ?? activeProfile;
  const profileSummary = autoSearchProfile === 'auto'
    ? `Auto nutzt ${effectiveProfile.label}`
    : activeProfile.label;

  useEffect(() => {
    if (!automationRunning && !currentAutomationRun) return;
    const intervalId = window.setInterval(() => {
      loadAutomation();
      loadModels();
    }, 4000);
    return () => window.clearInterval(intervalId);
  }, [automationRunning, currentAutomationRun?.id, currentAutomationRun?.status]);

  return (
    <div className="stack">
      {(message || busyLabel) && (
        <section className={`statusBanner ${messageLooksProblematic ? 'attention' : ''}`} role="status" aria-live="polite">
          <strong>{busyLabel || 'Status'}</strong>
          {message && <p>{message}</p>}
        </section>
      )}

      <section className={`modelHero ${modelTone === 'attention' ? 'attention' : ''}`}>
        <div>
          <p className="eyebrow">Modell-Assistent</p>
          <h2>{modelTitle}</h2>
          <p className="muted">Trainiere und vergleiche ein Modell nur im Paper-Kontext. Live-Trading bleibt gesperrt.</p>
          <div className="botFactRow">
            <span>{symbol}</span>
            <span>{timeframe}</span>
            <span>{modelType.replaceAll('_', ' ')}</span>
            <span>{limit} Kerzen</span>
          </div>
        </div>
        <div className="modelActions">
          <button className="primary" onClick={trainModel} disabled={loading}>Modell trainieren</button>
          <button onClick={compareRuleVsML} disabled={loading}>Regeln vergleichen</button>
          <button onClick={() => predictAsset()} disabled={loading}>Prognose laden</button>
        </div>
      </section>

      <section className={`modelAutomationPanel ${autoTone === 'ready' ? 'ready' : 'attention'}`}>
        <div className="guidedHeader">
          <div>
            <p className="eyebrow">Automatik</p>
            <h2>Rollierende Modellpflege</h2>
            <p className="muted">Paper-only · nächster Lauf: {pairText(automationStatus?.next_pairs)}</p>
          </div>
          <span className={`pill ${automationRunning || currentAutomationRun ? 'successPill' : ''}`}>
            {currentAutomationRun ? 'Optimiert' : automationRunning ? 'Läuft' : 'Pausiert'}
          </span>
        </div>

        <div className="botFactRow">
          <span>{profileSummary}</span>
          <span>{activeAutoAssetCount} Assets aktiv</span>
          <span>{textList(autoTimeframes).join(', ') || '-'}</span>
          <span>{autoAssetsPerRun} je Lauf</span>
          <span>{autoMaxModelCandidates} Modelltests</span>
          <span>{autoRunPlan?.total_steps ?? '-'} Schritte</span>
          <span>{autoInterval} Min.</span>
          <span>{currentAutomationRun ? 'Lauf aktiv' : 'Kein Lauf aktiv'}</span>
          <span>{autoUpdateBotModel ? 'Bot-Modell auto' : 'Nur speichern'}</span>
          <span>{autoQualityGateEnabled ? 'Qualitätsprüfung an' : 'Prüfung aus'}</span>
        </div>

        <div className="automationProfileStrip">
          <div>
            <span className="muted">Suchprofil</span>
            <strong>{profileSummary}</strong>
            <p>{autoRunPlan?.profile_reason ?? activeProfile.description} · {autoRunPlan?.optimization_tests ?? 0} Optimierungen · {autoRunPlan?.estimated_parameter_tests ?? 0} Parametertests</p>
          </div>
          <div className="profileChoiceGroup">
            {(Object.keys(AUTOMATION_PROFILE_PRESETS) as AutomationProfileId[]).map((profile) => (
              <button
                key={profile}
                className={profile === autoSearchProfile ? 'active' : ''}
                aria-pressed={profile === autoSearchProfile}
                onClick={() => applyAutomationProfile(profile)}
                disabled={loading}
              >
                {AUTOMATION_PROFILE_PRESETS[profile].label}
              </button>
            ))}
          </div>
        </div>

        <div className="modelAutomationActions">
          <button className="primary" onClick={() => automationCommand('run')} disabled={loading}>Jetzt optimieren</button>
          <button onClick={() => automationCommand(automationRunning ? 'stop' : 'start')} disabled={loading}>
            {automationRunning ? 'Automatik pausieren' : 'Automatik starten'}
          </button>
          {currentAutomationRun && (
            <button className="danger" onClick={() => automationCommand('cancel')} disabled={loading || currentAutomationRun.status === 'cancelling'}>
              Lauf stoppen
            </button>
          )}
          <button onClick={saveAutomationConfig} disabled={loading}>Einstellungen speichern</button>
        </div>

        <div className="modelSummaryGrid">
          <article className={`modelMetricCard ${currentAutomationRun ? 'active' : ''}`}>
            <span className="muted">Aktueller Lauf</span>
            <strong>{currentAutomationRun ? `${currentCompleted}/${currentTotal || '-'}` : '-'}</strong>
            <div className="progressTrack" aria-hidden="true"><span style={{ width: `${currentProgressPercent}%` }} /></div>
            <p>{currentAutomationRun ? `${currentAutomationRun.phase ?? 'Läuft'} · ${currentItemText(currentAutomationRun.current_item)}` : 'Kein Lauf aktiv'}</p>
          </article>
          <article className="modelMetricCard">
            <span className="muted">Letzter Lauf</span>
            <strong>{statusText(lastAutoRun?.status)}</strong>
            <p>{lastAutoRun ? pairText(lastAutoRun.selected_pairs) : 'Noch kein Lauf'}</p>
          </article>
          <article className="modelMetricCard">
            <span className="muted">Neues Modell</span>
            <strong>{number(autoModel?.accuracy, 3)}</strong>
            <p>{autoModel?.model_id ?? 'Noch kein Modell'} · {modelCandidateCount || 0} Varianten</p>
          </article>
          <article className="modelMetricCard">
            <span className="muted">Champion</span>
            <strong>{autoChampion?.score ? number(autoChampion.score, 2) : '-'}</strong>
            <p>{autoChampion?.symbol ? `${autoChampion.symbol} ${autoChampion.timeframe} · ${autoChampion.strategy}` : 'Noch kein Champion'}</p>
          </article>
          <article className="modelMetricCard">
            <span className="muted">Beste Optimierung</span>
            <strong>{autoBest?.metrics?.profit_factor ?? '-'}</strong>
            <p>{autoBest ? `${autoBest.symbol} ${autoBest.timeframe} · ${number(autoBest.metrics?.win_rate_percent, 2)}% Treffer` : 'Noch keine Werte'}</p>
          </article>
          <article className="modelMetricCard">
            <span className="muted">Paper-Bot-Modell</span>
            <strong>{botModelUpdate?.status === 'updated' ? 'Aktualisiert' : botModelUpdate?.status === 'blocked' ? 'Nicht übernommen' : activeBotModelId ? 'Aktiv' : '-'}</strong>
            <p>{activeBotModelId ?? 'Noch kein Modell zugewiesen'}{botModelUpdate?.strategy_name ? ` · ${botModelUpdate.strategy_name}` : ''}</p>
          </article>
          <article className={`modelMetricCard ${qualityGate?.passed === false ? 'attention' : ''}`}>
            <span className="muted">Qualitätsprüfung</span>
            <strong>{qualityGate ? (qualityGate.passed ? 'Bestanden' : 'Blockiert') : autoQualityGateEnabled ? 'Bereit' : 'Aus'}</strong>
            <p>{qualityGate?.reason ?? `Min. ${number(autoMinAccuracy, 2)} Accuracy · ${number(autoMinWinRate, 0)}% Treffer`}</p>
          </article>
          <article className={`modelMetricCard ${autoWarnings.length ? 'attention' : ''}`}>
            <span className="muted">Hinweise</span>
            <strong>{autoWarnings.length}</strong>
            <p>{autoWarnings[0]?.detail ?? 'Keine aktuellen Hinweise'}</p>
          </article>
        </div>

        <details className="advancedSettings">
          <summary>Automatik-Einstellungen ändern</summary>
          <div className="automationSettingsGrid">
            <label>Assets
              <textarea className="compactTextarea" value={autoSymbols} onChange={(event) => setAutoSymbols(event.target.value)} />
            </label>
            <label>Zeiträume
              <input value={autoTimeframes} onChange={(event) => setAutoTimeframes(event.target.value)} />
            </label>
            <label>Strategien
              <textarea className="compactTextarea" value={autoStrategies} onChange={(event) => setAutoStrategies(event.target.value)} />
            </label>
            <label className="checkboxLine">Assets erweitern
              <input type="checkbox" checked={autoExpandAssets} onChange={(event) => setAutoExpandAssets(event.target.checked)} />
              <span>Suchraum automatisch vergrößern</span>
            </label>
            <label>Asset-Suchraum
              <textarea className="compactTextarea" value={autoAssetUniverse} onChange={(event) => setAutoAssetUniverse(event.target.value)} />
            </label>
            <label>Max. Assets
              <input type="number" min={1} max={50} value={autoMaxAssets} onChange={(event) => setAutoMaxAssets(Number(event.target.value))} />
            </label>
            <label>Modelltyp
              <select value={autoModelType} onChange={(event) => setAutoModelType(event.target.value)}>
                <option value="random_forest">Random Forest</option>
                <option value="logistic_regression">Logistic Regression</option>
              </select>
            </label>
            <label>Modellvarianten
              <input value={autoModelCandidates} onChange={(event) => setAutoModelCandidates(event.target.value)} />
            </label>
            <label>Trainingsgrößen
              <input value={autoTrainingLimits} onChange={(event) => setAutoTrainingLimits(event.target.value)} />
            </label>
            <label>Lookaheads
              <input value={autoLookaheads} onChange={(event) => setAutoLookaheads(event.target.value)} />
            </label>
            <label>Max. Modelltests
              <input type="number" min={1} max={12} value={autoMaxModelCandidates} onChange={(event) => setAutoMaxModelCandidates(Number(event.target.value))} />
            </label>
            <label>Trainingskerzen
              <input type="number" min={180} max={2500} value={autoLimit} onChange={(event) => setAutoLimit(Number(event.target.value))} />
            </label>
            <label>Optimierungskerzen
              <input type="number" min={160} max={1500} value={autoOptimizationLimit} onChange={(event) => setAutoOptimizationLimit(Number(event.target.value))} />
            </label>
            <label>Assets je Lauf
              <input type="number" min={1} max={12} value={autoAssetsPerRun} onChange={(event) => setAutoAssetsPerRun(Number(event.target.value))} />
            </label>
            <label>Tests je Strategie
              <input type="number" min={1} max={250} value={autoMaxCombinations} onChange={(event) => setAutoMaxCombinations(Number(event.target.value))} />
            </label>
            <label className="checkboxLine">Alle Strategien
              <input type="checkbox" checked={autoFullStrategySearch} onChange={(event) => setAutoFullStrategySearch(event.target.checked)} />
              <span>Strategien vollständig durchsuchen</span>
            </label>
            <label className="checkboxLine">Mehrere Ziele
              <input type="checkbox" checked={autoObjectiveSearch} onChange={(event) => setAutoObjectiveSearch(event.target.checked)} />
              <span>Beste Zielmetrik selbst suchen</span>
            </label>
            <label>Optimierungsziele
              <input value={autoOptimizationObjectives} onChange={(event) => setAutoOptimizationObjectives(event.target.value)} />
            </label>
            <label>Intervall Minuten
              <input type="number" min={5} max={1440} value={autoInterval} onChange={(event) => setAutoInterval(Number(event.target.value))} />
            </label>
            <label className="checkboxLine">Paper-Bot-Modell
              <input type="checkbox" checked={autoUpdateBotModel} onChange={(event) => setAutoUpdateBotModel(event.target.checked)} />
              <span>Neues Modell zuweisen</span>
            </label>
            <label className="checkboxLine">Paper-Strategie
              <input type="checkbox" checked={autoUpdateBotStrategy} onChange={(event) => setAutoUpdateBotStrategy(event.target.checked)} />
              <span>Beste Strategie zuweisen</span>
            </label>
            <label className="checkboxLine">Qualität prüfen
              <input type="checkbox" checked={autoQualityGateEnabled} onChange={(event) => setAutoQualityGateEnabled(event.target.checked)} />
              <span>Schwache Modelle blockieren</span>
            </label>
            <label className="checkboxLine">Regelmodell schlagen
              <input type="checkbox" checked={autoRequireBeatsRule} onChange={(event) => setAutoRequireBeatsRule(event.target.checked)} />
              <span>Nur bessere Modelle übernehmen</span>
            </label>
            <label>Min. Accuracy
              <input type="number" min={0} max={1} step={0.01} value={autoMinAccuracy} onChange={(event) => setAutoMinAccuracy(Number(event.target.value))} />
            </label>
            <label>Min. Trefferquote %
              <input type="number" min={0} max={100} step={1} value={autoMinWinRate} onChange={(event) => setAutoMinWinRate(Number(event.target.value))} />
            </label>
            <label>Min. Profit Factor
              <input type="number" min={0} max={10} step={0.1} value={autoMinProfitFactor} onChange={(event) => setAutoMinProfitFactor(Number(event.target.value))} />
            </label>
          </div>
        </details>

        <details className="advancedSettings">
          <summary>Laufhistorie anzeigen</summary>
          <div className="tableScroll">
            <table>
              <thead><tr><th align="left">Zeit</th><th align="left">Status</th><th align="left">Assets</th><th align="right">PF</th><th align="right">Treffer</th></tr></thead>
              <tbody>
                {(automationStatus?.recent_runs ?? []).map((item) => (
                  <tr key={item.id ?? item.started_at}>
                    <td>{item.finished_at ? new Date(item.finished_at).toLocaleString('de-DE') : '-'}</td>
                    <td>{statusText(item.status)}</td>
                    <td>{pairText(item.selected_pairs)}</td>
                    <td align="right">{item.best?.metrics?.profit_factor ?? '-'}</td>
                    <td align="right">{number(item.best?.metrics?.win_rate_percent, 2)}%</td>
                  </tr>
                ))}
                {(automationStatus?.recent_runs ?? []).length === 0 && <tr><td colSpan={5}>Noch keine Automatikläufe.</td></tr>}
              </tbody>
            </table>
          </div>
        </details>
      </section>

      <section className="card">
        <details className="advancedSettings" open={!hasModelResult}>
          <summary>Modell-Einstellungen ändern</summary>
          <div className="modelFormGrid">
            <label>Asset
              <input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="BTC/USD" />
            </label>
            <label>Zeitraum
              <select value={timeframe} onChange={(event) => setTimeframe(event.target.value)}>
                <option value="1h">1h</option>
                <option value="4h">4h</option>
                <option value="1D">1D</option>
              </select>
            </label>
            <label>Modelltyp
              <select value={modelType} onChange={(event) => setModelType(event.target.value)}>
                <option value="random_forest">Random Forest</option>
                <option value="logistic_regression">Logistic Regression</option>
              </select>
            </label>
            <label>Kerzen
              <input type="number" min={180} max={2500} value={limit} onChange={(event) => setLimit(Number(event.target.value))} />
            </label>
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <button className="primary" onClick={trainModel} disabled={loading}>Modell trainieren</button>
            <button onClick={compareRuleVsML} disabled={loading}>Regeln vergleichen</button>
            <button onClick={() => predictAsset()} disabled={loading}>Prognose laden</button>
          </div>
        </details>
      </section>

      <div className="modelSummaryGrid">
        <article className={`modelMetricCard ${modelTone === 'attention' ? 'attention' : ''}`}>
          <span className="muted">Modellqualität</span>
          <strong>{number(mlAccuracy, 3)}</strong>
          <p>Regelmodell {number(ruleAccuracy, 3)}</p>
        </article>
        <article className="modelMetricCard">
          <span className="muted">Trading-Vergleich</span>
          <strong>{result.trading_metrics?.profit_factor ?? '-'}</strong>
          <p>PF · {number(result.trading_metrics?.win_rate_percent, 2)}% Treffer</p>
        </article>
        <article className="modelMetricCard">
          <span className="muted">Prognose</span>
          <strong>{prediction?.prediction_direction ?? '-'}</strong>
          <p>{prediction ? `Long ${number(prediction.probabilities?.long, 3)} · Short ${number(prediction.probabilities?.short, 3)}` : 'Noch nicht geladen'}</p>
        </article>
        <article className="modelMetricCard">
          <span className="muted">Daten</span>
          <strong>{result.row_count ?? latestModel?.row_count ?? 0}</strong>
          <p>{result.model_id ?? latestModel?.model_id ?? 'Noch kein Modell'}</p>
        </article>
      </div>

      <section className="card">
        <div className="guidedHeader">
          <div>
            <p className="eyebrow">Einordnung</p>
            <h2>Was treibt das Modell?</h2>
            <p className="muted">{topFeature ? `${topFeature.feature} hat aktuell den größten Einfluss.` : 'Nach dem Training siehst du hier die wichtigsten Einflussfaktoren.'}</p>
          </div>
          <span className="pill">{result.feature_importance?.length ?? 0} Features</span>
        </div>
        <details className="advancedSettings">
          <summary>Feature-Tabelle anzeigen</summary>
          <div className="tableScroll">
            <table>
              <thead><tr><th align="left">Feature</th><th align="right">Wichtigkeit</th></tr></thead>
              <tbody>
                {(result.feature_importance ?? []).slice(0, 12).map((item) => (
                  <tr key={item.feature}><td>{item.feature}</td><td align="right">{number(item.importance, 6)}</td></tr>
                ))}
                {(result.feature_importance ?? []).length === 0 && <tr><td colSpan={2}>Noch keine Feature-Werte geladen.</td></tr>}
              </tbody>
            </table>
          </div>
        </details>
      </section>

      <section className="card">
        <details className="advancedSettings">
          <summary>Gespeicherte Modelle anzeigen</summary>
          <div className="tableScroll">
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
          </div>
        </details>
      </section>
    </div>
  );
}
