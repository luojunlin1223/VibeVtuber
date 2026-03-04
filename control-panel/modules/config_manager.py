"""
Reads and writes PythonFaceTracker/config.json, PythonTextDriver/config.json,
and control-panel/panel_config.json.
"""

import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACKER_CONFIG_PATH = os.path.join(PROJECT_ROOT, "PythonFaceTracker", "config.json")
TEXT_DRIVER_CONFIG_PATH = os.path.join(PROJECT_ROOT, "PythonTextDriver", "config.json")
PANEL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "panel_config.json")

_PANEL_DEFAULTS = {
    "unity_app_path": "",
}


def read_tracker_config() -> dict:
    with open(TRACKER_CONFIG_PATH, "r") as f:
        return json.load(f)


def write_tracker_config(updates: dict) -> dict:
    config = read_tracker_config()
    # Deep merge one level
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            config[key].update(value)
        else:
            config[key] = value
    with open(TRACKER_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    return config


def read_text_driver_config() -> dict:
    with open(TEXT_DRIVER_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def write_text_driver_config(updates: dict) -> dict:
    config = read_text_driver_config()
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            config[key].update(value)
        else:
            config[key] = value
    with open(TEXT_DRIVER_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return config


def read_panel_config() -> dict:
    path = os.path.normpath(PANEL_CONFIG_PATH)
    if not os.path.exists(path):
        return dict(_PANEL_DEFAULTS)
    with open(path, "r") as f:
        data = json.load(f)
    return {**_PANEL_DEFAULTS, **data}


def write_panel_config(updates: dict) -> dict:
    config = read_panel_config()
    config.update(updates)
    path = os.path.normpath(PANEL_CONFIG_PATH)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    return config
