"""
settings.py - Configuration Management
Handles reading/writing config.json and in-memory mapping.
"""

import json
import os


class Settings:
    """Manages runtime configuration loaded from config.json."""

    DEFAULT_CONFIG = {
        "server": {
            "host": "",
            "port": 443,
            "protocol": "https"
        },
        "client": {
            "id": "",
            "name": "",
            "heartbeat_interval": 60
        },
        "logging": {
            "level": "INFO",
            "max_size_mb": 5,
            "backup_count": 5
        },
        "buffer": {
            "max_size_mb": 100,
            "flush_interval": 30
        }
    }

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "config.json"
            )
        self.config_path = config_path
        self._config = {}
        self.load()

    def load(self):
        """Load configuration from config.json."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        else:
            self._config = self.DEFAULT_CONFIG.copy()
            self.save()

    def save(self):
        """Save current configuration to config.json."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4, ensure_ascii=False)

    def get(self, key: str, default=None):
        """Get a config value by dot-separated key (e.g. 'server.host')."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value):
        """Set a config value by dot-separated key."""
        keys = key.split(".")
        cfg = self._config
        for k in keys[:-1]:
            cfg = cfg.setdefault(k, {})
        cfg[keys[-1]] = value
