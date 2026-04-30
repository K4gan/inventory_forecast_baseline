from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error


@dataclass(frozen=True)
class ForecastResult:
    sku: str
    next_week_units: float
    validation_mae: float


def generate_sales(seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for sku in ["basic-tee", "denim-jacket", "running-shoe"]:
        base = rng.integers(24, 80)
        for week in range(1, 105):
            promo = int(week % 9 == 0)
            season = 12 * np.sin(2 * np.pi * week / 52)
            demand = max(0, base + season + promo * 18 + rng.normal(0, 5))
            rows.append({"sku": sku, "week": week, "promo": promo, "units": round(demand)})
    return pd.DataFrame(rows)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["sku", "week"]).copy()
    out["lag_1"] = out.groupby("sku")["units"].shift(1)
    out["lag_4"] = out.groupby("sku")["units"].shift(4)
    out["rolling_4"] = out.groupby("sku")["units"].shift(1).rolling(4).mean().reset_index(level=0, drop=True)
    return out.dropna()


def train_for_sku(df: pd.DataFrame, sku: str) -> ForecastResult:
    data = add_features(df[df["sku"] == sku])
    train = data[data["week"] <= 92]
    test = data[data["week"] > 92]
    features = ["week", "promo", "lag_1", "lag_4", "rolling_4"]
    model = RandomForestRegressor(n_estimators=180, min_samples_leaf=2, random_state=7)
    model.fit(train[features], train["units"])
    validation = model.predict(test[features])
    latest = data.tail(1)[features]
    return ForecastResult(sku, float(model.predict(latest)[0]), float(mean_absolute_error(test["units"], validation)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a weekly inventory demand baseline.")
    parser.add_argument("--sku", default="basic-tee")
    args = parser.parse_args()
    result = train_for_sku(generate_sales(), args.sku)
    print(f"sku={result.sku} next_week_units={result.next_week_units:.1f} validation_mae={result.validation_mae:.2f}")


if __name__ == "__main__":
    main()
