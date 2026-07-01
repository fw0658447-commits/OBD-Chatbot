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

export function BotStatusCard({ bot }: { bot: BotStatus }) {
  const safeMode = !bot.live_trading_enabled && bot.mode === 'paper';

  return (
    <section className="card">
      <h2>Bot Status</h2>
      <div className={safeMode ? 'kpi good' : 'kpi bad'}>{safeMode ? 'Sicher' : 'Prüfen'}</div>
      <p><strong>Status:</strong> {statusLabel(bot.status)}</p>
      <p><strong>Modus:</strong> {modeLabel(bot.mode)}</p>
      <p><strong>Echtes Trading:</strong> {bot.live_trading_enabled ? 'aktiv' : 'gesperrt'}</p>
      <div className="miniGrid">
        <div>
          <span className="muted">Risiko je Trade</span>
          <strong>{(bot.max_risk_per_trade * 100).toFixed(2)}%</strong>
        </div>
        <div>
          <span className="muted">Tagesverlust</span>
          <strong>{(bot.max_daily_loss * 100).toFixed(2)}%</strong>
        </div>
        <div>
          <span className="muted">Offene Trades</span>
          <strong>{bot.max_open_trades}</strong>
        </div>
        <div>
          <span className="muted">Mindestqualität</span>
          <strong>{bot.min_confidence_score}/100</strong>
        </div>
      </div>
    </section>
  );
}
