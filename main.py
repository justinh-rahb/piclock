import os
import json
import time
import datetime
import requests
from Adafruit_CharLCD import Adafruit_CharLCDPlate

COLORS = [
    ("Red", (1.0, 0.0, 0.0)),
    ("Green", (0.0, 1.0, 0.0)),
    ("Blue", (0.0, 0.0, 1.0)),
    ("Yellow", (1.0, 1.0, 0.0)),
    ("Teal", (0.0, 1.0, 1.0)),
    ("Violet", (1.0, 0.0, 1.0)),
    ("White", (1.0, 1.0, 1.0)),
    ("Off", (0.0, 0.0, 0.0))
]

COLOR_PATH = "/opt/piclock/backlight.txt"
last_color_name = None  # Will track what color is currently applied
COLORS_DICT = dict(COLORS)

# Setup LCD
lcd = Adafruit_CharLCDPlate()
lcd.set_color(1.0, 1.0, 1.0)  # Default white
lcd.clear()

# Try restoring saved color
try:
    COLORS_DICT = dict(COLORS)  # Convert to dictionary
    with open("/opt/piclock/backlight.txt", "r") as f:
        name = f.read().strip()
        if name in COLORS_DICT:
            lcd.set_color(*COLORS_DICT[name])
except Exception as e:
    print(f"Backlight restore failed: {e}")

# Constants
BUTTONS = {
    "select": 0,
    "right": 1,
    "down": 2,
    "up": 3,
    "left": 4
}

menu_index = 0
in_menu = False

# Utility functions
def get_custom_message(path="/opt/piclock/msg.txt"):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except:
        return None

def get_location(path="/opt/piclock/location.txt"):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except:
        return None

def weather_summary(code):
    return {
        0: "Clear",
        1: "Mainly clr",
        2: "Partly cldy",
        3: "Overcast",
        45: "Fog",
        48: "Fog",
        51: "Drizzle",
        53: "Drizzle",
        55: "Drizzle",
        61: "Rain",
        63: "Rain",
        65: "Rain",
        66: "Frz rain",
        67: "Frz rain",
        71: "Snow",
        73: "Snow",
        75: "Snow",
        77: "Snow",
        80: "Shwrs",
        81: "Shwrs",
        82: "Shwrs",
        95: "Storm",
        96: "Storm",
        99: "Storm"
    }.get(code, "Weather")

def get_weather():
    cache_path = "/opt/piclock/weather_cache.json"
    location = get_location()
    if not location:
        return None

    # Check cached weather
    try:
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                cached = json.load(f)
            if time.time() - cached.get("timestamp", 0) < 3600:  # 1 hour
                return cached.get("weather")
    except:
        pass  # fail silently and try to re-fetch

    try:
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
        geo_res = requests.get(geocode_url, timeout=5)
        geo_res.raise_for_status()
        geo_data = geo_res.json()
        if "results" not in geo_data or not geo_data["results"]:
            return None
        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_res = requests.get(weather_url, timeout=5)
        weather_res.raise_for_status()
        weather_data = weather_res.json()

        if "current_weather" in weather_data:
            temp = weather_data["current_weather"]["temperature"]
            code = weather_data["current_weather"]["weathercode"]
            summary = weather_summary(code)
            result = f"{temp:.1f}C {summary}"[:16]

            # Save cache
            with open(cache_path, "w") as f:
                json.dump({
                    "timestamp": time.time(),
                    "weather": result
                }, f)

            return result
    except:
        return None

# Display logic
last_display = ["", ""]

def draw_main():
    global last_display
    line1 = datetime.datetime.now().strftime("%I:%M %p %b %d")[:16]
    line2 = get_custom_message() or get_weather() or "No weather data"

    if [line1, line2] != last_display:
        lcd.clear()
        lcd.message(f"{line1}\n{line2[:16]}")
        last_display = [line1, line2[:16]]

def draw_menu():
    lcd.clear()
    lcd.message(f"Backlight:\n> {COLORS[menu_index][0]}")

def apply_color():
    name, rgb = COLORS[menu_index]
    lcd.set_color(*rgb)
    lcd.clear()
    lcd.message(f"Set to:\n{name}")
    time.sleep(1.5)

# Boot message
lcd.message("  PiClock v2.0\n= Wife Edition =")
time.sleep(2)
lcd.clear()

# Main loop
try:
    while True:
        if in_menu:
            draw_menu()
            while in_menu:
                if lcd.is_pressed(BUTTONS["up"]):
                    menu_index = (menu_index - 1) % len(COLORS)
                    draw_menu()
                    time.sleep(0.2)
                elif lcd.is_pressed(BUTTONS["down"]):
                    menu_index = (menu_index + 1) % len(COLORS)
                    draw_menu()
                    time.sleep(0.2)
                elif lcd.is_pressed(BUTTONS["right"]):
                    apply_color()
                    in_menu = False
                elif lcd.is_pressed(BUTTONS["left"]):
                    lcd.clear()
                    in_menu = False
                time.sleep(0.1)
        else:
            draw_main()

            # Check for backlight color changes from web interface
            try:
                if os.path.exists(COLOR_PATH):
                    with open(COLOR_PATH, "r") as f:
                        name = f.read().strip()
                        if name != last_color_name and name in COLORS_DICT:
                            lcd.set_color(*COLORS_DICT[name])
                            last_color_name = name
            except Exception as e:
                print(f"Error checking backlight.txt: {e}")

            for _ in range(10):
                if lcd.is_pressed(BUTTONS["select"]):
                    in_menu = True
                    break
                time.sleep(0.1)

except KeyboardInterrupt:
    lcd.clear()
    lcd.set_color(0.0, 0.0, 0.0)
    lcd.message("Shutting down LCD")
