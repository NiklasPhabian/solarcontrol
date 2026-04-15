import os
import luma.core.interface.serial
import luma.oled.device
import luma.core.render
import PIL.ImageFont
import time
from config import Config

config = Config()


class PVDisplay:

    def __init__(self):
        self.serial =  luma.core.interface.serial.i2c(port=1, address=0x3C)
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

    def show_power(self, power):
        """
        Display current power centered on the OLED.
        """

        if power is None:
            self.show_text("No data")
            return

        # Format power nicely
        if power >= 1000:
            text = f"{power / 1000:.2f} kW"
        else:
            text = f"{power:.1f} W"

        self.show_text(text)


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


    def show_chart_with_last_value(self, bars, value=None):
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

        if value >= 1000:
            text = f"{value / 1000:.2f} kW"
        else:
            text = f"{value:.1f} W"

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


def display_loop():
    display = PVDisplay()
    power = 123   # Example power value

    while True:
        display.show(power)
        time.sleep(2)


def display_list():
    display = PVDisplay()
    lines = ['Hello Qian', 'You are pretty', 'Have a nice day!']
    for line in lines:
        display.show_text(line)
        time.sleep(2)


if __name__ == '__main__':
    import database
    
    display = PVDisplay()
    db_path = config.sqlite_db_path()
    table_name = config.realtime_table_name()

    db = database.SQLiteDatabase(db_path, table_name)
    
    while True:
        bars = [row['power'] for row in db.latest_n15mins(60)]
        value = db.latest_realtime()['power']
        display.show_chart_with_last_value(bars=bars, value=value)
        time.sleep(2)
        