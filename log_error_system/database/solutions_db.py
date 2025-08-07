import json
import os
import hashlib

from ai_model.model import predict_solution  # AI model
from api_fallback.fallback_api import fetch_solution_from_api  # Optional external API

PREDICTED_CACHE_FILE = "database/ai_predictions.json"
if os.path.exists(PREDICTED_CACHE_FILE):
    with open(PREDICTED_CACHE_FILE, "r", encoding="utf-8") as f:
        ai_predicted_cache = json.load(f)
else:
    ai_predicted_cache = {}

def save_ai_prediction(message, category):
    ai_predicted_cache[message] = category
    with open(PREDICTED_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(ai_predicted_cache, f, indent=2, ensure_ascii=False)

CATEGORY_TO_FIX = {
    "network": "Check VPN, firewall, and DNS settings.",
    "database": "Check DB credentials and host reachability.",
    "timeout": "Increase timeout or investigate server delay.",
    "authentication": "Verify user credentials and session configs.",
    "file": "Ensure the file exists and has proper permissions."
}


solutions_dict = {
    "database connection failed": "Check your database connection settings and try again.",
    "unable to connect to database": "Make sure the database server is running and try again.",
    "timeout while loading user data": "Increase the timeout value and try again.",
    "timeout occurred while fetching data": "Increase the timeout value and try again.",
    "memory overload in module x": "Reduce the memory usage of module X and try again.",
    "cassette 2 empty": "Refill cassette 2 with appropriate denomination notes and verify the cassette is correctly seated.",
    "deposit slot jammed": "Check the deposit slot for any physical obstructions or misaligned envelopes and clear the jam.",
    "unable to connect to core banking server": "Verify network connection between the E-Agent and the bank's core server. Restart router if necessary.",
    "card reader failure": "Inspect and clean the card reader. If the problem persists, replace the card reader unit.",
    "pin pad malfunction": "Reboot the machine. If issue continues, inspect the PIN pad connector or replace the unit.",
    "printer paper empty": "Open the printer compartment and load a new roll of thermal paper.",
    "cash dispenser motor error": "Check for jammed notes in the dispenser. Perform a dispenser test cycle through diagnostics mode.",
    "network latency detected": "Monitor the connection stability. If ping times remain high, consider switching to a backup network route.",
    "transaction timeout": "Check the backend server response time. Restart application services if necessary.",
    "session expired unexpectedly": "Verify software timeout settings. Upgrade the firmware if an update is available.",
    "card jammed in reader": "Manually remove the card if safe to do so, then reset the machine. Log incident if removal fails.",
    "atm rebooted unexpectedly": "Check system logs for hardware or software faults. Perform a diagnostic check of hardware modules.",
    "power supply interruption": "Verify power source and UPS status. Restore power and allow system to reboot fully.",
    "camera malfunction": "Check the connection to the surveillance module. Replace camera if no feed is detected.",
    "security module tampered": "Log a security alert. Alert branch supervisor and disable the ATM until physical inspection is completed.",
    "door sensor triggered": "Check if ATM service door is properly closed. Re-secure door and reset the sensor alert.",
    "vault temperature too high": "Inspect the ATM environment cooling. Allow cooldown before resuming operations.",
    "card reader timeout": "Check reader module for response delay. Clean reader and restart the terminal.",
    "host unreachable": "Verify bank host server status and connectivity. Escalate to network team if issue persists.",
    "encryption key not found": "Reload the security keys via HSM or contact HQ to issue a new key injection command.",
    "cassette 1 low": "Refill Cassette 1 with appropriate denomination before it runs out.",
    "cassette 2 low": "Refill Cassette 2 with sufficient RM100 notes to avoid transaction disruption.",
    "printer paper low": "Open the printer compartment and load a new roll of thermal paper.",
    "high cpu usage detected": "Restart background services and monitor system performance. Upgrade if persistent.",
    "unusual transaction volume": "Alert branch supervisor. Monitor for potential fraud or misconfiguration.",
    "temperature nearing threshold": "Check air ventilation around the ATM. Reduce heat sources nearby.",
    "battery backup low": "Inspect or replace the UPS unit to ensure reliable power during outages.",
    "frequent pin entry failures": "Consider enabling temporary hold or increasing fraud alert sensitivity.",
    "external device response delay": "Check USB or serial cable connections. Reboot attached modules.",
    "surveillance camera signal weak": "Inspect camera wiring and lens. Clean and secure connections for better video feed.",
    "cash dispenser jammed": "Open the dispenser tray and remove any jammed notes. Perform dispenser test in diagnostic mode.",
    "cassette not recognized": "Ensure the cassette is properly seated. Reinsert or replace if not detected.",
    "receipt printer failure": "Check for paper jams. Restart the printer or replace it if issue persists.",
    "screen backlight failure": "Replace the ATM display unit or verify the power connection to the display.",
    "card reader misaligned": "Realign the card reader or reseat its internal connector.",
    "pin pad key stuck": "Inspect and clean the PIN pad. If hardware fault persists, replace the keypad unit.",
    "atm unable to sync with hq": "Check WAN link connectivity. Restart router or VPN device.",
    "host response delayed": "Check host system latency and verify if firewall or DNS is affecting requests.",
    "network disconnected": "Verify LAN cable and switch port. Test with ping or traceroute.",
    "ssl handshake failed": "Ensure the ATM system time is correct and SSL certificates are not expired.",
    "dns resolution failed": "Update DNS settings or switch to a backup DNS (e.g., 8.8.8.8).",
    "ftp transfer failed": "Check FTP server availability and credentials. Retry file sync.",
    "encryption module not initialized": "Initialize the HSM or crypto module and perform a secure key injection.",
    "camera feed lost": "Verify physical connection to DVR or IP feed. Reboot the camera if required.",
    "tamper switch triggered": "Verify ATM case has not been opened. Reset tamper state after inspection.",
    "safe door left open": "Ensure vault door is securely closed and locked. Reset the door sensor.",
    "security alert - intrusion detected": "Disable ATM temporarily. Inform branch security and perform physical check.",
    "bootloader failed": "Reflash the ATM bootloader using vendor software. Check for corrupted firmware.",
    "application not responding": "Restart ATM services. If the issue persists, reinstall core ATM software.",
    "update failed - rollback initiated": "Check software version compatibility. Clear cache and retry update.",
    "config file missing": "Restore default config file from backup. Avoid hard shutdowns during config edits.",
    "service daemon not running": "Start the daemon manually or set it to auto-start on boot.",
    "ups battery critically low": "Replace UPS battery or verify UPS is charging correctly.",
    "power surge detected": "Inspect power regulation module. Install surge protection if absent.",
    "fan malfunction detected": "Clean internal fans. Replace any fan not spinning during diagnostics.",
    "internal temperature exceeded": "Shut down ATM temporarily. Improve ventilation or air conditioning.",
    "humidity sensor alert": "Check for water leak or excess humidity. Use dehumidifier if needed.",
    "no internet connection": "Check network connectivity and DNS settings. Reboot router or VPN device.",
    "dns resolution issue": "Update DNS settings or switch to a backup DNS (e.g., 8.8.8.8).",
    "ftp transfer issue": "Check FTP server availability and credentials. Retry file sync.",
    "looks like the active ej is not growing. no transactions, perhaps?": "Check if the ATM is idle or has not processed any transactions recently. Verify the network connectivity, transaction routing, and the status of ATM services. If the machine is live but inactive, this message is normal. If unexpected, check the transaction logs, EJ pointer, and restart the transaction service if needed.",
    "error occured while closing jms session:":"Check if the JMS session is not null and not already closed before calling session.close() inside a try-catch block.",
    "error occured while closing jms producer:":"Check if the JMS producer is not null and not already closed before calling producer.close() inside a try-catch block.",

}

dynamic_path = "database/solutions_dynamic.json"
if os.path.exists(dynamic_path):
        with open(dynamic_path, "r", encoding="utf-8", errors="ignore") as f:
         dynamic_solutions = json.load(f)
         solutions_dict.update(dynamic_solutions)
        
# --- Find solution logic ---
def find_solution(message):
    message = message.lower()
    for keyword in solutions_dict:
        if keyword in message:
            return solutions_dict[keyword]
    return None

# --- Utility to load/save editable solutions ---
def load_solutions():
    try:
        with open("database/solutions_dynamic.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_solutions(data):
    with open("database/solutions_dynamic.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)