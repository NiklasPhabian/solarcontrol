import os
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


class Plotter:
    OUTPUT_DIR = "www"
    
    def __init__(self, db_table):
        self.db_table = db_table

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
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        filepath = os.path.join(self.OUTPUT_DIR, filename)
        plt.savefig(filepath)
        plt.close()
        
    def plot_power(self, column, hours=24):
        start_time, end_time = self._get_time_range(hours=hours)
        data = self.db_table.resampled_timeseries(column=column, start_time=start_time, end_time=end_time, sample_interval=15)
        timestamps = [row["timestamp"] for row in data]
        values = [row[column] for row in data]

        plt.figure(figsize=(10, 5))
        plt.plot(timestamps, values, marker='o')
        plt.title(f"{column} over the last {hours} hours")
        plt.xlabel("Time")
        plt.ylabel("Power (W)")
        plt.gca().xaxis.set_major_locator(MaxNLocator(nbins=12))
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.grid()

        filename = f"{column}_last_{hours}_hours.png"
        self._save_plot(filename)

    def plot_power_by_hour(self, column, days=7):
        """Plot the average power over the hours of the day.
        
        Args:
            column: The column name to plot (e.g., 'power_pv')
            days: Number of days of historical data to use for averaging
        """
        start_time, end_time = self._get_time_range(days=days)
        
        query_sql = f"""\
        SELECT 
            CAST(strftime('%H', timestamp, 'localtime') AS INTEGER) AS hour,
            AVG({column}) AS avg_power
        FROM {self.db_table.name}
        WHERE timestamp BETWEEN ? AND ?
        GROUP BY hour
        ORDER BY hour;
        """
        rows = self._execute_query(query_sql, start_time, end_time)
        
        # Prepare data for plotting
        hours = list(range(24))
        avg_powers = [0] * 24
        
        for hour, avg_power in rows:
            if avg_power is not None:
                avg_powers[hour] = avg_power
        
        # Create bar chart
        plt.figure(figsize=(12, 6))
        plt.bar(hours, avg_powers, color='steelblue', edgecolor='navy', alpha=0.7)
        plt.title(f"Average {column} by hour of day (last {days} days)")
        plt.xlabel("Hour of day (local time)")
        plt.ylabel("Power (W)")
        plt.xticks(hours)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        filename = f"{column}_by_hour.png"
        self._save_plot(filename)

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
            DATE(timestamp, 'localtime') AS day,
            SUM(hourly_avg) / 1000 AS daily_energy_kwh
        FROM (
            SELECT 
                timestamp,
                AVG({column}) AS hourly_avg
            FROM {self.db_table.name}
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY DATE(timestamp, 'localtime'), strftime('%H', timestamp, 'localtime')
        ) hourly_data
        GROUP BY DATE(timestamp, 'localtime')
        ORDER BY day;
        """
        rows = self._execute_query(query_sql, start_time, end_time)
        
        # Prepare data for plotting
        days_list = [row[0] for row in rows]
        energies = [row[1] if row[1] is not None else 0 for row in rows]
        
        # Create bar chart
        plt.figure(figsize=(14, 6))
        plt.bar(range(len(days_list)), energies, color='green', edgecolor='darkgreen', alpha=0.7)
        plt.title(f"Daily energy production: {column} (last {days} days)")
        plt.xlabel("Date (local time)")
        plt.ylabel("Energy (kWh)")
        plt.xticks(range(len(days_list)), days_list, rotation=45)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        filename = f"{column}_daily_energy.png"
        self._save_plot(filename)

    def plot_daily_trajectory(self, column, days=30):
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
            DATE(timestamp, 'localtime') AS day,
            strftime('%H', timestamp, 'localtime') || ':' || 
            printf('%02d', CAST(CAST(strftime('%M', timestamp, 'localtime') AS INTEGER) / 15 AS INTEGER) * 15) AS quarter_hour,
            AVG({column}) AS avg_power
        FROM {self.db_table.name}
        WHERE timestamp BETWEEN ? AND ?
        GROUP BY DATE(timestamp, 'localtime'), 
                 strftime('%H', timestamp, 'localtime'),
                 CAST(CAST(strftime('%M', timestamp, 'localtime') AS INTEGER) / 15 AS INTEGER) * 15
        ORDER BY day, quarter_hour;
        """
        rows = self._execute_query(query_sql, start_time, end_time)
        
        # Organize data by day
        day_data = {}
        quarter_hours_set = set()
        for day, quarter_hour, avg_power in rows:
            if day not in day_data:
                day_data[day] = {}
            day_data[day][quarter_hour] = avg_power if avg_power is not None else 0
            quarter_hours_set.add(quarter_hour)
        
        # Create line plot
        plt.figure(figsize=(14, 6))
        quarter_hours = sorted(quarter_hours_set)
        
        for day in sorted(day_data.keys()):
            powers = [day_data[day].get(qh, 0) for qh in quarter_hours]
            plt.plot(range(len(quarter_hours)), powers, marker='o', label=day, alpha=0.7, markersize=0)
        
        plt.title(f"Daily power trajectory: {column} (last {days} days)")
        plt.xlabel("Time of day (local time)")
        plt.ylabel("Power (W)")
        # Show quarter-hour labels, but only every 4th one to avoid clutter
        tick_positions = range(0, len(quarter_hours), 4)
        tick_labels = [quarter_hours[i] for i in tick_positions]
        plt.xticks(tick_positions, tick_labels, rotation=45)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        plt.grid(alpha=0.3)
        plt.tight_layout()
        
        filename = f"{column}_daily_trajectory.png"
        self._save_plot(filename)


def main() -> None:
    from database import SQLiteDatabase, SQLiteTable
    from config import Config
    
    config = Config('config_bishop.ini')
    db_path = config['sqlite']['db_path']
    table_name = config['sqlite']['table_name']

    database = SQLiteDatabase(db_path=db_path)
    db_table = SQLiteTable(database=database, name=table_name, columns=['power_pv', 'power_fridge', 'power_dishwasher', 'temperature'])        

    plotter = Plotter(db_table)
    plotter.plot_power("power_pv", hours=24)
    plotter.plot_daily_energy("power_pv", days=7)   # Last week
    plotter.plot_power_by_hour("power_pv", days=7)
    plotter.plot_daily_trajectory("power_pv", days=7)  # Last week




if __name__ == "__main__":
    main()
