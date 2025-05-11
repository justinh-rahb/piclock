#!/bin/bash

# Start clock in background
/usr/bin/python3 /opt/piclock/main.py &

# Start web control (Flask app)
exec /usr/bin/python3 /opt/piclock/web_control.py
