import pyttsx3
import datetime

def init_engine():
    return pyttsx3.init()

def say_alert(engine, alert_msg):
    print("[ALERTE]", alert_msg)
    engine.say(alert_msg)
    engine.runAndWait()

def log_alert(alert_msg, log_file="alertes.log"):
    with open(log_file, "a") as f:
        f.write(f"{datetime.datetime.now()} - {alert_msg}\n")
