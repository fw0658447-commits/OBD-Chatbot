'use client';

import { useState } from 'react';
import { getApiBaseUrl } from '../lib/api';

type ActionResult = {
  action: string;
  result: unknown;
};

export function BotControls() {
  const [symbol, setSymbol] = useState('BTC/USD');
  const [timeframe, setTimeframe] = useState('1h');
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState<ActionResult | null>(null);

  async function post(path: string, body?: unknown, action = path) {
    setLoading(true);
    try {
      const response = await fetch(`${getApiBaseUrl()}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      });
      const result = await response.json();
      setLastResult({ action, result });
    } catch (error) {
      setLastResult({ action, result: { error: String(error) } });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section style={{ border: '1px solid #ddd', borderRadius: 12, padding: 20 }}>
      <h2>Bot Controls</h2>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
        <input
          value={symbol}
          onChange={(event) => setSymbol(event.target.value)}
          placeholder="Symbol"
          style={{ padding: 8, border: '1px solid #ccc', borderRadius: 6 }}
        />
        <select
          value={timeframe}
          onChange={(event) => setTimeframe(event.target.value)}
          style={{ padding: 8, border: '1px solid #ccc', borderRadius: 6 }}
        >
          <option value="1h">1h</option>
          <option value="4h">4h</option>
          <option value="1D">1D</option>
        </select>
        <button
          disabled={loading}
          onClick={() => post('/api/bot/run-cycle', {
            symbol,
            timeframe,
            portfolio_value: 10000,
            open_trades_count: 0,
            daily_pnl_percent: 0,
          }, 'run-cycle')}
        >
          Bot-Cycle starten
        </button>
        <button disabled={loading} onClick={() => post('/api/bot/evaluate-open-orders', undefined, 'evaluate-open-orders')}>
          Offene Orders auswerten
        </button>
        <button disabled={loading} onClick={() => post('/api/bot/kill-switch', undefined, 'kill-switch')}>
          Kill-Switch
        </button>
      </div>
      <p>Nach einer Aktion die Seite neu laden, um die Serverdaten zu aktualisieren.</p>
      {lastResult && (
        <pre style={{ overflowX: 'auto', background: '#f7f7f7', padding: 12, borderRadius: 8 }}>
          {JSON.stringify(lastResult, null, 2)}
        </pre>
      )}
    </section>
  );
}
