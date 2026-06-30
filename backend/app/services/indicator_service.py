from __future__ import annotations

import pandas as pd


class IndicatorService:
    def calculate(self, candles: list[dict]) -> dict:
        df = pd.DataFrame(candles)
        if df.empty or len(df) < 60:
            raise ValueError('Not enough candle data. Need at least 60 candles.')

        for column in ['open', 'high', 'low', 'close', 'volume']:
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors='coerce')

        df['sma20'] = df['close'].rolling(window=20).mean()
        df['sma50'] = df['close'].rolling(window=50).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['rsi'] = self._calculate_rsi(df['close'])
        df['atr'] = self._calculate_atr(df)
        df['high_20'] = df['high'].rolling(window=20).max()
        df['low_20'] = df['low'].rolling(window=20).min()
        df['previous_high_20'] = df['high'].shift(1).rolling(window=20).max()
        df['previous_low_20'] = df['low'].shift(1).rolling(window=20).min()

        latest = df.iloc[-1]
        previous = df.iloc[-2]
        atr_percent = latest['atr'] / latest['close'] * 100 if latest['close'] else 0

        return {
            'latest_close': float(latest['close']),
            'previous_close': float(previous['close']),
            'sma20': float(latest['sma20']),
            'sma50': float(latest['sma50']),
            'ema21': float(latest['ema21']),
            'rsi': float(latest['rsi']),
            'atr': float(latest['atr']),
            'atr_percent': float(atr_percent),
            'price_above_sma50': bool(latest['close'] > latest['sma50']),
            'sma20_above_sma50': bool(latest['sma20'] > latest['sma50']),
            'trend_strength': float(self._trend_strength(latest)),
            'volume_confirmation': bool(self._volume_confirmation(df)),
            'last_return_percent': float((latest['close'] - previous['close']) / previous['close'] * 100),
            'high_20': float(latest['high_20']),
            'low_20': float(latest['low_20']),
            'previous_high_20': float(latest['previous_high_20']),
            'previous_low_20': float(latest['previous_low_20']),
            'distance_to_ema21_atr': float(abs(latest['close'] - latest['ema21']) / latest['atr']) if latest['atr'] else 0.0,
            'range_20_percent': float((latest['high_20'] - latest['low_20']) / latest['close'] * 100) if latest['close'] else 0.0,
        }

    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, pd.NA)
        return (100 - (100 / (1 + rs))).fillna(50)

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(period).mean().bfill()

    def _trend_strength(self, latest: pd.Series) -> float:
        if not latest['sma50']:
            return 50.0
        distance = (latest['close'] - latest['sma50']) / latest['sma50'] * 100
        if distance > 5:
            return 85.0
        if distance > 2:
            return 70.0
        if distance > 0:
            return 55.0
        if distance > -2:
            return 45.0
        return 30.0

    def _volume_confirmation(self, df: pd.DataFrame) -> bool:
        if 'volume' not in df.columns or df['volume'].isna().all():
            return False
        recent_volume = df['volume'].tail(5).mean()
        average_volume = df['volume'].tail(30).mean()
        return bool(recent_volume > average_volume)
