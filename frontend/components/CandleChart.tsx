'use client';

import { useEffect, useRef } from 'react';
import { CandlestickSeries, createChart, type CandlestickData, type UTCTimestamp } from 'lightweight-charts';
import type { Candle } from '../types/trading';

function toSeriesData(candles: Candle[]): CandlestickData[] {
  return candles.map((candle) => ({
    time: Math.floor(new Date(candle.timestamp).getTime() / 1000) as UTCTimestamp,
    open: Number(candle.open),
    high: Number(candle.high),
    low: Number(candle.low),
    close: Number(candle.close)
  }));
}

export function CandleChart({ candles }: { candles: Candle[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current || candles.length === 0) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 420,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#1f2937'
      },
      grid: {
        vertLines: { color: '#edf0f5' },
        horzLines: { color: '#edf0f5' }
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: true }
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#067647',
      downColor: '#b42318',
      borderVisible: false,
      wickUpColor: '#067647',
      wickDownColor: '#b42318'
    });

    series.setData(toSeriesData(candles));
    chart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver(() => {
      if (!containerRef.current) return;
      chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [candles]);

  if (candles.length === 0) {
    return <div className="chartBox row" style={{ justifyContent: 'center' }}>Keine Kerzendaten geladen.</div>;
  }

  return <div ref={containerRef} className="chartBox" />;
}
