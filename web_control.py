from flask import Flask, request, render_template, redirect, url_for
import os
from datetime import datetime

app = Flask(__name__)
app.static_folder = 'static'

now=datetime.now().strftime("%I:%M %p • %B %d, %Y")

# Paths
MESSAGE_PATH = "/opt/piclock/msg.txt"
COLOR_PATH = "/opt/piclock/backlight.txt"

# Available backlight colors
COLORS = {
    "Red": (1.0, 0.0, 0.0),
    "Green": (0.0, 1.0, 0.0),
    "Blue": (0.0, 0.0, 1.0),
    "Yellow": (1.0, 1.0, 0.0),
    "Teal": (0.0, 1.0, 1.0),
    "Violet": (1.0, 0.0, 1.0),
    "White": (1.0, 1.0, 1.0),
    "Off": (0.0, 0.0, 0.0)
}

def apply_color(color_name):
    try:
        from Adafruit_CharLCD import Adafruit_CharLCDPlate
        lcd = Adafruit_CharLCDPlate()
        rgb = COLORS.get(color_name, (1.0, 1.0, 1.0))
        lcd.set_color(*rgb)
        lcd.clear()
        lcd.message(f"Backlight:\n{color_name}")
    except Exception as e:
        print(f"Error applying backlight: {e}")

@app.route("/", methods=["GET", "POST"])
def index():
    # Load current values
    current_msg = ""
    selected_color = "White"

    if os.path.exists(MESSAGE_PATH):
        with open(MESSAGE_PATH, "r") as f:
            current_msg = f.read().strip()

    if os.path.exists(COLOR_PATH):
        with open(COLOR_PATH, "r") as f:
            selected_color = f.read().strip()

    # Handle form submissions
    if request.method == "POST":
        if "clear" in request.form:
            if os.path.exists(MESSAGE_PATH):
                os.remove(MESSAGE_PATH)
            return redirect(url_for('index'))

        if "message" in request.form:
            msg = request.form.get("message", "").strip()
            with open(MESSAGE_PATH, "w") as f:
                f.write(msg)
            return redirect(url_for('index'))

        if "color" in request.form:
            color = request.form.get("color")
            if color in COLORS:
                with open(COLOR_PATH, "w") as f:
                    f.write(color)
                apply_color(color)
            return redirect(url_for('index'))

    #return render_template("index.html", current=current_msg, colors=COLORS.keys(), selected=selected_color)
    return render_template("index.html", current=current_msg, colors=COLORS.keys(), selected=selected_color, now=now)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
