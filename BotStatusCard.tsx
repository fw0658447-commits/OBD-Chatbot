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

export function BotStatusCard({ bot }: { bot: BotStatus }) {
  return (
    <section style={{ border: '1px solid #ddd', borderRadius: 12, padding: 20, maxWidth: 560 }}>
      <h2>Bot Status</h2>
      <p><strong>Status:</strong> {bot.status}</p>
      <p><strong>Modus:</strong> {bot.mode}</p>
      <p><strong>Live-Trading:</strong> {bot.live_trading_enabled ? 'aktiv' : 'gesperrt'}</p>
      <p><strong>Max. Risiko pro Trade:</strong> {(bot.max_risk_per_trade * 100).toFixed(2)}%</p>
      <p><strong>Max. Tagesverlust:</strong> {(bot.max_daily_loss * 100).toFixed(2)}%</p>
      <p><strong>Max. offene Trades:</strong> {bot.max_open_trades}</p>
      <p><strong>Mindest-CRV:</strong> {bot.min_crv}</p>
      <p><strong>Mindest-Confidence:</strong> {bot.min_confidence_score}/100</p>
      <p><strong>Max. Risk Score:</strong> {bot.max_risk_score}/100</p>
      <p><strong>Decision Modes:</strong> {(bot.supported_decision_modes ?? ['rule']).join(', ')}</p>
    </section>
  );
}
