import os
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


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
        
    def plot_timeseries(self, column, hours=24):
        start_time, end_time = self._get_time_range(hours=hours)
        data = self.db_table.resampled_timeseries(column=column, start_time=start_time, end_time=end_time, sample_interval=15)
        timestamps = [row["timestamp"] for row in data]
        values = [row[column] if row[column] is not None else float('nan') for row in data]
        unit = guess_unit(column)

        plt.figure(figsize=self._figsize, dpi=self._dpi)
        plt.plot(timestamps, values, marker='o')
        plt.title(f"{column} over the last {hours} hours")
        plt.xlabel("Time")
        plt.ylabel(f"{column} ({unit})")
        plt.gca().xaxis.set_major_locator(MaxNLocator(nbins=12))
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.grid()

        filename = f"{column}_last_{hours}_hours.png"
        self._save_plot(filename)
        return filename

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
