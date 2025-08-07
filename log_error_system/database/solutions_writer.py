import json
import os

DB_PATH = "database/solutions_dynamic.json"

def write_solution(message, solution, path=DB_PATH):
    """
    Add or update a solution for a given log message in the JSON database.
    """
    # Load current database
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    # Update or add
    data[message] = solution

    # Save back
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def delete_solution(message, path=DB_PATH):
    """
    Delete a solution from the JSON database by message.
    Returns True if deleted, False if not found.
    """
    if not os.path.exists(path):
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        data = {}

    if message in data:
        del data[message]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True

    return False
