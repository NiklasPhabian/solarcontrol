import os
import datetime


class HTMLWriter:

    def __init__(self, output_dir: str, plot_files: list, current_conditions: dict):
        self.output_dir = output_dir
        self.output_file = os.path.join(output_dir, "index.html")
        self.html_lines = []
        self.plots = plot_files
        self.current_conditions = current_conditions


    def make_html_header(self) -> None:
        """Generate the HTML header for the index file."""
        self.html_lines = [
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
        ]

    def make_title(self) -> None:
        """Generate the title for the HTML document."""
        time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.html_lines.extend([
            "  <h1>SolarControl Plots</h1>",
            f"  <p>Generated on {time}</p>",
        ])

    def get_unit(self, quantity) -> dict:
        """Return the units for each measurement. 
        quantities may have suffixes such as _blue, _black, _white."""
        units = {
            "power": "W",
            "temperature": "°C",
            "humidity": "%"
        }
        if "_" in quantity:
            base_quantity = quantity.split("_")[0]
            return units.get(base_quantity, "")

        return units.get(quantity, "")
        

    def make_current_conditions_section(self) -> None:
        """Generate an HTML section displaying the current conditions."""
        current_conditions_html = "<table border='1'>"        
        for key, value in self.current_conditions.items():
            current_conditions_html += f"""<tr><td >{key}</td><td align="right">{value} {self.get_unit(key)}</td></tr>"""
        current_conditions_html += "</table>"

        self.html_lines.extend([
            "  <section>",
            "    <h1>Current Conditions</h1>",
            current_conditions_html,
            "  </section>",
        ])


    def make_plot_sections(self) -> None:
        """Generate HTML sections displaying the plot files."""
        self.html_lines.extend([
            "  <section>",
            "    <h1>SolarControl Plots</h1>",
            "    <p>Browse the generated plot images below.</p>",
            "  </section>",
        ])
        for plot in self.plots:
            self.html_lines.extend([
                "  <section>",
                f"    <h2>{plot}</h2>",
                f"    <img src=\"{plot}\" alt=\"{plot}\">",
                "  </section>",
            ])

    def make_html_footer(self) -> None:
        """Generate the HTML footer for the index file."""
        self.html_lines.extend([
            "</body>",
            "</html>"
        ])

    def write_html(self) -> None:
        """Generate an HTML index file displaying current conditions and plots.
        """
        
        self.make_html_header()
        self.make_title()
        self.make_current_conditions_section()
        self.make_plot_sections()
        self.make_html_footer()

        with open(self.output_file, "w", encoding="utf-8") as index_file:
            index_file.write("\n".join(self.html_lines))
