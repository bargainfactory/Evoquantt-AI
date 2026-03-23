"""
ML Engine: RandomForest + LSTM ensemble for price prediction and regime classification.
"""
from __future__ import annotations

import os
import pickle
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score

warnings.filterwarnings("ignore")

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

from config import settings


class MLEngine:
    """
    Ensemble ML engine:
      - RandomForest classifier (direction: up/down)
      - GradientBoosting classifier
      - LSTM price sequence model
    """

    FEATURE_COLS = [
        "rsi_14", "macd", "macd_signal", "macd_hist",
        "bb_width_20", "atr_14", "adx_14", "obv",
        "ema_21", "ema_50", "sma_20", "sma_50",
        "hvol_20", "roc_10", "mfi_14", "cci_14",
        "vroc_14", "mom_10", "vol_ratio_20",
    ]
    SEQUENCE_LEN = 60
    CACHE_DIR = Path(settings.MODEL_CACHE_DIR)

    def __init__(self, symbol: str):
        self.symbol = symbol.replace("/", "_").replace(":", "_")
        self.rf_model: RandomForestClassifier | None = None
        self.gb_model: GradientBoostingClassifier | None = None
        self.lstm_model = None
        self.scaler = StandardScaler()
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------
    def _build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        feat = df.copy()
        feat["returns"] = feat["close"].pct_change()
        feat["log_returns"] = np.log(feat["close"] / feat["close"].shift(1))
        feat["hl_ratio"] = (feat["high"] - feat["low"]) / feat["close"]
        feat["target"] = (feat["close"].shift(-1) > feat["close"]).astype(int)
        feat = feat.dropna()
        return feat

    def _get_feature_matrix(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        feat = self._build_features(df)
        available_cols = [c for c in self.FEATURE_COLS if c in feat.columns]
        extra_cols = ["returns", "log_returns", "hl_ratio"]
        all_cols = available_cols + [c for c in extra_cols if c in feat.columns]
        X = feat[all_cols].values
        y = feat["target"].values
        return X, y

    # ------------------------------------------------------------------
    # RandomForest training
    # ------------------------------------------------------------------
    def train_rf(self, df: pd.DataFrame) -> dict[str, float]:
        X, y = self._get_feature_matrix(df)
        tscv = TimeSeriesSplit(n_splits=5)
        accuracies, f1s = [], []

        for train_idx, val_idx in tscv.split(X):
            X_tr, X_val = X[train_idx], X[val_idx]
            y_tr, y_val = y[train_idx], y[val_idx]
            X_tr_sc = self.scaler.fit_transform(X_tr)
            X_val_sc = self.scaler.transform(X_val)
            model = RandomForestClassifier(
                n_estimators=200,
                max_depth=8,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1,
            )
            model.fit(X_tr_sc, y_tr)
            preds = model.predict(X_val_sc)
            accuracies.append(accuracy_score(y_val, preds))
            f1s.append(f1_score(y_val, preds, zero_division=0))

        # Final fit on all data
        X_sc = self.scaler.fit_transform(X)
        self.rf_model = RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=5, random_state=42, n_jobs=-1)
        self.rf_model.fit(X_sc, y)

        self._save_rf()
        return {"accuracy": float(np.mean(accuracies)), "f1": float(np.mean(f1s))}

    def train_gb(self, df: pd.DataFrame) -> dict[str, float]:
        X, y = self._get_feature_matrix(df)
        X_sc = self.scaler.fit_transform(X)
        self.gb_model = GradientBoostingClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42)
        self.gb_model.fit(X_sc, y)
        preds = self.gb_model.predict(X_sc)
        return {"accuracy": float(accuracy_score(y, preds)), "f1": float(f1_score(y, preds, zero_division=0))}

    # ------------------------------------------------------------------
    # LSTM training
    # ------------------------------------------------------------------
    def train_lstm(self, df: pd.DataFrame) -> dict[str, float]:
        if not TF_AVAILABLE:
            return {"error": "TensorFlow not available"}

        feat = self._build_features(df)
        available_cols = [c for c in self.FEATURE_COLS if c in feat.columns]
        data = feat[available_cols + ["close"]].values
        scaler = StandardScaler()
        data_sc = scaler.fit_transform(data)

        X_seq, y_seq = [], []
        for i in range(self.SEQUENCE_LEN, len(data_sc)):
            X_seq.append(data_sc[i - self.SEQUENCE_LEN:i])
            price_t = data_sc[i, available_cols.index("close") if "close" in available_cols else -1]
            price_prev = data_sc[i - 1, -1]
            y_seq.append(1 if price_t > price_prev else 0)

        X_arr = np.array(X_seq)
        y_arr = np.array(y_seq)

        split = int(len(X_arr) * 0.8)
        X_tr, X_val = X_arr[:split], X_arr[split:]
        y_tr, y_val = y_arr[:split], y_arr[split:]

        model = Sequential([
            LSTM(128, return_sequences=True, input_shape=(self.SEQUENCE_LEN, X_arr.shape[2])),
            Dropout(0.2),
            BatchNormalization(),
            LSTM(64, return_sequences=False),
            Dropout(0.2),
            BatchNormalization(),
            Dense(32, activation="relu"),
            Dense(1, activation="sigmoid"),
        ])
        model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        callbacks = [
            EarlyStopping(patience=5, restore_best_weights=True),
            ReduceLROnPlateau(patience=3, factor=0.5),
        ]
        history = model.fit(
            X_tr, y_tr,
            validation_data=(X_val, y_val),
            epochs=settings.LSTM_EPOCHS,
            batch_size=settings.LSTM_BATCH_SIZE,
            callbacks=callbacks,
            verbose=0,
        )
        self.lstm_model = model
        self._save_lstm()

        val_acc = float(max(history.history.get("val_accuracy", [0])))
        return {"val_accuracy": val_acc, "epochs_trained": len(history.history["loss"])}

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------
    def predict_ensemble(self, df: pd.DataFrame) -> dict[str, Any]:
        self._load_models()
        preds: dict[str, Any] = {}

        X, _ = self._get_feature_matrix(df)
        if len(X) == 0:
            return {"error": "Insufficient data"}
        X_sc = self.scaler.transform(X)
        last = X_sc[-1:].reshape(1, -1)

        if self.rf_model:
            prob = self.rf_model.predict_proba(last)[0]
            preds["rf"] = {"direction": "UP" if prob[1] > 0.5 else "DOWN", "confidence": float(max(prob))}

        if self.gb_model:
            prob = self.gb_model.predict_proba(last)[0]
            preds["gb"] = {"direction": "UP" if prob[1] > 0.5 else "DOWN", "confidence": float(max(prob))}

        if self.lstm_model and TF_AVAILABLE:
            feat = self._build_features(df)
            avail = [c for c in self.FEATURE_COLS if c in feat.columns]
            data_sc = StandardScaler().fit_transform(feat[avail + ["close"]].values)
            if len(data_sc) >= self.SEQUENCE_LEN:
                seq = data_sc[-self.SEQUENCE_LEN:].reshape(1, self.SEQUENCE_LEN, -1)
                prob = float(self.lstm_model.predict(seq, verbose=0)[0][0])
                preds["lstm"] = {"direction": "UP" if prob > 0.5 else "DOWN", "confidence": max(prob, 1 - prob)}

        # Ensemble vote
        votes = [1 if p["direction"] == "UP" else 0 for p in preds.values() if "direction" in p]
        conf_list = [p["confidence"] for p in preds.values() if "confidence" in p]
        ensemble_dir = "UP" if sum(votes) > len(votes) / 2 else "DOWN"
        ensemble_conf = float(np.mean(conf_list)) if conf_list else 0.5

        return {
            "ensemble": {"direction": ensemble_dir, "confidence": ensemble_conf},
            "models": preds,
        }

    # ------------------------------------------------------------------
    # Feature importance
    # ------------------------------------------------------------------
    def get_feature_importance(self) -> list[dict[str, Any]]:
        self._load_models()
        if not self.rf_model:
            return []
        importances = self.rf_model.feature_importances_
        cols = self.FEATURE_COLS[:len(importances)]
        return sorted(
            [{"feature": c, "importance": float(i)} for c, i in zip(cols, importances)],
            key=lambda x: x["importance"],
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _save_rf(self) -> None:
        path = self.CACHE_DIR / f"{self.symbol}_rf.pkl"
        with open(path, "wb") as f:
            pickle.dump((self.rf_model, self.scaler), f)

    def _save_lstm(self) -> None:
        if self.lstm_model:
            path = self.CACHE_DIR / f"{self.symbol}_lstm"
            self.lstm_model.save(str(path))

    def _load_models(self) -> None:
        rf_path = self.CACHE_DIR / f"{self.symbol}_rf.pkl"
        if rf_path.exists() and self.rf_model is None:
            with open(rf_path, "rb") as f:
                self.rf_model, self.scaler = pickle.load(f)

        lstm_path = self.CACHE_DIR / f"{self.symbol}_lstm"
        if TF_AVAILABLE and os.path.exists(lstm_path) and self.lstm_model is None:
            self.lstm_model = load_model(str(lstm_path))
