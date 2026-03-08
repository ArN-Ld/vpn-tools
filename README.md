# VPN Tools Collection

A collection of Python-based tools for testing, optimizing, and managing VPN connections. This repository contains utilities designed to help users get the most out of their VPN services.

> **Note**: This is an enhanced fork of [valtumi/vpn-tools](https://github.com/valtumi/vpn-tools) with improvements including modular project structure, comprehensive testing, CI/CD integration, and enhanced automation capabilities.

## Available Tools

### Mullvad Speed Test (`mullvad_speed_test.py`)

A comprehensive tool for testing and comparing Mullvad VPN server performance. This tool helps you find the best performing Mullvad servers based on various metrics including download speed, upload speed, latency, and reliability.

Note: Mullvad removed OpenVPN from its relay fleet in January 2026. This tool now targets WireGuard relays only.

#### Features
- Interactive user interface with color-coded outputs
- Geographic-based server analysis and distance calculations
- Automatic connection calibration to optimize testing
- Tests multiple Mullvad VPN servers sequentially
- Measures:
  - Download and upload speeds
  - Latency and jitter
  - Packet loss
  - Connection time
- Performs MTR (My TraceRoute) tests
- Generates detailed reports with server performance metrics
- Provides comprehensive server rankings:
  - Top 5 servers by distance
  - Top 5 servers by connection time
  - Top 5 servers by download speed
  - Top 5 servers by upload speed
  - Top 5 servers by latency
  - Top 5 servers by reliability
  - Best overall servers (weighted scoring)
- Optimized server selection algorithm
- Enhanced visual feedback with multi-level color gradient progress bars
- Detailed breakdowns of selected servers by country
- Uses Mullvad WireGuard relays
- Detailed logging for troubleshooting
- Stores test results in SQLite database for historical analysis

## Prerequisites

### System Requirements

- **Python**: 3.9+ (tested with Python 3.9.6)
- **Mullvad VPN**: Client with CLI access ([download](https://mullvad.net/download))
- **System packages**:
  - `mtr` (My TraceRoute) - for network path analysis
  - `sudo` privileges - required for MTR execution

### Python Dependencies

- `speedtest-cli>=2.1.3` - Network speed testing
- `geopy>=2.4.1` - Geographical calculations and distance computation
- `colorama>=0.4.6` - Color-coded terminal output (optional but recommended)

## Installation

1. Install required system packages:
   ```bash
   # macOS
   brew install mtr

   # Debian/Ubuntu
   sudo apt-get install mtr

   # Fedora
   sudo dnf install mtr
   ```

2. Install Python dependencies:
   ```bash
   # Runtime dependencies
   pip install -r requirements.txt

   # Development dependencies (optional)
   pip install -r requirements-dev.txt
   ```

   Note: The script includes fallback handling if colorama is not installed, but the user experience will be enhanced with this package.

3. Install and configure Mullvad VPN client:
   - Download from [Mullvad's official website](https://mullvad.net/download)
   - Ensure the CLI tool is accessible in your system PATH

## Usage

Basic usage:
```bash
sudo python mullvad_speed_test.py
```

This will run in interactive mode, guiding you through the process.

Advanced usage with options:
```bash
sudo python mullvad_speed_test.py --location "Paris, France" --max-servers 20
```

## Command-line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--location` | Reference location (city only or "City, Country", case-insensitive) | "Beijing, Beijing, China" |
| `--max-servers` | Maximum number of servers to test | 15 |
| `--max-servers-hard-limit` | Hard limit on number of servers to test | 45 |
| `--max-distance` | Maximum distance (km) for server selection | No limit |
| `--default-lat` | Default latitude if geocoding fails | None |
| `--default-lon` | Default longitude if geocoding fails | None |
| `--min-download-speed` | Minimum download speed in Mbps for viable servers | 3.0 |
| `--connection-timeout` | Default connection timeout in seconds | 20.0 |
| `--min-viable-servers` | Minimum number of viable servers required | 8 |
| `--countdown-seconds` | Interactive countdown before tests start | 5 |
| `--no-open-results` | Disable end-of-run prompt to open results file | Disabled |
| `--interactive` | Enable interactive mode | Auto-detected |
| `--non-interactive` | Disable interactive mode | - |
| `--verbose` | Enable verbose logging | Disabled |
| `--db` | SQLite database file path | "runtime/mullvad_results.db" |

## Example Use Cases

### Find Best Servers Near Your Location
```bash
sudo python mullvad_speed_test.py --interactive
```

### Test Servers Near a Specific Location
```bash
sudo python mullvad_speed_test.py --location "Tokyo, Japan" --max-servers 15
```

### Testing Within a Specific Distance Range
```bash
sudo python mullvad_speed_test.py --location "Berlin, Germany" --max-distance 2000
```


### Testing with Custom Performance Criteria
```bash
sudo python mullvad_speed_test.py --min-download-speed 5.0 --min-viable-servers 10
```

### Non-interactive automation example
```bash
sudo python mullvad_speed_test.py --non-interactive --location "Paris, France" --default-lat 48.8566 --default-lon 2.3522 --no-open-results
```

## Development and CI

### Running Tests Locally

Run syntax checks and tests:
```bash
# Syntax validation
python -m py_compile src/vpn_tools/*.py src/vpn_tools/ui/*.py

# Run test suite
pytest -q

# Run with verbose output
pytest -v
```

### Code Quality

The project uses:
- **pytest** for testing
- **black** for code formatting
- **flake8** for linting
- **mypy** for type checking

Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

### Continuous Integration

GitHub Actions CI (`.github/workflows/ci.yml`) automatically runs on push and pull requests:
- Python syntax validation
- Full test suite execution
- Tested with Python 3.12 on Ubuntu

## Supporting Modules

### Mullvad Coordinates (`src/vpn_tools/mullvad_coordinates.py`)
A helper module that loads accurate geographical coordinates for Mullvad server locations from `src/vpn_tools/data/coordinates.json`. The data is cached in memory at import time for fast lookups. If the main JSON file is missing, the module falls back to `src/vpn_tools/data/coordinates.example.json` or an empty dataset. These coordinates are used by the speed test tool for precise distance calculations.

## Understanding Results

After running the tests, the script generates a detailed report in a log file with the following sections:

1. **Test Parameters**: Your location, test date, WireGuard protocol, etc.
2. **Individual Server Results**: Detailed performance metrics for each tested server
3. **Summary Section**: 
   - Top 5 servers by distance
   - Top 5 servers by connection time
   - Top 5 servers by download speed
   - Top 5 servers by upload speed
   - Top 5 servers by latency
   - Top 5 servers by reliability
   - Best overall servers (weighted scoring)
   - Average performance statistics

The script also provides a real-time summary in the terminal and offers to open the full report when testing completes.

## Testing Process

1. **Connection Calibration**: The script first calibrates by testing connection times to servers on different continents
2. **Initial Testing**: Tests the closest servers to your location
3. **Adaptive Search**: If enough viable servers aren't found, searches for servers on other continents with detailed country breakdowns
4. **Results Analysis**: Calculates comprehensive metrics and generates rankings
5. **Report Generation**: Creates detailed logs and summaries

A server is considered "viable" if it establishes a connection successfully and provides a download speed above the minimum threshold (3 Mbps by default).

## Troubleshooting

### Dependency Issues
If you encounter errors related to missing Python modules:
```bash
# Install all required and recommended modules in one command
pip install geopy speedtest-cli colorama
```

The script is designed to work even if optional modules like colorama are not installed, but with a reduced user experience.

### Geolocation Issues
If your location cannot be determined automatically:
- Use the interactive mode which offers manual coordinate input
- Specify coordinates directly: `--default-lat 48.8566 --default-lon 2.3522`

### Connection Problems
- Permission Denied for MTR: Run the script with sudo privileges
- Mullvad CLI Not Found: Ensure Mullvad is installed and its CLI is in your system PATH
- If the script fails to connect to many servers:
  - Check your internet connection
  - Verify Mullvad VPN is properly configured
  - Increase the distance limit: `--max-distance 5000`

## Logging

The tools generate detailed logs and data files in the `runtime/` directory:
- `runtime/mullvad_speed_test.log` - Detailed operation logs
- `runtime/mullvad_test_results_*.log` - Test results and summaries
- `runtime/mullvad_results.db` - SQLite database with structured storage of all test results
- `runtime/geocoords_cache.pkl` - Cached geocoding results

## Future Tools (Planned)
- VPN connection monitor and auto-reconnect utility
- Multi-VPN provider speed comparison tool
- VPN traffic analysis tool
- Split tunneling configuration helper

## Security Notes

- **Privilege requirements**: The tool requires sudo privileges for MTR tests
- **Data privacy**: No sensitive data (like API keys or credentials) is stored
- **Local storage**: All logs and results are stored locally in the `runtime/` directory
- **Vulnerability reporting**: See [SECURITY.md](SECURITY.md) for security policy and how to report issues

For complete security guidelines, please review our [Security Policy](SECURITY.md).

## Contributing

Contributions are welcome! If you have ideas for new VPN tools or improvements to existing ones, please feel free to:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

Before opening a pull request:
- Update `CHANGELOG.md` under `Unreleased`
- Run the checks listed in `MAINTENANCE.md`

## Project Maintenance

- Change history: [docs/CHANGELOG.md](docs/CHANGELOG.md)
- Maintenance process: [docs/MAINTENANCE.md](docs/MAINTENANCE.md)
- Technical audit and roadmap: [docs/PROJECT_AUDIT.md](docs/PROJECT_AUDIT.md)

## Credits

This project is derived from [vpn-tools](https://github.com/valtumi/vpn-tools) by [valtumi](https://github.com/valtumi) (Valera).

Original work Copyright © 2025 Valera

Enhancements and modifications in this fork:
- Modular project structure with `src/`, `docs/`, `tests/` organization
- Comprehensive test suite with pytest
- GitHub Actions CI/CD pipeline
- Enhanced non-interactive mode for automation
- Runtime artifacts organization
- Improved error handling and fallback mechanisms
- Extended documentation and maintenance workflows

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Original work Copyright © 2025 Valera
