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

  const gateItems = gates.gates ?? [];
  const failedGates = gateItems.filter((gate: any) => !gate.passed);
  const alertItems = alerts.items ?? [];
  const criticalAlerts = Number(alerts.critical_count ?? 0);
  const warningAlerts = Number(alerts.warning_count ?? 0);
  const dailyPnl = Number(daily.summary?.total_pnl ?? 0);
  const paperReleased = Boolean(gates.released_for_paper_automation);
  const monitorNeedsAttention = !paperReleased || criticalAlerts > 0 || failedGates.length > 0;
  const monitorTitle = criticalAlerts > 0
    ? 'Kritische Warnung aktiv'
    : paperReleased
      ? 'Paper-Betrieb freigegeben'
      : 'Noch nicht freigegeben';
  const monitorDetail = gates.recommendation ?? 'Prüfe Freigabe, Tagesbericht und Alerts, bevor der Paper-Bot automatisch läuft.';
  const bestMatrixItem = [...(matrix.items ?? [])].sort((a: any, b: any) => Number(b.profit_factor ?? 0) - Number(a.profit_factor ?? 0))[0];

  return (
    <div className="stack">
      <section className={`monitorHero ${monitorNeedsAttention ? 'attention' : ''}`}>
        <div>
          <p className="eyebrow">Risiko-Ampel</p>
          <h2>{monitorTitle}</h2>
          <p className="muted">{monitorDetail}</p>
          <div className="botFactRow">
            <span>Echtgeld gesperrt</span>
            <span>{failedGates.length} offene Prüfpunkte</span>
            <span>{criticalAlerts + warningAlerts} Alerts</span>
            <span>{gates.persistence ?? 'memory'}</span>
          </div>
        </div>
        <div className="monitorActions">
          <button className="primary" onClick={refresh} disabled={loading}>Risiko neu prüfen</button>
        </div>
      </section>

      <div className="monitorSummaryGrid">
        <article className={`monitorMetricCard ${!paperReleased ? 'attention' : ''}`}>
          <span className="muted">Freigabe</span>
          <strong className={paperReleased ? 'good' : 'bad'}>{gates.status ?? 'unbekannt'}</strong>
          <p>{paperReleased ? 'Paper-Automatik erlaubt' : 'Noch blockiert'}</p>
        </article>
        <article className={`monitorMetricCard ${dailyPnl < 0 ? 'attention' : ''}`}>
          <span className="muted">24h P/L</span>
          <strong className={dailyPnl >= 0 ? 'good' : 'bad'}>{number(dailyPnl, 2)}</strong>
          <p>{daily.summary?.orders_total ?? 0} Orders · {number(daily.summary?.win_rate_percent, 1)}% Treffer</p>
        </article>
        <article className={`monitorMetricCard ${criticalAlerts > 0 || warningAlerts > 0 ? 'attention' : ''}`}>
          <span className="muted">Alerts</span>
          <strong>{criticalAlerts + warningAlerts}</strong>
          <p>{criticalAlerts} kritisch · {warningAlerts} Warnungen</p>
        </article>
        <article className={`monitorMetricCard ${failedGates.length > 0 ? 'attention' : ''}`}>
          <span className="muted">Prüfpunkte</span>
          <strong>{gateItems.length - failedGates.length}/{gateItems.length}</strong>
          <p>{failedGates.length ? 'Noch offen' : 'Alles bestanden'}</p>
        </article>
      </div>

      <section className="card">
        <div className="guidedHeader">
          <div>
            <p className="eyebrow">Prüfpunkte</p>
            <h2>Was blockiert noch?</h2>
            <p className="muted">Nur offene Punkte brauchen Aufmerksamkeit; bestandene Punkte bleiben unten in den Details.</p>
          </div>
          <span className={`pill ${failedGates.length ? 'warnPill' : 'goodPill'}`}>{failedGates.length ? `${failedGates.length} offen` : 'Alles ok'}</span>
        </div>
        {failedGates.length ? (
          <div className="checklistGrid">
            {failedGates.map((gate: any) => (
              <div key={gate.name} className="checkItem blocked">
                <strong>{gate.name}</strong>
                <span>Ist {String(gate.actual ?? '-')} · Soll {String(gate.required ?? '-')} · {gate.severity}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="emptyState">
            <h3>Keine offenen Prüfpunkte</h3>
            <p className="muted">Die aktuellen Gates sind bestanden. Echtgeldhandel bleibt trotzdem gesperrt.</p>
          </div>
        )}
      </section>

      <section className="card">
        <div className="guidedHeader">
          <div>
            <p className="eyebrow">Alerts</p>
            <h2>Aktive Meldungen</h2>
            <p className="muted">Warnungen werden hier als kurze Karten angezeigt.</p>
          </div>
          <span className={`pill ${alertItems.length ? 'warnPill' : 'goodPill'}`}>{alertItems.length ? `${alertItems.length} aktiv` : 'Keine Alerts'}</span>
        </div>
        {alertItems.length ? (
          <div className="alertGrid">
            {alertItems.slice(0, 6).map((item: any, index: number) => (
              <article key={`${item.code}-${index}`} className={`alertCard ${item.severity === 'critical' ? 'critical' : ''}`}>
                <div className="stepTop">
                  <strong>{item.code}</strong>
                  <span className={`pill ${item.severity === 'critical' ? 'badPill' : 'warnPill'}`}>{item.severity}</span>
                </div>
                <p>{item.message}</p>
              </article>
            ))}
          </div>
        ) : (
          <div className="emptyState">
            <h3>Keine aktiven Alerts</h3>
            <p className="muted">Der Monitoring-Service meldet aktuell keine Warnungen.</p>
          </div>
        )}
      </section>

      <section className="card">
        <details className="advancedSettings">
          <summary>Details zu Gates, Alerts und Strategie-Matrix anzeigen</summary>
          <div className="monitorDetailsGrid">
            <article className="monitorDetailCard">
              <span className="muted">Stärkste Strategie</span>
              <strong>{bestMatrixItem?.strategy_name ?? '-'}</strong>
              <p>{bestMatrixItem ? `${bestMatrixItem.decision_mode} · PF ${bestMatrixItem.profit_factor ?? '-'}` : 'Noch keine geschlossenen Orders'}</p>
            </article>
            <article className="monitorDetailCard">
              <span className="muted">Risk Events 24h</span>
              <strong>{daily.summary?.risk_events ?? 0}</strong>
              <p>{daily.summary?.closed_orders ?? 0} geschlossene Orders</p>
            </article>
          </div>

          <h3>Validation Gates</h3>
          <div className="tableScroll">
            <table>
              <thead><tr><th align="left">Gate</th><th align="left">Status</th><th align="right">Ist</th><th align="right">Soll</th><th align="left">Schwere</th></tr></thead>
              <tbody>
                {gateItems.map((gate: any) => (
                  <tr key={gate.name}>
                    <td>{gate.name}</td>
                    <td className={gate.passed ? 'good' : 'bad'}>{gate.passed ? 'bestanden' : 'offen'}</td>
                    <td align="right">{String(gate.actual ?? '-')}</td>
                    <td align="right">{String(gate.required ?? '-')}</td>
                    <td>{gate.severity}</td>
                  </tr>
                ))}
                {gateItems.length === 0 && <tr><td colSpan={5}>Noch keine Prüfpunkte geladen.</td></tr>}
              </tbody>
            </table>
          </div>

          <h3>Aktive Alerts</h3>
          <div className="tableScroll">
            <table>
              <thead><tr><th align="left">Severity</th><th align="left">Code</th><th align="left">Meldung</th></tr></thead>
              <tbody>
                {alertItems.map((item: any, index: number) => <tr key={`${item.code}-${index}`}><td>{item.severity}</td><td>{item.code}</td><td>{item.message}</td></tr>)}
                {alertItems.length === 0 && <tr><td colSpan={3}>Keine aktiven Alerts.</td></tr>}
              </tbody>
            </table>
          </div>

          <h3>Strategie-/Modus-Matrix</h3>
          <div className="tableScroll">
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
                {(matrix.items ?? []).length === 0 && <tr><td colSpan={7}>Noch keine geschlossenen Orders für Matrix.</td></tr>}
              </tbody>
            </table>
          </div>
        </details>
      </section>
    </div>
  );
}
