import re

def parse_log_line(line):
    line = line.strip()

    # Pattern 1: Format like → 2025-06-08 02:00:15,015 [ERROR ] (Module) - Message
    pattern1 = r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?)\s*\[\s*(\w+)\s*\]\s*\((.*?)\)\s*-\s*(.*)"
    match1 = re.match(pattern1, line)

    if match1:
        timestamp, level, module, message = match1.groups()
        return {
            "timestamp": timestamp.strip(),
            "level": level.upper().strip(),
            "module": module.strip(),
            "message": message.strip()
        }

    # Pattern 2: Fallback → [timestamp] LEVEL: message
    pattern2 = r"^\[(.*?)\]\s+(\w+):\s+(.*)"
    match2 = re.match(pattern2, line)

    if match2:
        timestamp, level, message = match2.groups()
        return {
            "timestamp": timestamp.strip(),
            "level": level.upper().strip(),
            "module": None,
            "message": message.strip()
        }
    # No match
    return None

def is_error_log(log_entry):
    return log_entry and log_entry["level"] in {"ERROR", "DEBUG", "WARN"}

def is_warning_log(log_entry):
    return log_entry and log_entry["level"] in {"WARN", "WARNING"}
