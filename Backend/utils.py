import json
from datetime import datetime

def safe_json_loads(text, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default

def safe_json_dumps(data, indent=2):
    try:
        return json.dumps(data, indent=indent)
    except (TypeError, ValueError):
        return json.dumps(str(data), indent=indent)

def format_datetime(dt, fmt="%Y-%m-%d %H:%M:%S"):
    if not isinstance(dt, datetime):
        return str(dt)
    return dt.strftime(fmt)

def log_info(message: str):
    print(f"INFO {format_datetime(datetime.now())} - {message}")

def log_error(message: str):
    print(f"ERROR {format_datetime(datetime.now())} - {message}")

def extract_text_from_docs(docs: list):
    return " ".join(doc.get("text", "") for doc in docs if doc.get("text"))

def extract_titles_from_docs(docs: list):
    return [doc.get("title") for doc in docs if doc.get("title")]

def validate_mode(mode: str):
    valid_modes = ["competitor", "news", "blended"]
    if mode not in valid_modes:
        raise ValueError(f"Invalid mode {mode}. Must be one of {valid_modes}.")
    return mode
