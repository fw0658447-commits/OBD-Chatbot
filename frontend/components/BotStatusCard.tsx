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

function statusLabel(status: string) {
  if (status === 'paper_only') return 'Bereit für Paper-Trading';
  if (status === 'backend_not_reachable') return 'API nicht erreichbar';
  return status.replaceAll('_', ' ');
}

function modeLabel(mode: string) {
  if (mode === 'paper') return 'Paper-Trading';
  return mode.replaceAll('_', ' ');
}

function percent(value: number) {
  return `${(Number(value ?? 0) * 100).toFixed(2)}%`;
}

export function BotStatusCard({ bot }: { bot: BotStatus }) {
  const safeMode = !bot.live_trading_enabled && bot.mode === 'paper';
  const decisionModes = bot.supported_decision_modes?.length ? bot.supported_decision_modes.join(', ') : bot.default_decision_mode ?? 'Regeln';

  return (
    <section className={`botSafetyCard ${safeMode ? '' : 'attention'}`}>
      <div className="guidedHeader">
        <div>
          <p className="eyebrow">Sicherheit</p>
          <h2>{safeMode ? 'Echtgeld bleibt gesperrt' : 'Bot-Sicherheit prüfen'}</h2>
          <p className="muted">{safeMode ? 'Der Bot arbeitet im Paper-Modus und kann nur simulierte Entscheidungen erzeugen.' : 'Bitte Modus und Live-Trading-Sperre prüfen, bevor Tests weiterlaufen.'}</p>
        </div>
        <span className={`pill ${safeMode ? 'goodPill' : 'badPill'}`}>{safeMode ? 'Sicher' : 'Prüfen'}</span>
      </div>

      <div className="botSafetyGrid">
        <article>
          <span className="muted">Modus</span>
          <strong>{modeLabel(bot.mode)}</strong>
          <p>{statusLabel(bot.status)}</p>
        </article>
        <article>
          <span className="muted">Echtes Trading</span>
          <strong className={bot.live_trading_enabled ? 'bad' : 'good'}>{bot.live_trading_enabled ? 'Aktiv' : 'Gesperrt'}</strong>
          <p>{bot.live_trading_enabled ? 'Nicht für lokale Tests gedacht' : 'Nur Simulation'}</p>
        </article>
        <article>
          <span className="muted">Risiko je Trade</span>
          <strong>{percent(bot.max_risk_per_trade)}</strong>
          <p>Tageslimit {percent(bot.max_daily_loss)}</p>
        </article>
        <article>
          <span className="muted">Qualität</span>
          <strong>{bot.min_confidence_score}/100</strong>
          <p>CRV ab {bot.min_crv} · max. {bot.max_open_trades} Trades</p>
        </article>
      </div>

      <p className="muted">Entscheidungsarten: {decisionModes}</p>
    </section>
  );
}
