from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any


class DataQualityService:
    """Validates whether market data is good enough for paper-bot decisions."""

    def assess_candles(self, candles: list[dict[str, Any]], timeframe: str, provider: str | None = None) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        if len(candles) < 80:
            issues.append({'code': 'too_few_candles', 'message': 'At least 80 candles are required for stable indicators.'})

        parsed_times: list[datetime] = []
        previous_time: datetime | None = None
        max_gap_ratio = 0.0
        expected_seconds = self._expected_seconds(timeframe)
        invalid_ohlc_count = 0
        zero_volume_count = 0
        close_values: list[float] = []
        ranges_pct: list[float] = []

        for index, candle in enumerate(candles):
            try:
                ts = self._parse_timestamp(candle.get('timestamp') or candle.get('candle_time'))
                parsed_times.append(ts)
                if previous_time is not None:
                    delta_seconds = abs((ts - previous_time).total_seconds())
                    if expected_seconds and delta_seconds > expected_seconds * 1.8:
                        max_gap_ratio = max(max_gap_ratio, delta_seconds / expected_seconds)
                previous_time = ts

                open_price = float(candle['open'])
                high = float(candle['high'])
                low = float(candle['low'])
                close = float(candle['close'])
                volume = float(candle.get('volume') or 0.0)
                close_values.append(close)
                if low <= 0 or high <= 0 or open_price <= 0 or close <= 0:
                    invalid_ohlc_count += 1
                if high < max(open_price, close) or low > min(open_price, close) or high < low:
                    invalid_ohlc_count += 1
                if volume <= 0:
                    zero_volume_count += 1
                if close > 0:
                    ranges_pct.append((high - low) / close * 100)
            except Exception:
                invalid_ohlc_count += 1

        if invalid_ohlc_count:
            issues.append({'code': 'invalid_ohlc', 'message': f'{invalid_ohlc_count} candles contain invalid OHLC values.'})
        if max_gap_ratio >= 3:
            issues.append({'code': 'large_data_gap', 'message': f'Largest candle gap is {max_gap_ratio:.1f}x expected interval.'})
        elif max_gap_ratio >= 1.8:
            warnings.append({'code': 'moderate_data_gap', 'message': f'Largest candle gap is {max_gap_ratio:.1f}x expected interval.'})

        stale_minutes = None
        if parsed_times:
            latest = max(parsed_times)
            now = datetime.now(timezone.utc)
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            stale_minutes = (now - latest).total_seconds() / 60
            max_age_minutes = (expected_seconds / 60 * 3) if expected_seconds else 180
            if stale_minutes > max_age_minutes:
                warnings.append({'code': 'stale_data', 'message': f'Latest candle is {stale_minutes:.1f} minutes old.'})

        if close_values:
            bad_close_moves = 0
            for previous, current in zip(close_values, close_values[1:]):
                if previous > 0 and abs(current - previous) / previous * 100 > 20:
                    bad_close_moves += 1
            if bad_close_moves:
                warnings.append({'code': 'extreme_close_move', 'message': f'{bad_close_moves} candle-to-candle moves exceed 20%.'})

        zero_volume_ratio = zero_volume_count / len(candles) if candles else 1.0
        if zero_volume_ratio > 0.5:
            warnings.append({'code': 'mostly_zero_volume', 'message': 'More than half of candles have zero volume; volume filters may be unreliable.'})

        score = 100
        score -= min(45, len(issues) * 20)
        score -= min(30, len(warnings) * 8)
        score -= min(25, invalid_ohlc_count * 3)
        if max_gap_ratio:
            score -= min(15, max(0, max_gap_ratio - 1) * 4)
        if zero_volume_ratio > 0.5:
            score -= 10
        score = max(0, round(score, 2))
        trade_allowed = score >= 70 and not issues

        return {
            'status': 'ok' if trade_allowed else 'degraded',
            'provider': provider or 'unknown',
            'timeframe': timeframe,
            'candle_count': len(candles),
            'quality_score': score,
            'trade_allowed': trade_allowed,
            'issues': issues,
            'warnings': warnings,
            'latest_candle_age_minutes': round(stale_minutes, 2) if stale_minutes is not None else None,
            'largest_gap_ratio': round(max_gap_ratio, 2),
            'zero_volume_ratio': round(zero_volume_ratio, 4),
            'average_range_percent': round(mean(ranges_pct), 4) if ranges_pct else None,
        }

    def _expected_seconds(self, timeframe: str) -> int:
        mapping = {'1m': 60, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600, '4h': 14400, '1d': 86400, '1D': 86400}
        return mapping.get(timeframe, 3600)

    def _parse_timestamp(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        raw = str(value).replace('Z', '+00:00')
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return datetime.strptime(raw, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)


data_quality_service = DataQualityService()
