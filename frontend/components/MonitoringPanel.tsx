'use client';

import { useEffect, useState } from 'react';
import { apiGet } from '../lib/api';

function number(value: unknown, digits = 2) {
  return Number(value ?? 0).toFixed(digits);
}

export function MonitoringPanel() {
  const [gates, setGates] = useState<any>({ gates: [], performance: {} });
  const [daily, setDaily] = useState<any>({ summary: {}, breakdowns: {} });
  const [alerts, setAlerts] = useState<any>({ items: [] });
  const [matrix, setMatrix] = useState<any>({ items: [] });
  const [loading, setLoading] = useState(false);

  async function refresh() {
    setLoading(true);
    const [gateData, dailyData, alertData, matrixData] = await Promise.all([
      apiGet<any>('/api/monitoring/validation-gates', { gates: [], performance: {} }),
      apiGet<any>('/api/monitoring/daily-report?lookback_hours=24', { summary: {}, breakdowns: {} }),
      apiGet<any>('/api/monitoring/alerts', { items: [] }),
      apiGet<any>('/api/monitoring/strategy-matrix', { items: [] })
    ]);
    setGates(gateData);
    setDaily(dailyData);
    setAlerts(alertData);
    setMatrix(matrixData);
    setLoading(false);
  }

  useEffect(() => { refresh(); }, []);

  return (
    <div className="stack">
      <section className="card">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <div>
            <h2>v1.2 Validierung & Monitoring</h2>
            <p className="muted">Freigabe-Gates fuer realistischen Paper-Betrieb. Echtgeldhandel bleibt gesperrt.</p>
          </div>
          <button className="primary" onClick={refresh} disabled={loading}>Aktualisieren</button>
        </div>
      </section>

      <div className="grid">
        <section className="card">
          <h2>Release-Status</h2>
          <div className={`kpi ${gates.released_for_paper_automation ? 'good' : 'bad'}`}>{gates.status ?? 'unbekannt'}</div>
          <p>{gates.recommendation}</p>
          <p className="muted">Enforcement: {String(gates.enforcement_enabled ?? false)} | Persistence: {gates.persistence ?? 'memory'}</p>
        </section>
        <section className="card">
          <h2>24h Report</h2>
          <p>Orders: {daily.summary?.orders_total ?? 0}</p>
          <p>Geschlossen: {daily.summary?.closed_orders ?? 0}</p>
          <p>P/L: {number(daily.summary?.total_pnl, 2)}</p>
          <p>Winrate: {number(daily.summary?.win_rate_percent, 1)}%</p>
          <p>Risk Events: {daily.summary?.risk_events ?? 0}</p>
        </section>
        <section className="card">
          <h2>Alerts</h2>
          <div className={`kpi ${alerts.status === 'ok' ? 'good' : 'bad'}`}>{alerts.status ?? 'unbekannt'}</div>
          <p>Kritisch: {alerts.critical_count ?? 0}</p>
          <p>Warnungen: {alerts.warning_count ?? 0}</p>
        </section>
      </div>

      <section className="card">
        <h2>Validation Gates</h2>
        <table>
          <thead><tr><th align="left">Gate</th><th align="left">Status</th><th align="right">Ist</th><th align="right">Soll</th><th align="left">Schwere</th></tr></thead>
          <tbody>
            {(gates.gates ?? []).map((gate: any) => (
              <tr key={gate.name}>
                <td>{gate.name}</td>
                <td className={gate.passed ? 'good' : 'bad'}>{gate.passed ? 'bestanden' : 'offen'}</td>
                <td align="right">{String(gate.actual ?? '-')}</td>
                <td align="right">{String(gate.required ?? '-')}</td>
                <td>{gate.severity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>Aktive Alerts</h2>
        <table>
          <thead><tr><th align="left">Severity</th><th align="left">Code</th><th align="left">Meldung</th></tr></thead>
          <tbody>
            {(alerts.items ?? []).map((item: any, index: number) => <tr key={`${item.code}-${index}`}><td>{item.severity}</td><td>{item.code}</td><td>{item.message}</td></tr>)}
            {(alerts.items ?? []).length === 0 && <tr><td colSpan={3}>Keine aktiven Alerts.</td></tr>}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>Strategie-/Modus-Matrix</h2>
        <table>
          <thead><tr><th align="left">Strategie</th><th align="left">Modus</th><th align="right">Trades</th><th align="right">Winrate</th><th align="right">PF</th><th align="right">DD %</th><th align="right">Expectancy</th></tr></thead>
          <tbody>
            {(matrix.items ?? []).map((item: any, index: number) => (
              <tr key={`${item.strategy_name}-${item.decision_mode}-${index}`}>
                <td>{item.strategy_name}</td>
                <td>{item.decision_mode}</td>
                <td align="right">{item.closed_orders}</td>
                <td align="right">{number(item.win_rate_percent, 1)}%</td>
                <td align="right">{item.profit_factor ?? '-'}</td>
                <td align="right">{number(item.max_drawdown_percent, 2)}%</td>
                <td align="right">{number(item.expectancy_per_trade, 2)}</td>
              </tr>
            ))}
            {(matrix.items ?? []).length === 0 && <tr><td colSpan={7}>Noch keine geschlossenen Orders fuer Matrix.</td></tr>}
          </tbody>
        </table>
      </section>
    </div>
  );
}
