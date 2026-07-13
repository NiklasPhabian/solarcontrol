import os
import luma.core.interface.serial
import luma.oled.device
import luma.core.render
import PIL.ImageFont
import time


class Display:

    def __init__(self, port, address):
        self.port = int(port)
        self.address = address
        self.serial =  luma.core.interface.serial.i2c(port=self.port, address=self.address)
        self.device = luma.oled.device.ssd1306(self.serial)

        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if os.path.exists(font_path):
            self.font_path = font_path
            self.font = PIL.ImageFont.truetype(font_path, size=48)
        else:
            self.font_path = None
            self.font = PIL.ImageFont.load_default()

    def _best_font(self, text, max_width, max_height):
        if not self.font_path:
            return self.font

        for size in range(64, 8, -2):
            font = PIL.ImageFont.truetype(self.font_path, size=size)
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            if text_width <= max_width and text_height <= max_height:
                return font

        return PIL.ImageFont.truetype(self.font_path, size=8)

    def _draw_centered(self, draw, text, font=None):
        font = font or self._best_font(text, self.device.width, self.device.height)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = max((self.device.width - text_width) // 2, 0)
        y = max((self.device.height - text_height) // 2, 0)
        draw.text((x, y), text, font=font, fill="white")

    def show_text(self, text, font=None):
        """
        Display arbitrary text centered on the OLED.
        """
        with luma.core.render.canvas(self.device) as draw:
            self._draw_centered(draw, text, font=font)


    def format_quantity(self, quantity, unit):
        """
        Format a quantity with its unit, using appropriate SI prefixes.
        """
        if abs(quantity) >= 1_000_000:
            quantity /= 1_000_000
            unit = 'M' + unit
            return f"{quantity:.2f} {unit}"
        elif abs(quantity) >= 1000:
            quantity /= 1000
            unit = 'k' + unit
            return f"{quantity:.2f} {unit}"
        elif abs(quantity) < 1:
            quantity *= 1000
            unit = 'm' + unit
            return f"{quantity:.2f} {unit}"
        else:
            return f"{quantity:.1f} {unit}"

    def display_quantity(self, quantity, unit):
        """
        Display a quantity with its unit, centered on the OLED.
        """
        if quantity is None:
            self.show_text("No data")
            return

        text = self.format_quantity(quantity, unit)
        self.show_text(text)

    def display_celsius(self, temp_c):
        """
        Display a temperature in Celsius, formatted nicely.
        """
        self.display_quantity(temp_c, "°C")

    def display_watts(self, watts):
        """
        Display power in watts, formatted nicely.
        """
        self.display_quantity(watts, "W")

    def show_bar_chart(self, data):
        """
        Display a simple bar chart on the OLED.
        data: list of numeric values
        """
        if not data:
            self.show_text("No data")
            return

        with luma.core.render.canvas(self.device) as draw:
            max_val = max(data)
            if max_val == 0:
                max_val = 1  # Avoid division by zero

            num_bars = len(data)
            bar_width = self.device.width // num_bars
            spacing = 1  # pixels between bars

            for i, val in enumerate(data):
                bar_height = int((val / max_val) * (self.device.height - 10))  # Leave space for labels if needed
                x = i * bar_width + spacing // 2
                y = self.device.height - bar_height
                draw.rectangle([x, y, x + bar_width - spacing, self.device.height], fill="white")

    def show_chart_with_last_value(self, bars, unit, value=None):
        """
        Display a bar chart at the bottom and the last value on top.

        Supports:
          - all positive values
          - all negative values
          - mixed positive/negative values
        """

        if not bars:
            self.show_text("No data")
            return

        if value is None:
            value = bars[-1]

        text = self.format_quantity(value, unit)

        with luma.core.render.canvas(self.device) as draw:
            # -----------------------------
            # Draw value text
            # -----------------------------
            font = self._best_font(text, self.device.width, 12)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            x_text = (self.device.width - text_width) // 2
            draw.text((x_text, 0), text, font=font, fill="white")

            # -----------------------------
            # Chart dimensions
            # -----------------------------
            chart_top = text_height + 5
            chart_bottom = self.device.height - 1
            chart_height = chart_bottom - chart_top + 1

            num_bars = len(bars)
            bar_width = max(1, self.device.width // num_bars)
            spacing = 1

            # -----------------------------
            # Scale
            # -----------------------------
            min_val = min(bars)
            max_val = max(bars)

            # Always include zero
            min_val = min(min_val, 0)
            max_val = max(max_val, 0)

            if min_val == max_val:
                max_val += 1

            value_range = max_val - min_val

            # Pixel coordinate of the zero line
            zero_y = chart_top + int(max_val / value_range * (chart_height - 1))

            # Clamp to display
            zero_y = max(chart_top, min(chart_bottom, zero_y))

            # Draw zero line if both positive and negative values exist
            if min_val < 0 < max_val:
                draw.line(
                    [(0, zero_y), (self.device.width - 1, zero_y)],
                    fill="white",
                )

            # -----------------------------
            # Draw bars
            # -----------------------------
            for i, val in enumerate(bars):
                x0 = i * bar_width + spacing // 2
                x1 = x0 + bar_width - spacing

                # Pixel position of the value
                y_val = chart_top + int(
                    (max_val - val) / value_range * (chart_height - 1)
                )

                if val >= 0:
                    y0 = y_val
                    y1 = zero_y
                else:
                    y0 = zero_y
                    y1 = y_val

                draw.rectangle(
                    [x0, min(y0, y1), x1, max(y0, y1)],
                    fill="white",
                )


    def show_controller_state(self, state, power_balance, cooldown_remaining_s=None):
        """Show controller mode in the yellow band (top 16 px) + context in the blue area.

        The display hardware has a fixed two-colour split:
          - rows  0-15  are driven by yellow phosphor
          - rows 16-63  are driven by blue phosphor

        Layout:
          yellow band  →  state label  (HP / EL / OFF / INIT)
          blue area    →  power balance, or HP cooldown countdown
        """
        YELLOW_TOP    = 0
        YELLOW_HEIGHT = 16
        BLUE_TOP      = 16
        BLUE_HEIGHT   = self.device.height - BLUE_TOP  # 48 px on a 64-px display

        state_label = state if state is not None else "INIT"

        if cooldown_remaining_s is not None and cooldown_remaining_s > 0:
            sub = f"CD {int(cooldown_remaining_s)}s"
        else:
            sub = self.format_quantity(power_balance, "W") if power_balance is not None else "---"

        with luma.core.render.canvas(self.device) as draw:
            # --- Yellow band: state label ---
            font_top = self._best_font(state_label, self.device.width, YELLOW_HEIGHT - 2)
            bbox = draw.textbbox((0, 0), state_label, font=font_top)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (self.device.width - tw) // 2
            y = YELLOW_TOP + (YELLOW_HEIGHT - th) // 2
            draw.text((x, y), state_label, font=font_top, fill="white")

            # --- Blue area: context line ---
            font_bot = self._best_font(sub, self.device.width, BLUE_HEIGHT - 4)
            bbox = draw.textbbox((0, 0), sub, font=font_bot)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (self.device.width - tw) // 2
            y = BLUE_TOP + (BLUE_HEIGHT - th) // 2
            draw.text((x, y), sub, font=font_bot, fill="white")

    def show_chart_with_last_value_old(self, bars, unit, value=None):
        """
        Display a bar chart at the bottom and the last value on top.
        data: list of numeric values
        """
        if not bars:
            self.show_text("No data")
            return

        # Format last_value like power
        if value is None:
            value = bars[-1]

        text = self.format_quantity(value, unit)

        with luma.core.render.canvas(self.device) as draw:
            # Draw the text on top
            font = self._best_font(text, self.device.width, 12)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x_text = (self.device.width - text_width) // 2
            y_text = 0
            draw.text((x_text, y_text), text, font=font, fill="white")

            # Draw bars below
            max_val = max(bars)
            if max_val == 0:
                max_val = 1

            num_bars = len(bars)
            bar_width = self.device.width // num_bars
            spacing = 1
            chart_top = text_height + 5  # Start bars below text
            chart_height = self.device.height - chart_top

            for i, val in enumerate(bars):
                bar_height = int((val / max_val) * chart_height)
                x_bar = i * bar_width + spacing // 2
                y_bar = self.device.height - bar_height
                draw.rectangle([x_bar, y_bar, x_bar + bar_width - spacing, self.device.height], fill="white")


if __name__ == '__main__':
    from database import SQLiteDatabase, SQLiteTable
    from config import Config

    config = Config('config_bishop.ini')

    address = config['display']['address']
    port = config['display']['port']

    display = Display(port=port, address=address)
    db_path = config['sqlite']['db_path']
    table_name = config['sqlite']['table_name']

    database = SQLiteDatabase(db_path=db_path)
    db_table = SQLiteTable(database=database, name=table_name, columns=['power_pv', 'power_fridge', 'power_dishwasher', 'temperature'])

    while True:
        bars = db_table.latest_n_resampled_values(n=60, column="power_pv", aggregate="AVG", sample_interval=15)   
        value = db_table.latest_value("power_pv")
        display.show_chart_with_last_value(bars=bars, value=value, unit='W')
        time.sleep(2)

