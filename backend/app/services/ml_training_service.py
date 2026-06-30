from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.config import settings
from app.services.ai_prediction_service import AIPredictionService
from app.services.backtest_service import BacktestService
from app.services.indicator_service import IndicatorService
from app.services.market_data_service import get_market_data_service
from app.services.strategy_engine import StrategyEngine


MODEL_REGISTRY: dict[str, dict[str, Any]] = {}


@dataclass
class MLModelBundle:
    model_id: str
    model_type: str
    estimator: Any
    feature_columns: list[str]
    class_labels: list[int]
    metadata: dict[str, Any]
    path: str | None = None


class MLTrainingService:
    """Baseline ML pipeline for v0.8/v0.9.

    The model is intentionally conservative: it trains on the same engineered
    features that v0.7 exported, evaluates on a chronological holdout, and
    reports whether it beats the rule-based prediction direction on the same
    test rows. This is not investment advice and not a live trading model.
    """

    DEFAULT_MODEL_DIR = Path('/tmp/trading-cockpit-models')
    LABELS = [-1, 0, 1]

    def __init__(self):
        self.backtest_service = BacktestService()
        self.market_data_service = get_market_data_service()
        self.indicator_service = IndicatorService()
        self.ai_prediction_service = AIPredictionService()
        self.strategy_engine = StrategyEngine()
        self.model_dir = Path(getattr(settings, 'model_storage_path', '') or self.DEFAULT_MODEL_DIR)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def train(
        self,
        symbols: list[str],
        timeframes: list[str],
        strategies: list[str],
        limit: int,
        lookahead_bars: int,
        max_rows: int,
        min_warmup_bars: int,
        model_type: str = 'random_forest',
        test_size: float = 0.25,
        target_column: str = 'target_label',
    ) -> dict[str, Any]:
        dataset = self.backtest_service.export_ml_dataset(
            symbols=symbols,
            timeframes=timeframes,
            strategies=strategies,
            limit=limit,
            lookahead_bars=lookahead_bars,
            max_rows=max_rows,
            min_warmup_bars=min_warmup_bars,
        )
        rows = dataset.get('rows', [])
        if len(rows) < 80:
            raise ValueError('Not enough ML rows. Increase symbols, limit, or max_rows.')

        df = pd.DataFrame(rows).copy()
        feature_columns = self._select_feature_columns(dataset.get('feature_columns', []), df)
        if target_column not in df.columns:
            raise ValueError(f'Missing target column: {target_column}')

        X = self._clean_features(df[feature_columns])
        y = df[target_column].astype(int)
        split_index = max(1, min(len(df) - 1, int(len(df) * (1 - test_size))))
        X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
        y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]
        test_df = df.iloc[split_index:].copy()

        estimator = self._make_estimator(model_type)
        estimator.fit(X_train, y_train)
        y_pred = estimator.predict(X_test)
        probabilities = self._predict_probabilities(estimator, X_test)
        ml_metrics = self._classification_metrics(y_test.to_numpy(), y_pred)
        rule_metrics = self._rule_baseline_metrics(test_df, y_test.to_numpy())
        trading_metrics = self._directional_trading_metrics(test_df, y_pred, prefix='ml')
        rule_trading_metrics = self._directional_trading_metrics(
            test_df,
            self._rule_labels(test_df).to_numpy(),
            prefix='rule',
        )

        model_id = f'ml-v0.9-{uuid4().hex[:12]}'
        metadata = {
            'model_id': model_id,
            'model_type': model_type,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'symbols': symbols,
            'timeframes': timeframes,
            'strategies': strategies,
            'lookahead_bars': lookahead_bars,
            'target_column': target_column,
            'row_count': len(df),
            'train_rows': len(X_train),
            'test_rows': len(X_test),
            'feature_columns': feature_columns,
            'class_labels': self.LABELS,
            'metrics': ml_metrics,
            'rule_baseline_metrics': rule_metrics,
            'trading_metrics': trading_metrics,
            'rule_trading_metrics': rule_trading_metrics,
            'feature_importance': self._feature_importance(estimator, feature_columns),
            'dataset_note': dataset.get('note'),
        }
        path = self.model_dir / f'{model_id}.joblib'
        bundle = MLModelBundle(
            model_id=model_id,
            model_type=model_type,
            estimator=estimator,
            feature_columns=feature_columns,
            class_labels=self.LABELS,
            metadata=metadata,
            path=str(path),
        )
        joblib.dump(bundle, path)
        MODEL_REGISTRY[model_id] = {'bundle': bundle, 'metadata': metadata}

        preview = self._prediction_preview(test_df, y_test.to_numpy(), y_pred, probabilities)
        return {
            **metadata,
            'model_path': str(path),
            'persistence': 'memory',
            'prediction_preview': preview,
        }

    def predict_from_features(self, model_id: str | None, features: dict[str, Any]) -> dict[str, Any]:
        bundle = self._load_bundle(model_id)
        feature_values = {column: self._safe_float(features.get(column), 0.0) for column in bundle.feature_columns}
        X = pd.DataFrame([feature_values], columns=bundle.feature_columns)
        prediction = int(bundle.estimator.predict(X)[0])
        probability_map = self._single_probability_map(bundle.estimator, X)
        return {
            'model_id': bundle.model_id,
            'model_type': bundle.model_type,
            'prediction_label': prediction,
            'prediction_direction': self._label_to_direction(prediction),
            'probabilities': probability_map,
            'features_used': feature_values,
            'metadata': bundle.metadata,
        }

    def predict_asset(self, model_id: str | None, symbol: str, timeframe: str, strategy_name: str, limit: int) -> dict[str, Any]:
        candles = self.market_data_service.get_candles(symbol=symbol, timeframe=timeframe, limit=limit)
        indicators = self.indicator_service.calculate(candles)
        rule_prediction = self.ai_prediction_service.predict(symbol=symbol, timeframe=timeframe, indicators=indicators)
        strategy_name = self.strategy_engine.resolve_strategy_name(strategy_name)
        signal = self.strategy_engine.create_signal(rule_prediction, indicators, strategy_name=strategy_name)
        feature_row = self._build_feature_row(indicators, rule_prediction, signal)
        ml_prediction = self.predict_from_features(model_id, feature_row)
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy_name': strategy_name,
            'rule_prediction': rule_prediction,
            'signal_preview': signal,
            'ml_prediction': ml_prediction,
            'note': 'ML-Prognose basiert auf v0.8 Baseline-Modell und ersetzt keine Risikopruefung.',
        }

    def compare_rule_vs_ml(self, **kwargs: Any) -> dict[str, Any]:
        result = self.train(**kwargs)
        return {
            'model_id': result['model_id'],
            'model_type': result['model_type'],
            'row_count': result['row_count'],
            'test_rows': result['test_rows'],
            'ml_metrics': result['metrics'],
            'rule_baseline_metrics': result['rule_baseline_metrics'],
            'ml_trading_metrics': result['trading_metrics'],
            'rule_trading_metrics': result['rule_trading_metrics'],
            'feature_importance': result['feature_importance'],
            'interpretation': self._comparison_interpretation(result),
        }

    def list_models(self) -> list[dict[str, Any]]:
        models: list[dict[str, Any]] = [item['metadata'] for item in MODEL_REGISTRY.values()]
        for path in sorted(list(self.model_dir.glob('ml-v0.9-*.joblib')) + list(self.model_dir.glob('ml-v0.8-*.joblib')), reverse=True):
            try:
                bundle: MLModelBundle = joblib.load(path)
                if bundle.model_id not in MODEL_REGISTRY:
                    models.append(bundle.metadata)
            except Exception:
                continue
        return sorted(models, key=lambda item: item.get('created_at', ''), reverse=True)

    def _load_bundle(self, model_id: str | None) -> MLModelBundle:
        if model_id is None:
            models = self.list_models()
            if not models:
                raise ValueError('No trained model available. Train a model first.')
            model_id = models[0]['model_id']
        if model_id in MODEL_REGISTRY:
            return MODEL_REGISTRY[model_id]['bundle']
        path = self.model_dir / f'{model_id}.joblib'
        if not path.exists():
            raise ValueError(f'Model not found: {model_id}')
        bundle: MLModelBundle = joblib.load(path)
        MODEL_REGISTRY[model_id] = {'bundle': bundle, 'metadata': bundle.metadata}
        return bundle

    def _make_estimator(self, model_type: str):
        normalized = model_type.lower().strip()
        if normalized in {'logistic_regression', 'logistic'}:
            return Pipeline([
                ('scaler', StandardScaler()),
                ('model', LogisticRegression(max_iter=800, class_weight='balanced')),
            ])
        if normalized in {'random_forest', 'rf'}:
            return RandomForestClassifier(
                n_estimators=140,
                max_depth=7,
                min_samples_leaf=4,
                class_weight='balanced_subsample',
                random_state=42,
            )
        raise ValueError(f'Unsupported model_type: {model_type}')

    def _select_feature_columns(self, exported_features: list[str], df: pd.DataFrame) -> list[str]:
        candidates = list(exported_features) + [
            'close',
            'price_above_sma50',
            'sma20_above_sma50',
            'volume_confirmation',
        ]
        columns: list[str] = []
        for column in candidates:
            if column in df.columns and column not in columns:
                columns.append(column)
        return columns

    def _clean_features(self, frame: pd.DataFrame) -> pd.DataFrame:
        clean = frame.copy()
        for column in clean.columns:
            clean[column] = pd.to_numeric(clean[column], errors='coerce')
        clean = clean.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        return clean

    def _predict_probabilities(self, estimator: Any, X: pd.DataFrame) -> list[dict[str, float]]:
        if not hasattr(estimator, 'predict_proba'):
            return []
        probs = estimator.predict_proba(X)
        classes = list(getattr(estimator, 'classes_', []))
        if hasattr(estimator, 'named_steps') and 'model' in estimator.named_steps:
            classes = list(estimator.named_steps['model'].classes_)
        rows: list[dict[str, float]] = []
        for row in probs:
            rows.append({str(int(label)): round(float(prob), 6) for label, prob in zip(classes, row)})
        return rows

    def _single_probability_map(self, estimator: Any, X: pd.DataFrame) -> dict[str, float]:
        rows = self._predict_probabilities(estimator, X)
        if not rows:
            return {}
        return {
            'short': rows[0].get('-1', 0.0),
            'neutral': rows[0].get('0', 0.0),
            'long': rows[0].get('1', 0.0),
        }

    def _classification_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true,
            y_pred,
            labels=self.LABELS,
            zero_division=0,
        )
        matrix = confusion_matrix(y_true, y_pred, labels=self.LABELS)
        return {
            'accuracy': round(float(accuracy_score(y_true, y_pred)), 6),
            'by_label': {
                self._label_to_direction(label): {
                    'precision': round(float(precision[index]), 6),
                    'recall': round(float(recall[index]), 6),
                    'f1': round(float(f1[index]), 6),
                    'support': int(support[index]),
                }
                for index, label in enumerate(self.LABELS)
            },
            'confusion_matrix': {
                'labels': [self._label_to_direction(label) for label in self.LABELS],
                'matrix': matrix.astype(int).tolist(),
            },
        }

    def _rule_baseline_metrics(self, test_df: pd.DataFrame, y_true: np.ndarray) -> dict[str, Any]:
        rule_pred = self._rule_labels(test_df).to_numpy()
        return self._classification_metrics(y_true, rule_pred)

    def _rule_labels(self, frame: pd.DataFrame) -> pd.Series:
        mapping = {'long': 1, 'short': -1, 'neutral': 0}
        return frame.get('prediction_direction', pd.Series(['neutral'] * len(frame))).map(mapping).fillna(0).astype(int)

    def _directional_trading_metrics(self, test_df: pd.DataFrame, labels: np.ndarray, prefix: str) -> dict[str, Any]:
        returns = pd.to_numeric(test_df['future_return_percent'], errors='coerce').fillna(0.0).to_numpy()
        trade_mask = labels != 0
        signed_returns = returns * labels
        trade_returns = signed_returns[trade_mask]
        wins = trade_returns[trade_returns > 0]
        losses = trade_returns[trade_returns < 0]
        gross_profit = float(np.sum(wins)) if len(wins) else 0.0
        gross_loss = float(np.sum(losses)) if len(losses) else 0.0
        return {
            'metric_prefix': prefix,
            'trades': int(len(trade_returns)),
            'win_rate_percent': round(float(len(wins) / len(trade_returns) * 100), 4) if len(trade_returns) else 0.0,
            'average_return_percent': round(float(np.mean(trade_returns)), 6) if len(trade_returns) else 0.0,
            'gross_profit_percent': round(gross_profit, 6),
            'gross_loss_percent': round(gross_loss, 6),
            'profit_factor': round(gross_profit / abs(gross_loss), 6) if gross_loss < 0 else None,
        }

    def _feature_importance(self, estimator: Any, feature_columns: list[str]) -> list[dict[str, float]]:
        model = estimator
        if hasattr(estimator, 'named_steps') and 'model' in estimator.named_steps:
            model = estimator.named_steps['model']
        values = None
        if hasattr(model, 'feature_importances_'):
            values = list(model.feature_importances_)
        elif hasattr(model, 'coef_'):
            values = list(np.mean(np.abs(model.coef_), axis=0))
        if values is None:
            return []
        ranked = sorted(
            [{'feature': column, 'importance': round(float(value), 8)} for column, value in zip(feature_columns, values)],
            key=lambda item: item['importance'],
            reverse=True,
        )
        return ranked

    def _prediction_preview(
        self,
        test_df: pd.DataFrame,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        probabilities: list[dict[str, float]],
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        preview: list[dict[str, Any]] = []
        for index, (_, row) in enumerate(test_df.head(limit).iterrows()):
            preview.append({
                'timestamp': row.get('timestamp'),
                'symbol': row.get('symbol'),
                'strategy': row.get('strategy'),
                'actual_label': self._label_to_direction(int(y_true[index])),
                'predicted_label': self._label_to_direction(int(y_pred[index])),
                'future_return_percent': round(float(row.get('future_return_percent') or 0), 6),
                'probabilities': probabilities[index] if index < len(probabilities) else {},
            })
        return preview

    def _build_feature_row(self, indicators: dict[str, Any], prediction: dict[str, Any], signal: dict[str, Any] | None) -> dict[str, Any]:
        return {
            'rsi': round(float(indicators.get('rsi') or 0), 6),
            'atr_percent': round(float(indicators.get('atr_percent') or 0), 6),
            'trend_strength': round(float(indicators.get('trend_strength') or 0), 6),
            'price_above_sma50': int(bool(indicators.get('price_above_sma50'))),
            'sma20_above_sma50': int(bool(indicators.get('sma20_above_sma50'))),
            'volume_confirmation': int(bool(indicators.get('volume_confirmation'))),
            'probability_long': round(float(prediction.get('probability_long') or 0), 6),
            'probability_short': round(float(prediction.get('probability_short') or 0), 6),
            'probability_neutral': round(float(prediction.get('probability_neutral') or 0), 6),
            'confidence_score': round(float(prediction.get('confidence_score') or 0), 6),
            'risk_score': round(float(prediction.get('risk_score') or 0), 6),
            'crv': round(float(signal.get('crv') or 0), 6) if signal else 0.0,
            'signal_score': round(float(signal.get('signal_score') or 0), 6) if signal else 0.0,
            'close': round(float(indicators.get('latest_close') or 0), 6),
        }

    def _safe_float(self, value: Any, default: float) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def _label_to_direction(self, label: int) -> str:
        return {-1: 'short', 0: 'neutral', 1: 'long'}.get(int(label), 'neutral')

    def _comparison_interpretation(self, result: dict[str, Any]) -> str:
        ml_accuracy = result['metrics'].get('accuracy', 0.0)
        rule_accuracy = result['rule_baseline_metrics'].get('accuracy', 0.0)
        if ml_accuracy > rule_accuracy:
            return 'Das ML-Baseline-Modell war auf dem Holdout genauer als das bisherige Regelmodell.'
        if ml_accuracy < rule_accuracy:
            return 'Das Regelmodell war auf dem Holdout genauer als das ML-Baseline-Modell; mehr Daten oder Features noetig.'
        return 'ML-Baseline und Regelmodell lagen auf dem Holdout gleichauf.'

    def model_metadata_json(self, result: dict[str, Any]) -> str:
        return json.dumps({key: value for key, value in result.items() if key not in {'prediction_preview'}}, default=str)
