import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
import sqlite3

from config import Config

DEFAULT_OUTPUT_FILE = "pv_energy_plot.png"


class PVPlotter:
    def __init__(self, db_path: Path, table_name: str, days: int = 30):
        self.db_path = db_path
        self.table_name = table_name
        self.days = days
        self.cutoff = datetime.now() - timedelta(days=days)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _read_sql(self, query: str, params: tuple) -> pd.DataFrame:
        with self._connect() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def load_series(self, metric: str, group_by: str) -> pd.DataFrame:
        if group_by == "raw":
            return self._load_raw_series(metric)
        if metric == "power":
            return self._load_aggregated_power(group_by)
        return self._load_aggregated_energy(group_by)

    def _load_raw_series(self, metric: str) -> pd.DataFrame:
        if metric == "power":
            sql = (
                f"SELECT timestamp, power FROM {self.table_name} "
                "WHERE timestamp >= ? ORDER BY timestamp ASC"
            )
        else:
            sql = (
                f"SELECT timestamp, (julianday(timestamp) - julianday(prev_ts)) * 24.0 * prev_power AS energy_wh "
                f"FROM ("
                f"  SELECT timestamp, power, lag(timestamp) OVER (ORDER BY timestamp) AS prev_ts, "
                f"         lag(power) OVER (ORDER BY timestamp) AS prev_power "
                f"  FROM {self.table_name} "
                f"  WHERE timestamp >= ? "
                f") "
                f"WHERE prev_ts IS NOT NULL ORDER BY timestamp ASC"
            )

        df = self._read_sql(sql, (self.cutoff.isoformat(),))
        if df.empty:
            return df

        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False, errors="coerce")
        df = df.dropna(subset=["timestamp"]) if metric == "power" else df.dropna(subset=["timestamp", "energy_wh"])
        df = df.set_index("timestamp")
        return df

    def _load_aggregated_power(self, group_by: str) -> pd.DataFrame:
        label = self._group_label(group_by)
        group_expr = self._group_expression(group_by)
        sql = (
            f"SELECT {group_expr} AS period, AVG(power) AS power "
            f"FROM {self.table_name} "
            f"WHERE timestamp >= ? "
            f"GROUP BY period "
            f"ORDER BY period ASC"
        )
        df = self._read_sql(sql, (self.cutoff.isoformat(),))
        return self._prepare_aggregated_df(df, label, "power")

    def _load_aggregated_energy(self, group_by: str) -> pd.DataFrame:
        label = self._group_label(group_by)
        group_expr = self._group_expression(group_by)
        sql = (
            f"SELECT {group_expr} AS period, SUM((julianday(timestamp) - julianday(prev_ts)) * 24.0 * prev_power) AS energy_wh "
            f"FROM ("
            f"  SELECT timestamp, power, lag(timestamp) OVER (ORDER BY timestamp) AS prev_ts, "
            f"         lag(power) OVER (ORDER BY timestamp) AS prev_power "
            f"  FROM {self.table_name} "
            f"  WHERE timestamp >= ? "
            f") "
            f"WHERE prev_ts IS NOT NULL "
            f"GROUP BY period "
            f"ORDER BY period ASC"
        )
        df = self._read_sql(sql, (self.cutoff.isoformat(),))
        return self._prepare_aggregated_df(df, label, "energy_wh")

    def _group_expression(self, group_by: str) -> str:
        if group_by == "hour":
            return "strftime('%H', timestamp)"
        if group_by == "day":
            return "date(timestamp)"
        if group_by == "month":
            return "strftime('%Y-%m', timestamp)"
        raise ValueError(f"Unsupported grouping: {group_by}")

    def _group_label(self, group_by: str) -> str:
        if group_by == "hour":
            return "Hour of day"
        if group_by == "day":
            return "Date"
        if group_by == "month":
            return "Month"
        raise ValueError(f"Unsupported grouping: {group_by}")

    def _prepare_aggregated_df(self, df: pd.DataFrame, label: str, column: str) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.dropna(subset=[column])
        df = df.set_index("period")
        df.index.name = label
        return df

    def plot(self, series: pd.DataFrame, output_path: Path, group_by: str, metric: str) -> None:
        if series.empty:
            raise ValueError("No data available to plot.")

        fig, ax = plt.subplots(figsize=(10, 4))
        if group_by == "raw":
            ax.plot(series.index, series[metric], marker=".", linewidth=1)
            x_label = "Time"
        else:
            ax.bar(series.index.astype(str), series[metric], width=0.8)
            x_label = series.index.name or "Group"
            plt.xticks(rotation=45, ha="right")

        title_metric = "Power" if metric == "power" else "Energy (Wh)"
        title_map = {
            "raw": f"PV {title_metric} - Last {self.days} day(s)",
            "hour": f"PV {title_metric} by Hour of Day (last {self.days} days)",
            "day": f"PV {title_metric} by Day (last {self.days} days)",
            "month": f"PV {title_metric} by Month (last {self.days} days)",
        }

        ax.set_title(title_map[group_by])
        ax.set_xlabel(x_label)
        ax.set_ylabel("W" if metric == "power" else "Wh")
        ax.grid(True, alpha=0.4)
        if group_by == "raw":
            fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
        plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a PNG plot of PV energy or power from the SQLite realtime history."
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        help="PNG output file path (default: pv_energy_plot.png)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days of history to include (default: 30)",
    )
    parser.add_argument(
        "--group-by",
        choices=["raw", "hour", "day", "month"],
        default="day",
        help="Grouping for the plot: raw, hour, day, month (default: day)",
    )
    parser.add_argument(
        "--metric",
        choices=["power", "energy"],
        default="energy",
        help="Metric to plot: power or energy (default: energy)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Config()
    db_path = config.get_sqlite_db_path()
    table_name = config.get_realtime_table_name()

    plotter = PVPlotter(db_path=db_path, table_name=table_name, days=args.days)
    series = plotter.load_series(metric=args.metric, group_by=args.group_by)

    if series.empty:
        raise SystemExit(f"No data found for the last {args.days} days.")

    output_path = Path(args.output)
    plotter.plot(series, output_path, args.group_by, args.metric)
    print(f"Saved plot: {output_path}")


if __name__ == "__main__":
    main()
