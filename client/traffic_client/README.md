# Traffic Client

Defensive traffic analysis client application.

## Project Structure

```
traffic_client/
  client_main.py          # Main entry point
  core/                   # Core business layer
    service_manager.py    # Windows/Linux service management
    engine.py             # Core control engine
    authorize.py          # Authorization module
  utils/                  # Utility layer
    system_tools.py       # Cross-platform system utilities
    crypto_tools.py       # AES-256/TLS encryption tools
    logger.py             # Global logging configuration
  config/                 # Configuration layer
    settings.py           # Config read/write and mapping
    config.json           # Runtime configuration
  data/                   # Runtime data (generated at runtime)
    traffic_buffer/       # Encrypted traffic buffer
    attack_log/           # Encrypted attack logs
    auth.dat              # Authorization info
    device_code.dat       # Device fingerprint
  log/                    # Log files
    client_run.log        # Auto-rotating run log
  script/                 # Deployment scripts
    install.bat / .sh     # One-click install
    uninstall.bat / .sh   # One-click uninstall
  requirements.txt        # Dependencies
```

## Quick Start

1. Install dependencies: `pip install -r requirements.txt`
2. Run: `python client_main.py`
