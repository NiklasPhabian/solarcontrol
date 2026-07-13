import os
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator


def guess_unit(column):
    """Guess the unit of a column based on its name."""
    if "power" in column:
        return "W"
    elif "temperature" in column:
        return "°C"
    elif "energy" in column:
        return "kWh"
    else:
        return ""


class Plotter:
    OUTPUT_DIR = "www"
    _figsize = (16, 9)
    _dpi = 75

    def __init__(self, db_table):
        self.db_table = db_table
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def _get_time_range(self, hours=None, days=None):
        """Get start and end time based on hours or days.

        Returns timezone-aware datetime objects in UTC.
        """
        end_time = datetime.now(timezone.utc)
        if hours:
            start_time = end_time - timedelta(hours=hours)
        elif days:
            start_time = end_time - timedelta(days=days)
        else:
            raise ValueError("Must specify either hours or days")
        return start_time, end_time

    def _execute_query(self, query_sql, start_time, end_time):
        """Execute a database query and return results."""
        cursor = self.db_table.database.conn.execute(
            query_sql,
            (start_time.isoformat(), end_time.isoformat())
        )
        return cursor.fetchall()

    def _save_plot(self, filename):
        """Save the current plot and update index.html."""
        filepath = os.path.join(self.OUTPUT_DIR, filename)
        plt.savefig(filepath)
        plt.close()
        return filepath

    @staticmethod
    def _nan_or_value(value):
        return value if value is not None else float('nan')

    def _fetch_resampled_timeseries(self, columns, start_time, end_time, sample_interval=15):
        """Return resampled averages for one or more columns."""
        if not columns:
            raise ValueError("columns must not be empty")

        select_columns = ",\n            ".join(
            f'AVG("{column}") AS "{column}"' for column in columns
        )
        query_sql = f"""\
        SELECT
            datetime(strftime('%Y-%m-%d %H:', timestamp) || printf('%02d', (strftime('%M', timestamp) / {sample_interval}) * {sample_interval}), 'localtime') AS interval,
            {select_columns}
        FROM {self.db_table.name}
        WHERE datetime(timestamp) BETWEEN datetime(?) AND datetime(?)
        GROUP BY interval
        ORDER BY interval;
        """
        rows = self._execute_query(query_sql, start_time, end_time)

        data = []
        for row in rows:
            row_data = {"timestamp": row[0]}
            for idx, column in enumerate(columns, start=1):
                row_data[column] = row[idx]
            data.append(row_data)
        return data

    def _plot_axis_series(self, axis, timestamps, data, columns):
        """Plot one or more columns onto the provided axis."""
        handles = []
        for column_spec in columns:
            if isinstance(column_spec, str):
                column = column_spec
                label = column_spec
                color = None
            else:
                column = column_spec["column"]
                label = column_spec.get("label", column)
                color = column_spec.get("color")

            values = [self._nan_or_value(row.get(column)) for row in data]
            handle, = axis.plot(timestamps, values, marker='o', label=label, color=color)
            handles.append(handle)
        return handles

    def _axis_label_for_columns(self, columns):
        units = []
        for column_spec in columns:
            column = column_spec if isinstance(column_spec, str) else column_spec["column"]
            unit = guess_unit(column)
            if unit and unit not in units:
                units.append(unit)

        if len(units) == 1:
            return units[0]
        if len(units) > 1:
            return ", ".join(units)
        return ""

    @staticmethod
    def _column_name(column_spec):
        return column_spec if isinstance(column_spec, str) else column_spec["column"]

    @staticmethod
    def _format_tick_value(value):
        if abs(value) >= 100:
            return f"{value:.0f}"
        if abs(value - round(value)) < 0.05:
            return f"{value:.0f}"
        return f"{value:.1f}"

    def _apply_axis_tick_units(self, axis, unit):
        if not unit:
            return

        axis.yaxis.set_major_formatter(
            FuncFormatter(lambda value, _pos: f"{self._format_tick_value(value)} {unit}")
        )

    def plot_resampled_timeseries(self,
                                  left_columns,
                                  hours=24,
                                  right_columns=None,
                                  sample_interval=15,
                                  title=None,
                                  left_axis_label=None,
                                  right_axis_label=None,
                                  left_tick_unit=None,
                                  right_tick_unit=None,
                                  filename=None):
        """Plot one or more resampled columns, optionally with a second y-axis."""
        right_columns = right_columns or []
        start_time, end_time = self._get_time_range(hours=hours)

        all_columns = [self._column_name(spec) for spec in left_columns + right_columns]
        unique_columns = list(dict.fromkeys(all_columns))
        data = self._fetch_resampled_timeseries(
            columns=unique_columns,
            start_time=start_time,
            end_time=end_time,
            sample_interval=sample_interval,
        )
        timestamps = [row["timestamp"] for row in data]

        plt.figure(figsize=self._figsize, dpi=self._dpi)
        ax_left = plt.gca()
        left_handles = self._plot_axis_series(ax_left, timestamps, data, left_columns)

        if left_axis_label is None:
            left_axis_label = ""

        if left_tick_unit is None:
            left_unit = self._axis_label_for_columns(left_columns)
        else:
            left_unit = left_tick_unit

        left_column_names = ", ".join(self._column_name(spec) for spec in left_columns)
        if not title:
            title = f"{left_column_names} over the last {hours} hours"

        if not filename:
            first_left_column = self._column_name(left_columns[0])
            filename = f"{first_left_column}_last_{hours}_hours.png"

        ax_left.set_title(title)
        ax_left.set_xlabel("Time")
        ax_left.set_ylabel(left_axis_label)
        self._apply_axis_tick_units(ax_left, left_unit)
        ax_left.xaxis.set_major_locator(MaxNLocator(nbins=12))

        legend_handles = list(left_handles)
        if right_columns:
            ax_right = ax_left.twinx()
            right_handles = self._plot_axis_series(ax_right, timestamps, data, right_columns)
            legend_handles.extend(right_handles)
            if right_axis_label is None:
                right_axis_label = ""
            if right_tick_unit is None:
                right_unit = self._axis_label_for_columns(right_columns)
            else:
                right_unit = right_tick_unit
            ax_right.set_ylabel(right_axis_label)
            self._apply_axis_tick_units(ax_right, right_unit)

        labels = [handle.get_label() for handle in legend_handles]
        if legend_handles:
            ax_left.legend(
                legend_handles,
                labels,
                loc='best',
                framealpha=0.65,
                facecolor='white',
                edgecolor='0.5',
            )

        for label in ax_left.get_xticklabels():
            label.set_rotation(45)
            label.set_horizontalalignment('right')
        plt.tight_layout()
        ax_left.grid()

        self._save_plot(filename)
        return filename
        
    def plot_timeseries(self, column, hours=24):
        return self.plot_resampled_timeseries(
            left_columns=[{"column": column, "label": column}],
            hours=hours,
            title=f"{column} over the last {hours} hours",
            left_axis_label=column,
            filename=f"{column}_last_{hours}_hours.png",
        )

    def plot_bwwp_with_fhs280_temperatures(self, hours=24, sample_interval=15):
        """Plot BWWP power on left axis and FHS280 temperatures on right axis."""
        return self.plot_resampled_timeseries(
            left_columns=[{"column": "power_bwwp", "label": "power_bwwp", "color": "tab:blue"}],
            right_columns=[
                {"column": "fhs280_t1", "label": "fhs280_t1", "color": "tab:red"},
                {"column": "fhs280_t2", "label": "fhs280_t2", "color": "tab:green"},
            ],
            hours=hours,
            sample_interval=sample_interval,
            title=f"power_bwwp + fhs280 temperatures over the last {hours} hours",
            left_axis_label="Power",
            right_axis_label="Temperature",
            left_tick_unit="W",
            right_tick_unit="°C",
            filename=f"power_bwwp_last_{hours}_hours.png",
        )

    def plot_pv_phase_powers(self, hours=24, sample_interval=15):
        """Plot PV phase powers (L1/L2/L3) together on one axis."""
        return self.plot_resampled_timeseries(
            left_columns=[
                {"column": "power_pv_l1", "label": "power_pv_l1", "color": "tab:red"},
                {"column": "power_pv_l2", "label": "power_pv_l2", "color": "tab:green"},
                {"column": "power_pv_l3", "label": "power_pv_l3", "color": "tab:blue"},
            ],
            hours=hours,
            sample_interval=sample_interval,
            title=f"power_pv_l1 + power_pv_l2 + power_pv_l3 over the last {hours} hours",
            left_axis_label="PV Power",
            left_tick_unit="W",
            filename=f"power_pv_l1_l2_l3_last_{hours}_hours.png",
        )

    def plot_avg_by_hours_of_day(self, column, days=7):
        """Plot the average over the hours of the day.
        
        Args:
            column: The column name to plot (e.g., 'power_pv')
            days: Number of days of historical data to use for averaging
        """
        start_time, end_time = self._get_time_range(days=days)
        
        query_sql = f"""\
        SELECT 
            CAST(substr(t."timestamp", 12, 2) AS INTEGER) AS hour,
            AVG({column}) AS avgerage
        FROM {self.db_table.name} AS t
        WHERE datetime(t."timestamp") BETWEEN datetime(?) AND datetime(?)
        GROUP BY hour
        ORDER BY hour;
        """
        rows = self._execute_query(query_sql, start_time, end_time)
        
        # Prepare data for plotting
        hours = list(range(24))
        avgs = [float('nan')] * 24

        for hour, avg in rows:
            if avg is not None:
                avgs[hour] = avg
        
        unit = guess_unit(column)
        # Create bar chart
        plt.figure(figsize=self._figsize, dpi=self._dpi)
        plt.bar(hours, avgs, color='steelblue', edgecolor='navy', alpha=0.7)
        plt.title(f"Average {column} by hour of day (last {days} days)")
        plt.xlabel("Hour of day (local time)")
        plt.ylabel(f"{column} ({unit})")
        plt.xticks(hours)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()

        filename = f"{column}_by_hour.png"
        
        self._save_plot(filename)
        return filename

    def plot_daily_energy(self, column, days=30):
        """Plot the daily energy production for the last n days as a bar chart.
        
        Energy is calculated by taking hourly averages and summing them per day.
        
        Args:
            column: The column name to plot (e.g., 'power_pv')
            days: Number of days to show in the plot
        """
        start_time, end_time = self._get_time_range(days=days)
        
        query_sql = f"""\
        SELECT 
            day,
            SUM(hourly_avg) / 1000 AS daily_energy_kwh
        FROM (
            SELECT 
                substr(t."timestamp", 1, 10) AS day,
                AVG({column}) AS hourly_avg
            FROM {self.db_table.name} AS t
            WHERE datetime(t."timestamp") BETWEEN datetime(?) AND datetime(?)
            GROUP BY substr(t."timestamp", 1, 10), CAST(substr(t."timestamp", 12, 2) AS INTEGER)
        ) hourly_data
        GROUP BY day
        ORDER BY day;
        """
        rows = self._execute_query(query_sql, start_time, end_time)
        
        # Prepare data for plotting
        days_list = [row[0] for row in rows]
        energies = [row[1] if row[1] is not None else float('nan') for row in rows]
        
        # Create bar chart
        plt.figure(figsize=self._figsize, dpi=self._dpi)
        plt.bar(range(len(days_list)), energies, color='green', edgecolor='darkgreen', alpha=0.7)
        plt.title(f"Daily energy: {column} (last {days} days)")
        plt.xlabel("Date (local time)")
        plt.ylabel("Energy (kWh)")
        plt.xticks(range(len(days_list)), days_list, rotation=45)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        filename = f"{column}_daily_energy.png"
        self._save_plot(filename)
        return filename

    def plot_daily_trajectory(self, column, days=30, start_hour=5, end_hour=20):
        """Plot the daily power trajectory with one line per day.
        
        Shows how power changes throughout the day by plotting quarter-hourly averages.
        Each day is shown as a separate line.
        
        Args:
            column: The column name to plot (e.g., 'power_pv')
            days: Number of days to include in the plot
        """
        start_time, end_time = self._get_time_range(days=days)
        
        query_sql = f"""\
        SELECT 
            substr(t."timestamp", 1, 10) AS day,
            substr(t."timestamp", 12, 2) || ':' || 
            printf('%02d', CAST(CAST(substr(t."timestamp", 15, 2) AS INTEGER) / 15 AS INTEGER) * 15) AS quarter_hour,
            AVG({column}) AS avg_power
        FROM {self.db_table.name} AS t
        WHERE datetime(t."timestamp") BETWEEN datetime(?) AND datetime(?)
        AND CAST(substr(t."timestamp", 12, 2) AS INTEGER) BETWEEN {start_hour} AND {end_hour}  -- Focus on daytime hours
        GROUP BY substr(t."timestamp", 1, 10), 
                 substr(t."timestamp", 12, 2),
                 CAST(CAST(substr(t."timestamp", 15, 2) AS INTEGER) / 15 AS INTEGER) * 15
        ORDER BY day, quarter_hour;
        """
        rows = self._execute_query(query_sql, start_time, end_time)
        
        # Organize data by day
        day_data = {}
        quarter_hours_set = set()
        for day, quarter_hour, avg_power in rows:
            if day not in day_data:
                day_data[day] = {}
            day_data[day][quarter_hour] = avg_power if avg_power is not None else float('nan')
            quarter_hours_set.add(quarter_hour)
        
        # Create line plot
        plt.figure(figsize=self._figsize, dpi=self._dpi)
        quarter_hours = sorted(quarter_hours_set)
        
        sorted_days = sorted(day_data.keys())
        for i, day in enumerate(sorted_days):
            powers = [day_data[day].get(qh, float('nan')) for qh in quarter_hours]
            is_latest = (i == len(sorted_days) - 1)
            linewidth = 2.5 if is_latest else 0.8
            zorder = 3 if is_latest else 1
            alpha = 0.95 if is_latest else 0.7
            color = 'red' if is_latest else 'blue'
            plt.plot(range(len(quarter_hours)), powers,
                     marker='o', label=day, alpha=alpha, markersize=0,
                     linewidth=linewidth, zorder=zorder, color=color)
        
        plt.title(f"Daily power trajectory: {column} (last {days} days)")
        plt.xlabel("Time of day (local time)")
        plt.ylabel("Power (W)")
        # Show quarter-hour labels, but only every 4th one to avoid clutter
        tick_positions = range(0, len(quarter_hours), 4)
        tick_labels = [quarter_hours[i] for i in tick_positions]
        plt.xticks(tick_positions, tick_labels, rotation=45)
        
        plt.legend(loc='upper left', fontsize=8)
        plt.grid(alpha=0.3)
        plt.tight_layout()
        
        filename = f"{column}_daily_trajectory.png"
        self._save_plot(filename)
        return filename


def main() -> None:
    from database import SQLiteDatabase, SQLiteTable
    from config import Config
    
    config = Config('config_bishop.ini')
    db_path = config['sqlite']['db_path']
    table_name = config['sqlite']['table_name']

    database = SQLiteDatabase(db_path=db_path)
    db_table = SQLiteTable(database=database, name=table_name, columns=['power_pv', 'power_fridge', 'power_dishwasher', 'temperature'])        

    plotter = Plotter(db_table)
    plotter.plot_timeseries("power_pv", hours=24)
    plotter.plot_daily_energy("power_pv", days=30)  
    plotter.plot_avg_by_hours_of_day("power_pv", days=7)
    plotter.plot_daily_trajectory("power_pv", days=30) 
    plotter.plot_timeseries("temperature", hours=24)
    plotter.plot_daily_trajectory("temperature", days=30, start_hour=0, end_hour=23) 


if __name__ == "__main__":
    main()
