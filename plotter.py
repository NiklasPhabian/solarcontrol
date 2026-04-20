import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt


class Plotter:
    
    def __init__(self, db_table):
        self.db_table = db_table

    def plot_power(self, column, hours=24):
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        data = self.db_table.resampled_timeseries(column=column, start_time=start_time, end_time=end_time, sample_interval=15)
        timestamps = [row["timestamp"] for row in data]
        values = [row[column] for row in data]

        plt.figure(figsize=(10, 5))
        plt.plot(timestamps, values, marker='o')
        plt.title(f"{column} over the last {hours} hours")
        plt.xlabel("Time")
        plt.ylabel("Power (W)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.grid()

        output_dir = "plots"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{column}_last_{hours}_hours.png"
        plt.savefig(os.path.join(output_dir, filename))
        self._write_index_html(output_dir)

    def _write_index_html(self, output_dir: str) -> None:
        images = sorted(
            f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f)) and f.lower().endswith(".png")
        )

        html_lines = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "  <meta charset='UTF-8'>",
            "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            "  <title>SolarControl Plots</title>",
            "  <style>",
            "    body { font-family: Arial, sans-serif; margin: 1rem; background: #f9f9f9; color: #222; }",
            "    h1 { margin-bottom: 0.5rem; }",
            "    section { margin-bottom: 2rem; padding: 1rem; background: #fff; border: 1px solid #ddd; border-radius: 8px; }",
            "    img { display: block; max-width: 100%; height: auto; margin-top: 0.5rem; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <h1>SolarControl Plots</h1>",
            "  <p>Browse the generated plot images below.</p>",
        ]

        for image in images:
            html_lines.extend([
                "  <section>",
                f"    <h2>{image}</h2>",
                f"    <img src=\"{image}\" alt=\"{image}\">",
                "  </section>",
            ])

        html_lines.extend(["</body>", "</html>"])

        with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as index_file:
            index_file.write("\n".join(html_lines))


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


if __name__ == "__main__":
    main()
