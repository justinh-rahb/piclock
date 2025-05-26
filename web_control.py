from flask import Flask, request, render_template, redirect, url_for, flash
import os
import datetime
import subprocess

app = Flask(__name__)
app.static_folder = 'static'
app.secret_key = 'os_settings_secret_key' # Required for flash messages

# Paths
MESSAGE_PATH = "/opt/piclock/msg.txt"
COLOR_PATH = "/opt/piclock/backlight.txt"
LOCATION_PATH = "/opt/piclock/location.txt" # Added from instructions
NTP_CONFIG_PATH = "/etc/systemd/timesyncd.conf" # Added from instructions

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

# Timezone functions
def get_available_timezones():
    try:
        # capture_output=True implies stdout=PIPE and stderr=PIPE. No need to specify stderr again.
        result = subprocess.run(["timedatectl", "list-timezones"], capture_output=True, text=True, check=True)
        return result.stdout.strip().split("\n")
    except subprocess.CalledProcessError as e:
        print(f"Error getting available timezones: {e}. Stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
        # Flashing here might be too noisy for a GET operation, returning empty list is okay.
        return []
    except FileNotFoundError:
        print("Error: timedatectl command not found. Cannot get available timezones.")
        return []

def get_current_timezone():
    try:
        result = subprocess.run(["timedatectl", "status"], capture_output=True, text=True, check=True)
        for line in result.stdout.split("\n"):
            if "Time zone:" in line:
                return line.split(":", 1)[1].strip().split(" ")[0]
        return "UTC" # Default if not found
    except subprocess.CalledProcessError as e:
        print(f"Error getting current timezone: {e}. Stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
        return "UTC" # Default on error
    except FileNotFoundError:
        print("Error: timedatectl command not found. Cannot get current timezone.")
        return "UTC"

# NTP Server functions
def get_current_ntp_server():
    ntp_server = ""
    try:
        if os.path.exists(NTP_CONFIG_PATH):
            with open(NTP_CONFIG_PATH, "r") as f:
                for line in f:
                    if line.strip().startswith("NTP="):
                        ntp_server = line.strip().split("=", 1)[1]
                        break
        return ntp_server
    except Exception as e:
        print(f"Error reading NTP config: {e}")
        return "" # Return empty or a default/error indicator

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
    # Load current values & OS data
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    # message = request.args.get("message", "") # This will be replaced by flashed messages

    current_msg = ""
    if os.path.exists(MESSAGE_PATH):
        with open(MESSAGE_PATH, "r") as f:
            current_msg = f.read().strip()

    selected_color = "White"
    if os.path.exists(COLOR_PATH):
        with open(COLOR_PATH, "r") as f:
            selected_color = f.read().strip()

    current_location = ""
    if os.path.exists(LOCATION_PATH):
        with open(LOCATION_PATH, "r") as f:
            current_location = f.read().strip()

    available_timezones = get_available_timezones()
    current_timezone = get_current_timezone()
    current_ntp_server = get_current_ntp_server()

    # Handle form submissions for items directly on the main page (message, color, location)
    if request.method == "POST":
        action_taken = False # Flag to see if any POST action was handled by this route
        if "clear" in request.form:
            if os.path.exists(MESSAGE_PATH):
                try:
                    os.remove(MESSAGE_PATH)
                    current_msg = ""
                    flash("Message cleared successfully.", "success")
                except OSError as e:
                    flash(f"Error clearing message: {e}", "error")
            else:
                flash("No message to clear.", "info")
            action_taken = True # Still consider it an action
        elif "message" in request.form:
            msg_to_set = request.form.get("message", "").strip()
            try:
                import tempfile
                tmp_path = None
                os.makedirs(os.path.dirname(MESSAGE_PATH), exist_ok=True) # Ensure dir exists for sudo cp
                with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmpfile:
                    tmp_path = tmpfile.name
                    tmpfile.write(msg_to_set)
                subprocess.run(["sudo", "cp", tmp_path, MESSAGE_PATH], check=True)
                current_msg = msg_to_set
                flash("Message updated successfully.", "success")
            except (IOError, subprocess.CalledProcessError, FileNotFoundError) as e:
                flash(f"Error updating message: {e}", "error")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            action_taken = True
        elif "color" in request.form:
            color_name = request.form.get("color")
            if color_name in COLORS:
                try:
                    import tempfile
                    tmp_path = None
                    os.makedirs(os.path.dirname(COLOR_PATH), exist_ok=True)
                    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmpfile:
                        tmp_path = tmpfile.name
                        tmpfile.write(color_name)
                    subprocess.run(["sudo", "cp", tmp_path, COLOR_PATH], check=True)
                    apply_color(color_name) 
                    selected_color = color_name
                    flash(f"Backlight color set to {color_name}.", "success")
                except (IOError, subprocess.CalledProcessError, FileNotFoundError) as e:
                    flash(f"Error setting backlight color: {e}", "error")
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        os.remove(tmp_path)
            else:
                flash(f"Invalid color selected: {color_name}", "error")
            action_taken = True
        elif "location" in request.form:
            new_location = request.form.get("location", "").strip()
            try:
                import tempfile
                tmp_path = None
                os.makedirs(os.path.dirname(LOCATION_PATH), exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmpfile:
                    tmp_path = tmpfile.name
                    tmpfile.write(new_location)
                subprocess.run(["sudo", "cp", tmp_path, LOCATION_PATH], check=True)
                current_location = new_location
                flash("Location updated successfully.", "success")
            except (IOError, subprocess.CalledProcessError, FileNotFoundError) as e:
                flash(f"Error updating location: {e}", "error")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            action_taken = True
        
        if action_taken:
            # Instead of passing message via render_template, rely on flashed messages
            # and redirect to show them cleanly after a POST.
            return redirect(url_for('index'))

    # For GET requests, or if no POST action was taken (should not happen with current form structure)
    return render_template("index.html",
                           current_time=current_time,
                           current_msg=current_msg,
                           colors=COLORS.keys(),
                           selected_color=selected_color,
                           # message=message, # Removed, using flash
                           current_location=current_location,
                           available_timezones=available_timezones,
                           current_timezone=current_timezone,
                           current_ntp_server=current_ntp_server)

@app.route("/set_timezone", methods=["POST"])
def set_timezone_route():
    if "timezone" in request.form:
        new_timezone = request.form["timezone"]
        try:
            # Capture stderr for more detailed error reporting
            result = subprocess.run(["sudo", "timedatectl", "set-timezone", new_timezone], check=True, capture_output=True, text=True) # capture_output implies stderr capture
            flash(f"Timezone successfully set to {new_timezone}.", "success")
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode().strip() if e.stderr else str(e)
            flash(f"Error setting timezone: {error_output}", "error")
        except FileNotFoundError:
            flash("Error: timedatectl command not found. Cannot set timezone.", "error")
    else:
        flash("No timezone provided.", "error")
    return redirect(url_for("index"))

@app.route("/set_ntp_server", methods=["POST"])
def set_ntp_server_route():
    if "ntp_server" in request.form:
        new_ntp_server = request.form["ntp_server"].strip()
        original_content = ""
        
        # The main logic for processing NTP server update is within this try block
        try:
            if os.path.exists(NTP_CONFIG_PATH):
                with open(NTP_CONFIG_PATH, "r") as f_read:
                    original_content = f_read.read()
            
            lines = original_content.splitlines()
            new_lines = []
            ntp_line_found = False
            for line in lines:
                stripped_line = line.strip()
                if stripped_line.startswith("NTP="):
                    if new_ntp_server:
                        new_lines.append(f"NTP={new_ntp_server}")
                    else:
                        new_lines.append(f"#{stripped_line}") # Comment out existing if new is empty
                    ntp_line_found = True
                elif stripped_line.startswith("#NTP=") and new_ntp_server:
                    new_lines.append(f"NTP={new_ntp_server}") # Replace commented line
                    ntp_line_found = True
                else:
                    new_lines.append(line) # Keep other lines as is
            
            if not ntp_line_found and new_ntp_server: # If no NTP line existed and new server is provided
                new_lines.append(f"NTP={new_ntp_server}")

            # Write to a temporary file first
            import tempfile
            tmp_path = None # Initialize tmp_path to ensure it's always defined for finally block
            try:
                with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmpfile:
                    tmp_path = tmpfile.name
                    for line_to_write in new_lines:
                        tmpfile.write(line_to_write + "\\n")
                
                # Use sudo to copy the temporary file to the actual config path
                cp_result = subprocess.run(["sudo", "cp", tmp_path, NTP_CONFIG_PATH], check=True, capture_output=True, text=True)
                
                # Restart timesyncd
                subprocess.run(["sudo", "systemctl", "restart", "systemd-timesyncd"], check=True, capture_output=True, text=True)
                flash("NTP server configuration updated and service restarted.", "success")

            except subprocess.CalledProcessError as e:
                # This could be from `sudo cp` or `sudo systemctl restart`
                error_message = e.stderr.decode().strip() if e.stderr else str(e)
                flash(f"Error during NTP configuration or service restart: {error_message}", "error")
                # If cp succeeded but restart failed, config is changed. If cp failed, it's not.
                # The "restore original content" logic might be complex here if cp failed.
                # For now, we assume if cp fails, original is intact. If restart fails, new config is there.
                # The previous logic of restoring original_content on restart failure is good, but needs sudo for write.
                # For simplicity here, if restart fails, we'll just report it. A more robust solution might try to sudo cp the original_content back.
            except IOError as e: # Error writing to temporary file
                flash(f"Error writing temporary NTP config: {e}", "error")
            except FileNotFoundError: # systemctl or cp not found
                flash("Error: Required system command (cp or systemctl) not found.", "error")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path) # Clean up temporary file
        except Exception as e: # Generic except for the outer try block
            flash(f"An unexpected error occurred during NTP server configuration: {e}", "error")
            print(f"Error in set_ntp_server_route: {e}") # Log for server-side debugging
    else: # This is the else for: 'if "ntp_server" in request.form:'
        flash("No NTP server provided.", "error")
    return redirect(url_for("index"))

@app.route("/sync_ntp", methods=["POST"])
def sync_ntp_route():
    try:
        # Enable NTP
        result_enable_ntp = subprocess.run(["sudo", "timedatectl", "set-ntp", "true"], check=True, capture_output=True, text=True) # capture_output implies stderr capture
        # Restart the service to force sync
        result_restart = subprocess.run(["sudo", "systemctl", "restart", "systemd-timesyncd"], check=True, capture_output=True, text=True) # capture_output implies stderr capture
        flash("NTP synchronization initiated with systemd-timesyncd.", "success")
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.decode().strip() if e.stderr else str(e)
        flash(f"Error during NTP sync: {error_output}", "error")
    except FileNotFoundError:
        flash("Error: timedatectl, systemctl or timesyncd command not found.", "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
