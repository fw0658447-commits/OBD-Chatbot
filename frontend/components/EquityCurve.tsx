'use client';

type Point = {
  timestamp: string;
  equity: number;
  event?: string;
};

function number(value: unknown, digits = 2) {
  return Number(value ?? 0).toFixed(digits);
}

export function EquityCurve({ points }: { points: Point[] }) {
  if (!points || points.length < 2) {
    return <p className="muted">Noch keine Equity-Kurve vorhanden.</p>;
  }

  const width = 720;
  const height = 220;
  const padding = 24;
  const values = points.map((point) => Number(point.equity));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = (width - padding * 2) / Math.max(points.length - 1, 1);

  const path = points.map((point, index) => {
    const x = padding + index * step;
    const y = height - padding - ((Number(point.equity) - min) / range) * (height - padding * 2);
    return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
  }).join(' ');

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Equity-Kurve" style={{ width: '100%', height: 260 }}>
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="currentColor" opacity="0.25" />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="currentColor" opacity="0.25" />
        <path d={path} fill="none" stroke="currentColor" strokeWidth="3" />
        {points.map((point, index) => {
          const x = padding + index * step;
          const y = height - padding - ((Number(point.equity) - min) / range) * (height - padding * 2);
          return <circle key={`${point.timestamp}-${index}`} cx={x} cy={y} r="3" fill="currentColor" />;
        })}
      </svg>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <span className="muted">Min: {number(min)}</span>
        <span className="muted">Max: {number(max)}</span>
        <span className="muted">Letzter Wert: {number(points[points.length - 1].equity)}</span>
      </div>
    </div>
  );
}
