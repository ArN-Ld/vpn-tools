#!/usr/bin/env python3
"""Mullvad VPN Server Performance Tester - Optimized Version"""
import subprocess, json, re, time, os, pickle, sqlite3, statistics, logging, sys, random, functools, shutil
from contextlib import contextmanager
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import argparse
from .ui.display_manager import (
    DisplayManager,
    get_symbol,
    get_terminal_width,
    Fore,
    Style,
    colorize,
    format_server_info,
    format_mtr_results,
    format_speedtest_results,
)

try:
    from .mullvad_coordinates import get_coordinates, resolve_location_input
except ImportError:
    get_coordinates = None
    resolve_location_input = None

# Constants
DEFAULT_MAX_SERVERS, MAX_SERVERS_HARD_LIMIT = 15, 45
RUNTIME_DIR = Path(os.environ.get("VPN_TOOLS_RUNTIME_DIR", "runtime"))
DEFAULT_LOCATION = "Beijing, Beijing, China"
COORDS_CACHE_FILE = RUNTIME_DIR / "geocoords_cache.pkl"
DEFAULT_DB_FILE = RUNTIME_DIR / "mullvad_results.db"
BEIJING_COORDS = (39.9057136, 116.3912972)
MIN_DOWNLOAD_SPEED, DEFAULT_CONNECTION_TIME = 3.0, 20.0
MAX_SPEEDTEST_TIME, MIN_SPEEDTEST_TIME, MIN_VIABLE_SERVERS = 70.0, 15.0, 8
MAX_SPEEDTEST_TIME_DISTANT = 150.0  # for servers > 3000 km (high-latency VPN tunnels)
DISTANCE_THRESHOLD_DISTANT = 3000   # km — beyond this, latency makes 70s too short

# Continent mapping for server selection
CONTINENT_MAPPING = {
    'North America': ['us', 'ca', 'mx'],
    'South America': ['br', 'ar', 'cl', 'co', 'pe'],
    'Europe': ['gb', 'uk', 'de', 'fr', 'it', 'es', 'nl', 'se', 'no', 'dk', 'fi', 'ch', 'at', 'be',
               'ie', 'pt', 'pl', 'cz', 'gr', 'ro', 'hu', 'si', 'sk', 'al', 'hr', 'rs', 'ee', 'bg',
               'cy', 'tr', 'ua', 'lv', 'lt', 'lu', 'is', 'md', 'ba', 'me', 'mk', 'mt'],
    'Asia': ['jp', 'kr', 'sg', 'hk', 'in', 'my', 'th', 'vn', 'id', 'ph', 'tw', 'cn', 'il', 'ae',
             'qa', 'sa', 'pk', 'bd', 'lk', 'kh', 'mm', 'la', 'np', 'uz', 'kz', 'ge', 'am', 'az'],
    'Oceania': ['au', 'nz'],
    'Africa': ['za', 'eg', 'ng', 'ke', 'ma']
}

COUNTRY_TO_CONTINENT = {code: continent for continent, codes in CONTINENT_MAPPING.items() for code in codes}

# Keywords (country names, city names, country codes) mapped to continents
KEYWORD_TO_CONTINENT = {
    **COUNTRY_TO_CONTINENT,
    # Country names
    'china': 'Asia', 'japan': 'Asia', 'korea': 'Asia', 'india': 'Asia',
    'singapore': 'Asia', 'malaysia': 'Asia', 'thailand': 'Asia',
    'vietnam': 'Asia', 'indonesia': 'Asia', 'philippines': 'Asia', 'taiwan': 'Asia',
    'israel': 'Asia',
    'france': 'Europe', 'germany': 'Europe', 'italy': 'Europe', 'spain': 'Europe',
    'netherlands': 'Europe', 'sweden': 'Europe', 'norway': 'Europe',
    'denmark': 'Europe', 'finland': 'Europe', 'switzerland': 'Europe',
    'austria': 'Europe', 'belgium': 'Europe', 'ireland': 'Europe',
    'portugal': 'Europe', 'poland': 'Europe', 'czech': 'Europe',
    'romania': 'Europe', 'hungary': 'Europe', 'greece': 'Europe',
    'uk': 'Europe', 'kingdom': 'Europe', 'britain': 'Europe',
    'bulgaria': 'Europe', 'albania': 'Europe', 'croatia': 'Europe',
    'serbia': 'Europe', 'slovenia': 'Europe', 'slovakia': 'Europe',
    'estonia': 'Europe', 'cyprus': 'Europe', 'turkey': 'Europe',
    'ukraine': 'Europe',
    'usa': 'North America', 'states': 'North America',
    'canada': 'North America', 'mexico': 'North America',
    'brazil': 'South America', 'argentina': 'South America',
    'chile': 'South America', 'colombia': 'South America',
    'peru': 'South America',
    'australia': 'Oceania', 'zealand': 'Oceania',
    'africa': 'Africa', 'egypt': 'Africa', 'nigeria': 'Africa',
    'kenya': 'Africa', 'morocco': 'Africa',
    # Major city names
    'tokyo': 'Asia', 'osaka': 'Asia', 'seoul': 'Asia', 'beijing': 'Asia',
    'shanghai': 'Asia', 'hong': 'Asia', 'mumbai': 'Asia', 'delhi': 'Asia',
    'bangkok': 'Asia', 'taipei': 'Asia', 'manila': 'Asia', 'jakarta': 'Asia',
    'lijiang': 'Asia', 'kuala': 'Asia', 'lumpur': 'Asia', 'aviv': 'Asia',
    'paris': 'Europe', 'berlin': 'Europe', 'london': 'Europe', 'madrid': 'Europe',
    'rome': 'Europe', 'amsterdam': 'Europe', 'stockholm': 'Europe',
    'oslo': 'Europe', 'copenhagen': 'Europe', 'helsinki': 'Europe',
    'zurich': 'Europe', 'vienna': 'Europe', 'brussels': 'Europe',
    'lisbon': 'Europe', 'warsaw': 'Europe', 'prague': 'Europe',
    'bucharest': 'Europe', 'budapest': 'Europe', 'athens': 'Europe',
    'dublin': 'Europe', 'milan': 'Europe', 'barcelona': 'Europe',
    'manchester': 'Europe', 'frankfurt': 'Europe', 'munich': 'Europe',
    'glasgow': 'Europe', 'bordeaux': 'Europe', 'marseille': 'Europe',
    'dusseldorf': 'Europe', 'gothenburg': 'Europe', 'stavanger': 'Europe',
    'valencia': 'Europe', 'palermo': 'Europe', 'sofia': 'Europe',
    'tirana': 'Europe', 'zagreb': 'Europe', 'belgrade': 'Europe',
    'ljubljana': 'Europe', 'bratislava': 'Europe', 'tallinn': 'Europe',
    'nicosia': 'Europe', 'istanbul': 'Europe', 'kyiv': 'Europe',
    'york': 'North America', 'angeles': 'North America',
    'chicago': 'North America', 'toronto': 'North America',
    'montreal': 'North America', 'vancouver': 'North America',
    'francisco': 'North America', 'seattle': 'North America',
    'miami': 'North America', 'dallas': 'North America',
    'atlanta': 'North America', 'denver': 'North America',
    'washington': 'North America', 'boston': 'North America',
    'phoenix': 'North America', 'houston': 'North America',
    'detroit': 'North America', 'raleigh': 'North America',
    'ashburn': 'North America', 'secaucus': 'North America',
    'calgary': 'North America', 'queretaro': 'North America',
    'paulo': 'South America', 'aires': 'South America',
    'santiago': 'South America', 'bogota': 'South America',
    'lima': 'South America', 'fortaleza': 'South America',
    'sydney': 'Oceania', 'melbourne': 'Oceania', 'auckland': 'Oceania',
    'perth': 'Oceania', 'brisbane': 'Oceania', 'adelaide': 'Oceania',
    'cairo': 'Africa', 'johannesburg': 'Africa', 'lagos': 'Africa',
    'nairobi': 'Africa', 'casablanca': 'Africa', 'cape': 'Africa',
}

# Setup logging (will be configured properly in main after runtime dir is created)
logger = logging.getLogger(__name__)

# Dataclasses for structured data
@dataclass
class ServerInfo:
    country: str; city: str; hostname: str; protocol: str
    provider: str; ownership: str; ip: str; ipv6: str
    connection_time: float = 0; latitude: float = 0.0; longitude: float = 0.0; distance_km: float = 0.0

@dataclass
class SpeedTestResult:
    download_speed: float; upload_speed: float; ping: float; jitter: float; packet_loss: float

@dataclass
class MtrResult:
    avg_latency: float; packet_loss: float; hops: int


def display_parameters_summary(args, ui, countdown_seconds=5):
    """Display a summary of all parameters with a countdown"""
    ui.header("SUMMARY OF MULLVAD VPN TEST PARAMETERS")
    params = [
        f"Location: {args.location}",
        "Protocol: WireGuard",
        f"Max number of servers: {args.max_servers}",
        f"Min. download speed: {args.min_download_speed} Mbps",
        f"Connection timeout: {args.connection_timeout} seconds",
        f"Minimum viable servers: {args.min_viable_servers}",
        f"Maximum distance: {args.max_distance if args.max_distance else 'No limit'} km",
        f"Database file: {args.db}",
        f"Interactive mode: {'Yes' if args.interactive else 'No'}"
    ]
    for param in params:
        ui.info(param)

    print(f"\nTests will start in {countdown_seconds} seconds. Press Ctrl+C to cancel...")
    try:
        for i in range(countdown_seconds, 0, -1):
            sys_msg = f"Starting in {i} seconds..."
            print(f"\r{colorize(sys_msg, Fore.YELLOW)}", end="")
            sys.stdout.flush()
            time.sleep(1)
        print("\rStarting tests... ")
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(0)

def run_command(cmd, timeout=None, check=False, capture_output=False):
    """Run a command with unified error handling"""
    try:
        return subprocess.run(cmd, text=True, timeout=timeout, check=check, capture_output=capture_output or check)
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with code {e.returncode}: {' '.join(cmd)}")
        logger.error(f"STDERR: {e.stderr}")
        return e
    except Exception as e:
        logger.error(f"Error running command {' '.join(cmd)}: {e}")
        return None

@functools.lru_cache(maxsize=1)
def load_geo_modules():
    """Lazily load geopy modules only when needed"""
    try:
        from geopy.distance import geodesic
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut
        return geodesic, Nominatim, GeocoderTimedOut
    except ImportError:
        logger.error("geopy modules not found. Please install with: pip install geopy")
        print("\nERROR: Required geopy modules not found.", file=sys.stderr)
        print("Please install with: pip install geopy\n", file=sys.stderr)
        sys.exit(1)

def input_location(ui):
    """Interactive function to input location"""
    ui.header("LOCATION FOR MULLVAD VPN TESTS")
    ui.info("Enter your origin city (or 'City, Country').")
    print("Examples: 'Paris' or 'Paris, France'")

    while True:
        location = input("\nYour location: ").strip()
        if location:
            return location
        else:
            ui.info(f"Using default location: {DEFAULT_LOCATION}")
            return DEFAULT_LOCATION

def input_coordinates(ui):
    """Interactive function to input coordinates manually"""
    ui.header("MANUAL COORDINATES INPUT")
    ui.warning("Unable to determine coordinates automatically.")
    ui.info("Please enter the coordinates manually.\n")

    while True:
        try:
            lat = float(input("Latitude (e.g. 48.8566 for Paris): ").strip())
            lon = float(input("Longitude (e.g. 2.3522 for Paris): ").strip())

            if -90 <= lat <= 90 and -180 <= lon <= 180:
                ui.success(f"Coordinates accepted: ({lat}, {lon})")
                return (lat, lon)
            else:
                ui.warning("Coordinates out of range. Latitude: -90 to 90, Longitude: -180 to 180")
        except ValueError:
            ui.error("Please enter valid numbers.")

def print_welcome(ui):
    """Print a welcome message with ASCII art"""
    title = r"""
 __  __         _ _               _  __     _______  _   _   _____         _
|  \/  |       | | |             | | \ \   /  /  _ \| \ | | |_   _|       | |
| \  / |_   _ _| | |_   ____ _  _| |  \ \_/  /| |_) |  \| |   | | ___  ___| |_ ___ _ __
| |\/| | | | | | | \ \ / / _` |/ _` |  \    / |  __/| . ` |   | |/ _ \/ __| __/ _ \ '__|
| |  | | |_| | | | |\ V / (_| | (_| |   \  /  | |   | |\  |   | |  __/\__ \ ||  __/ |
|_|  |_|\__,_|_|_|_| \_/ \__,_|\__,_|    \/   |_|   |_| \_|   |_|\___||___/\__\___|_|
    """
    print(colorize(title, Fore.CYAN + Style.BRIGHT))
    print(colorize("Mullvad VPN Server Performance Tester", Fore.GREEN + Style.BRIGHT))
    print(colorize("Optimized Version with Enhanced Features", Fore.YELLOW))
    print("")

# Main Mullvad Tester Class
class MullvadTester:
    def __init__(self, target_host="1.1.1.1", reference_location=DEFAULT_LOCATION,
                 default_lat=None, default_lon=None, verbose=False,
                 db_file=DEFAULT_DB_FILE, interactive=False,
                 max_servers_hard_limit=MAX_SERVERS_HARD_LIMIT,
                 min_download_speed=MIN_DOWNLOAD_SPEED,
                 connection_timeout=DEFAULT_CONNECTION_TIME,
                 min_viable_servers=MIN_VIABLE_SERVERS,
                 open_results_prompt=True,
                 machine_readable=False):
        
        # Set up logging and instance variables
        logger.setLevel(logging.INFO if verbose else logging.WARNING)
        self.machine_readable = machine_readable
        self.target_host = target_host
        self.max_servers_hard_limit = max_servers_hard_limit
        self.min_download_speed = min_download_speed
        self.default_connection_timeout = connection_timeout
        self.min_viable_servers = min_viable_servers
        self.open_results_prompt = open_results_prompt
        self.db_file = db_file
        self.ui = DisplayManager(interactive)
        
        # Get reference location
        if reference_location == DEFAULT_LOCATION and self.ui.interactive:
            reference_location = input_location(self.ui)
        
        self.reference_location = reference_location
        self.default_coords = (default_lat, default_lon) if default_lat is not None and default_lon is not None else None
        
        # Initialize tester
        self.coords_cache = self._load_coords_cache()
        self._init_database()
        self.reference_coords = self._get_location_coordinates()
        
        # Get Mullvad servers
        self.ui.header("RETRIEVING MULLVAD SERVERS")
        self.servers = self._get_servers()
        self._server_by_hostname = {s.hostname: s for s in self.servers}
        
        # Initialize results and counters
        self.results = {}
        self.connection_timeout = self.default_connection_timeout
        self.successful_servers = 0
        
        if not self.servers:
            self.ui.error("No Mullvad servers found. Please check that Mullvad is installed and accessible.")
            logger.error("No Mullvad servers found")
            sys.exit(1)
            
        logger.info(f"Found {len(self.servers)} Mullvad servers")
        logger.info("Reference location resolved successfully")
        
        self.ui.success(f"Mullvad servers found: {len(self.servers)}")
        self.ui.info(f"Reference location: {reference_location}")
        self.ui.info(f"Coordinates: ({self.reference_coords[0]:.4f}, {self.reference_coords[1]:.4f})")

    def log_and_info(self, message):
        """Log an info message and display it to the user."""
        logger.info(message)
        self.ui.info(message)

    def log_and_warning(self, message):
        """Log a warning message and display it to the user."""
        logger.warning(message)
        self.ui.warning(message)

    def log_and_error(self, message):
        """Log an error message and display it to the user."""
        logger.error(message)
        self.ui.error(message)

    def _load_coords_cache(self):
        """Load coordinates cache from disk if it exists"""
        if os.path.exists(COORDS_CACHE_FILE):
            try:
                with open(COORDS_CACHE_FILE, 'rb') as f:
                    cache = pickle.load(f)
                    self.log_and_info(f"Loaded {len(cache)} coordinates from cache")
                    return cache
            except Exception as e:
                self.log_and_warning(f"Could not load coordinates cache: {e}")
        return {}

    def _save_coords_cache(self):
        """Save coordinates cache to disk"""
        try:
            with open(COORDS_CACHE_FILE, 'wb') as f:
                pickle.dump(self.coords_cache, f)
                logger.info(f"Saved {len(self.coords_cache)} location coordinates to cache")
        except Exception as e:
            logger.warning(f"Could not save coordinates cache: {e}")

    @contextmanager
    def _with_db_cursor(self):
        """Yield a database cursor with automatic commit handling."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                yield cursor
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise

    def _init_database(self):
        """Initialize SQLite database for storing test results"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                c = conn.cursor()

                # Create tables with a single SQL operation for efficiency
                c.executescript('''
                    CREATE TABLE IF NOT EXISTS test_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT,
                        reference_location TEXT, reference_lat REAL, reference_lon REAL, protocol TEXT);

                    CREATE TABLE IF NOT EXISTS server_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER,
                        hostname TEXT, country TEXT, city TEXT, distance_km REAL,
                        connection_time REAL, download_speed REAL, upload_speed REAL,
                        ping REAL, jitter REAL, speedtest_packet_loss REAL,
                        mtr_latency REAL, mtr_packet_loss REAL, mtr_hops INTEGER,
                        viable INTEGER DEFAULT 0,
                        FOREIGN KEY (session_id) REFERENCES test_sessions (id));
                ''')

                # Check for viable column
                c.execute("PRAGMA table_info(server_results)")
                columns = [column[1] for column in c.fetchall()]
                if 'viable' not in columns:
                    self.log_and_info("Adding 'viable' column to server_results table")
                    c.execute("ALTER TABLE server_results ADD COLUMN viable INTEGER DEFAULT 0")

                conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            self.log_and_error(f"Error initializing database: {e}")

    def _get_location_coordinates(self):
        """Get coordinates for reference location"""
        location = self.reference_location.strip()

        # Check cache first (case-insensitive).
        for cached_location, coords in self.coords_cache.items():
            if cached_location.lower() == location.lower():
                self.reference_location = cached_location
                self.log_and_info(f"Using cached coordinates for {cached_location}: {coords}")
                return coords

        # Try to resolve against known Mullvad city coordinates before geocoding.
        if resolve_location_input is not None:
            canonical_location, coords, matches = resolve_location_input(location)
            if coords is not None and canonical_location is not None:
                self.reference_location = canonical_location
                self.coords_cache[canonical_location] = coords
                self._save_coords_cache()

                if len(matches) > 1:
                    self.log_and_warning(
                        f"Multiple city matches for '{location}', using '{canonical_location}'."
                    )

                self.ui.success(f"Using Mullvad city coordinates for: {canonical_location}")
                self.ui.success(f"Coordinates: ({coords[0]:.4f}, {coords[1]:.4f})")
                return coords

        # Load geopy modules
        _, Nominatim, _ = load_geo_modules()

        geolocator = Nominatim(user_agent="mullvad_speed_test")
        self.ui.info(f"Searching for coordinates for {location}...")

        try:
            location_data = geolocator.geocode(location, exactly_one=True)
        except Exception as e:
            logger.warning(f"Error getting coordinates for {location}: {e}")
            self.ui.error(f"Error searching for coordinates: {e}")
            return self._handle_geocode_failure(location)

        if location_data:
            coords = (location_data.latitude, location_data.longitude)
            self.ui.success(f"Location found: {location_data.address}")
            self.ui.success(f"Coordinates: {coords}")
            logger.info("Geocoding completed successfully")
            self.coords_cache[location] = coords
            self._save_coords_cache()
            return coords

        self.ui.error(f"Unable to find coordinates for: {location}")
        return self._handle_geocode_failure(location)

    def _handle_geocode_failure(self, location):
        """Fallback handling when geocoding fails"""
        if self.default_coords is not None:
            self.log_and_warning(
                f"Using default coordinates for {location}: {self.default_coords}"
            )
            self.coords_cache[location] = self.default_coords
            self._save_coords_cache()
            return self.default_coords

        if not self.ui.interactive:
            raise ValueError(
                "Unable to geocode location in non-interactive mode. "
                "Provide --default-lat and --default-lon."
            )

        return self._manual_coordinates_flow(location)

    def _manual_coordinates_flow(self, location):
        """Interactive flow for manual location or coordinate input"""
        self.ui.header("LOCATION OPTIONS")
        print("1. Try another location")
        print("2. Enter coordinates manually")

        choice = input("\nYour choice (1/2): ").strip()
        if choice == "1":
            new_location = input_location(self.ui)
            self.reference_location = new_location
            return self._get_location_coordinates()
        coords = input_coordinates(self.ui)
        self.coords_cache[location] = coords
        self._save_coords_cache()
        return coords

    def _calculate_distance(self, server_coords):
        """Calculate distance between server and reference location"""
        if server_coords == (0.0, 0.0) or self.reference_coords == (0.0, 0.0): return float('inf')
        geodesic, _, _ = load_geo_modules()
        return geodesic(self.reference_coords, server_coords).kilometers

    def _get_servers(self):
        """Parse mullvad relay list output to get server information"""
        servers = []
        try:
            self.log_and_info("Retrieving Mullvad server list...")
                
            output = subprocess.check_output(["mullvad", "relay", "list"], text=True)
            
            current_country, current_city = "", ""
            current_coords = (0.0, 0.0)

            # Regular expressions (compiled for efficiency)
            country_pattern = re.compile(r'^([A-Za-z\s]+)\s+\(([a-z]{2})\)$')
            city_pattern = re.compile(r'^\s*([A-Za-z\s,]+)\s+\([a-z]+\)\s+@\s+[-\d.]+°[NS],\s+[-\d.]+°[EW]$')
            server_pattern = re.compile(r'^\s*([a-z]{2}-[a-z]+-(?:wg|ovpn)-\d+)\s+\(([^,]+)(?:,\s*([^)]+))?\)\s+-\s+([^,]+)(?:,\s+hosted by ([^()]+))?\s+\(([^)]+)\)$')

            lines = output.strip().split('\n')

            def process_lines():
                nonlocal current_country, current_city, current_coords
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Parse country, city, and server in a single pass with if/elif chain
                    if country_match := country_pattern.match(line):
                        current_country = country_match.group(1)
                    elif city_match := city_pattern.match(line):
                        current_city = city_match.group(1)
                        if get_coordinates:
                            current_coords = get_coordinates(current_city, current_country)
                        else:
                            current_coords = (0.0, 0.0)
                    elif server_match := server_pattern.match(line):
                        hostname, ip = server_match.group(1), server_match.group(2)
                        ipv6 = server_match.group(3) or ""
                        protocol, provider = server_match.group(4), server_match.group(5) or ""
                        ownership = server_match.group(6)
                        distance = self._calculate_distance(current_coords)
                        servers.append(ServerInfo(
                            country=current_country, city=current_city, hostname=hostname,
                            protocol=protocol, provider=provider, ownership=ownership,
                            ip=ip, ipv6=ipv6, latitude=current_coords[0],
                            longitude=current_coords[1], distance_km=distance
                        ))

            process_lines()

            # Sort servers by distance - more efficient than sorting during processing
            return sorted(servers, key=lambda x: x.distance_km)
            
        except subprocess.CalledProcessError as e:
            self.log_and_error(f"Error retrieving server list: {e}")
            self.ui.warning("Please verify that Mullvad VPN is correctly installed and configured.")
            sys.exit(1)
        except Exception as e:
            self.log_and_error(f"Unexpected error retrieving server list: {e}")
            sys.exit(1)

    def _get_location_continent(self, location):
        """Determine which continent a location is in"""
        location_lower = location.lower().replace(',', ' ').replace('.', ' ').replace('-', ' ')

        for token in location_lower.split():
            if not token:
                continue
            continent = KEYWORD_TO_CONTINENT.get(token)
            if continent:
                return continent

        # Fallback: try matching the country part (last segment after comma)
        parts = location.split(',')
        if len(parts) >= 2:
            country_part = parts[-1].strip().lower()
            for token in country_part.split():
                continent = KEYWORD_TO_CONTINENT.get(token)
                if continent:
                    return continent

        logger.warning(f"Could not determine continent for {location}, defaulting to Europe")
        return "Europe"
        
    def run_connection_calibration(self):
        """Run connection tests on servers from different continents to calibrate timeout"""
        self.ui.header("CONNECTION CALIBRATION")
        self.ui.info("Selecting servers from each continent to determine average connection time...")
        
        # Group servers by continent
        available_continents = defaultdict(list)
        for server in self.servers:
            country_code = server.hostname.split('-')[0]
            continent = COUNTRY_TO_CONTINENT.get(country_code)
            if continent:
                available_continents[continent].append(server)
        
        # Determine user's continent
        self.user_continent = self._get_location_continent(self.reference_location)
        self.ui.info(f"Your location appears to be in: {self.user_continent}")
        self._emit_json_status("calibration", "Calibrating connections",
                              continent=self.user_continent,
                              continents=list(available_continents.keys()))
        
        # Select test servers - one from each continent
        test_servers = [random.choice(servers) for continent, servers in available_continents.items() if servers]
        
        self.ui.success(f"Servers selected for calibration: {len(test_servers)}")
        for server in test_servers:
            self.ui.info(f"  • {server.hostname} ({server.city}, {server.country})")
        self.ui.info(f"Testing {len(test_servers)} servers for connection calibration")
        
        # Test connection times
        self.connection_timeout = self.default_connection_timeout
        conn_times = []
        
        for server in test_servers:
            self.ui.info(f"Testing {server.hostname}...")
            cal_country_code = server.hostname.split('-')[0]
            cal_continent = COUNTRY_TO_CONTINENT.get(cal_country_code, 'Unknown')
            self._emit_json_status("calibration_test", f"Calibrating: {server.hostname}",
                                  hostname=server.hostname, city=server.city, country=server.country,
                                  continent=cal_continent)
            
            if self.connect_to_server(server):
                conn_times.append(server.connection_time)
                try: subprocess.run(["mullvad", "disconnect"], check=True, capture_output=True)
                except Exception: pass
        
        # Calculate and set timeout based on results
        if conn_times:
            avg_conn_time = sum(conn_times) / len(conn_times)
            self.connection_timeout = max(min(avg_conn_time * 1.5, self.default_connection_timeout), 10.0)
            
            self.ui.success(f"Average connection time: {avg_conn_time:.2f}s")
            self.ui.success(f"Connection timeout adjusted to: {self.connection_timeout:.2f}s")
            
            logger.info(f"Calibrated connection timeout to {self.connection_timeout:.2f}s based on average {avg_conn_time:.2f}s")
            return avg_conn_time
        else:
            self.connection_timeout = self.default_connection_timeout

            self.log_and_warning("No servers responded during calibration, using default timeout")
            self.ui.info(f"Connection timeout: {self.connection_timeout:.2f}s")
            return None

    def _select_servers(self, servers_list, max_per_country=5, max_total_servers=None, 
                      exclude_continent=None, tested_servers=None):
        """
        Unified server selection function that can be used for both initial and additional selection
        with parameters controlling behavior for each case.
        """
        if max_total_servers is None: max_total_servers = len(servers_list)
        if tested_servers is None: tested_servers = []
        
        # Filter by continent if needed
        if exclude_continent:
            filtered_servers = []
            for server in servers_list:
                country_code = server.hostname.split('-')[0]
                if exclude_continent and COUNTRY_TO_CONTINENT.get(country_code) == exclude_continent:
                    continue
                filtered_servers.append(server)
            servers_list = filtered_servers
        
        # If no servers after filtering, return empty list
        if not servers_list: return []
        
        # Group servers by country and city
        country_city_servers = defaultdict(lambda: defaultdict(list))
        for server in servers_list:
            country_code = server.hostname.split('-')[0]
            country_city_servers[country_code][server.city].append(server)

        self.ui.info(f"Selecting up to {max_total_servers} servers (max {max_per_country} per country)")
        
        # Sort countries by distance
        countries_by_distance = []
        for country_code, cities in country_city_servers.items():
            min_distance = min(
                min(server.distance_km for server in servers)
                for servers in cities.values()
            )
            countries_by_distance.append((country_code, min_distance))
        countries_by_distance.sort(key=lambda x: x[1])
        
        selected_servers = []
        countries_processed = 0
        selected_countries = {}  # Track selected servers by country
        
        # Select servers from each country
        for country_code, _ in countries_by_distance:
            if len(selected_servers) >= max_total_servers: break
                
            cities = country_city_servers[country_code]
            country_servers = []
            
            # Randomize city order
            city_names = list(cities.keys())
            random.shuffle(city_names)
            
            # Select one server from each city
            for city in city_names:
                if len(country_servers) < max_per_country:
                    server = random.choice(cities[city])
                    country_servers.append(server)
                    if len(selected_servers) + len(country_servers) >= max_total_servers: break
            
            # Fill any remaining slots for this country
            if len(country_servers) < max_per_country:
                remaining = max_per_country - len(country_servers)
                remaining_servers = [
                    s for city_servers in cities.values() for s in city_servers
                    if s not in country_servers
                ]
                random.shuffle(remaining_servers)
                country_servers.extend(remaining_servers[:remaining])
                
            # Track selected servers by country
            if country_servers:
                selected_countries[country_code] = len(country_servers)
                
            selected_servers.extend(country_servers)
            countries_processed += 1
            
            cities_count = len(set(s.city for s in country_servers))
            self.ui.info(f"Selected {len(country_servers)} servers from {cities_count} cities in {country_code}")
        
        # Ensure we have exactly the right number of servers
        if len(selected_servers) > max_total_servers:
            random.shuffle(selected_servers)
            selected_servers = selected_servers[:max_total_servers]
            
            # Update selected_countries counts
            selected_countries = {}
            for server in selected_servers:
                country_code = server.hostname.split('-')[0]
                selected_countries[country_code] = selected_countries.get(country_code, 0) + 1
        
        # Sort by distance
        selected_servers.sort(key=lambda x: x.distance_km)
        
        # Display success message
        msg = f"Selected {len(selected_servers)} servers from {countries_processed} countries"
        if exclude_continent:
            msg += f" outside of {exclude_continent}"
        self.ui.success(msg)

        if exclude_continent:
            self.ui.info("Selected countries and server counts:")
            for country_code, count in sorted(selected_countries.items(), key=lambda x: x[1], reverse=True):
                country_name = None
                for server in self.servers:
                    if server.hostname.startswith(country_code):
                        country_name = server.country
                        break
                if country_name:
                    self.ui.info(f"  • {country_name} ({country_code}): {count} servers")
                else:
                    self.ui.info(f"  • {country_code}: {count} servers")
        
        return selected_servers

    def _run_speedtest(self, distance_km=0):
        """Run speedtest-cli and return results.
        
        distance_km is used to scale the timeout: servers beyond DISTANCE_THRESHOLD_DISTANT
        get a longer timeout because high-latency VPN tunnels (300–600 ms ping) make
        speedtest-cli's HTTP phases take significantly longer.
        """
        speedtest_timeout = (
            MAX_SPEEDTEST_TIME_DISTANT if distance_km >= DISTANCE_THRESHOLD_DISTANT
            else MAX_SPEEDTEST_TIME
        )
        try:
            self.log_and_info("Running speed test...")
                
            cmd = ["speedtest-cli", "--json", "--secure", "--timeout", "20"]

            stdout, stderr, returncode, timed_out, elapsed_time = self.ui.run_command_with_spinner(
                cmd, f"{get_symbol('speedometer')} Speed test in progress", speedtest_timeout
            )

            if timed_out:
                self.ui.info(f"Speed test canceled after {speedtest_timeout:.0f}s (maximum time reached)")
                return SpeedTestResult(0, 0, 0, 0, 100)

            if elapsed_time < MIN_SPEEDTEST_TIME:
                self.ui.info(
                    f"{get_symbol('speedometer')} Speed test completed too quickly ({elapsed_time:.1f}s), may be unreliable"
                )
                logger.warning(
                    f"Speed test completed too quickly: {elapsed_time:.2f}s < {MIN_SPEEDTEST_TIME}s minimum"
                )
                time.sleep(1)

            if returncode != 0:
                if stderr and "403: Forbidden" in stderr:
                    self.ui.info("Speedtest service unavailable from this VPN server (IP likely blocked)")
                    logger.warning("Speedtest service blocked this VPN server's IP address (403 Forbidden)")
                else:
                    self.ui.info(f"Speed test failed: {stderr if stderr else 'Unknown error'}")
                    logger.error(f"Speedtest failed: {stderr}")
                return SpeedTestResult(0, 0, 0, 0, 100)

            try:
                data = json.loads(stdout)
            except json.JSONDecodeError as e:
                self.ui.info("Speed test results not usable (JSON parsing error)")
                logger.error(f"JSON parse error on output: {e}")
                return SpeedTestResult(0, 0, 0, 0, 100)

            # Check required fields
            required_fields = ['download', 'upload', 'ping']
            if not all(field in data for field in required_fields):
                field = next((f for f in required_fields if f not in data), "unknown field")
                logger.error(f"Missing required field in speedtest result: {field}")
                self.ui.info(f"Speed test results missing required data (no {field})")
                return SpeedTestResult(0, 0, 0, 0, 100)

            # Create SpeedTestResult from data
            result = SpeedTestResult(
                download_speed=data['download'] / 1_000_000,  # Convert to Mbps
                upload_speed=data['upload'] / 1_000_000,      # Convert to Mbps
                ping=data['ping'],
                jitter=data.get('jitter', 0),                 # Safe access with default
                packet_loss=data.get('packetLoss', 0)         # Safe access with default
            )

            logger.info(f"Speedtest results - Download: {result.download_speed:.2f} Mbps, "
                       f"Upload: {result.upload_speed:.2f} Mbps, Ping: {result.ping:.2f} ms")
            
            self.ui.success("Speed test results:")
            self.ui.info(format_speedtest_results(result))
                
            return result
        except Exception as e:
            logger.error(f"Unexpected error during speedtest: {e}")
            self.ui.info(f"Speed test unavailable (technical error: {str(e)[:50]})")
            return SpeedTestResult(0, 0, 0, 0, 100)

    def _run_mtr(self):
        """Run network latency test to target host.

        Attempts (in order):
          1. mtr without sudo  — works if mtr-packet has the SUID bit set
          2. sudo -n mtr       — non-interactive (no password prompt); works if
                                  sudo credentials are cached
          3. ping fallback     — always works, provides avg latency + packet loss
                                  (no hop data; hops reported as 0)
        """
        try:
            self.log_and_info(f"Running MTR test to {self.target_host}...")

            count, timeout = 10, 60
            mtr_args = ["-n", "-c", str(count), "-r", self.target_host]

            stdout, stderr, returncode, timed_out = "", "", 1, False

            # Attempt 1: mtr without sudo
            cmd = ["mtr"] + mtr_args
            stdout, stderr, returncode, timed_out, _ = self.ui.run_command_with_spinner(
                cmd, f"{get_symbol('ping')} MTR test in progress", timeout
            )

            # Attempt 2: sudo -n mtr (non-interactive — never prompts for password)
            if not timed_out and returncode != 0:
                cmd = ["sudo", "-n", "mtr"] + mtr_args
                stdout, stderr, returncode, timed_out, _ = self.ui.run_command_with_spinner(
                    cmd, f"{get_symbol('ping')} MTR test in progress (elevated)", timeout
                )

            # Attempt 3: ping fallback (mtr unavailable or broken on this OS)
            if not timed_out and returncode != 0:
                logger.warning(f"mtr unavailable (stderr: {stderr.strip()!r}), falling back to ping")
                return self._run_ping_fallback(count, timeout)

            if timed_out:
                self.ui.info("MTR test timed out")
                self._emit_json_status("mtr_failed", "MTR test timed out")
                return MtrResult(0, 100, 0)

            # Parse MTR report output
            lines = stdout.strip().split('\n')[1:]  # skip header line
            if not lines:
                self.log_and_warning("No MTR results received")
                return MtrResult(0, 100, 0)

            last_hop = lines[-1].split()
            avg_latency = float(last_hop[7])
            packet_loss = float(last_hop[2].rstrip('%'))
            hops = len(lines)

            logger.info(f"MTR results — Latency: {avg_latency:.2f} ms, "
                        f"Packet Loss: {packet_loss:.2f}%, Hops: {hops}")
            self.ui.success("MTR test results:")
            self.ui.info(format_mtr_results(result=MtrResult(avg_latency, packet_loss, hops)))
            return MtrResult(avg_latency, packet_loss, hops)

        except Exception as e:
            logger.error(f"Unexpected error during MTR test: {e}")
            self.ui.info("MTR test unavailable (technical error)")
            return MtrResult(0, 100, 0)

    def _run_ping_fallback(self, count: int = 10, timeout: int = 30) -> "MtrResult":
        """Fallback latency measurement using ping when mtr is unavailable."""
        try:
            self.ui.info("MTR unavailable — using ping for latency measurement")
            self._emit_json_status("mtr_ping_fallback", "MTR unavailable, using ping")
            cmd = ["ping", "-c", str(count), "-q", self.target_host]
            stdout, stderr, returncode, timed_out, _ = self.ui.run_command_with_spinner(
                cmd, f"{get_symbol('ping')} Ping test in progress", timeout
            )
            if timed_out or returncode != 0:
                self.ui.info("Ping test failed")
                self._emit_json_status("mtr_failed", "Ping test failed")
                logger.error(f"Ping failed: {stderr}")
                return MtrResult(0, 100, 0)

            # Parse macOS/Linux ping -q summary:
            # "5 packets transmitted, 5 received, 0.0% packet loss"
            # "round-trip min/avg/max/stddev = 1.2/3.4/5.6/0.8 ms"
            avg_latency, packet_loss = 0.0, 0.0
            for line in stdout.splitlines():
                if "packet loss" in line:
                    import re
                    m = re.search(r"([\d.]+)%\s+packet loss", line)
                    if m:
                        packet_loss = float(m.group(1))
                if "min/avg/max" in line or "round-trip" in line:
                    import re
                    m = re.search(r"[\d.]+/([\d.]+)/[\d.]+", line)
                    if m:
                        avg_latency = float(m.group(1))

            logger.info(f"Ping fallback — Latency: {avg_latency:.2f} ms, Loss: {packet_loss:.2f}%")
            self.ui.success("Ping results:")
            self.ui.info(format_mtr_results(result=MtrResult(avg_latency, packet_loss, 0)))
            return MtrResult(avg_latency, packet_loss, 0)
        except Exception as e:
            logger.error(f"Ping fallback error: {e}")
            return MtrResult(0, 100, 0)

    def connect_to_server(self, server):
        """Connect to a specific Mullvad server with timeout"""
        try:
            logger.info(f"Connecting to server {server.hostname} ({server.city}, {server.country})...")
            self.ui.header(f"SERVER TEST: {server.hostname}")
            self.ui.info(format_server_info(server))
            self.ui.connection_status(server.hostname, "connecting")
            self._emit_json_status("connecting", f"Connecting: {server.hostname}",
                                  hostname=server.hostname)

            connection_start_time = time.time()
            total_timeout = self.connection_timeout
            
            try:
                self.ui.info(f"Configuring relay...")
                
                # Configure relay
                result = run_command(
                    ["mullvad", "relay", "set", "location", server.hostname],
                    timeout=min(5, total_timeout/4), check=True, capture_output=True
                )
                
                if result is None or isinstance(result, Exception):
                    self.ui.connection_status(server.hostname, "error")
                    return False
                
                self.ui.info(f"Initiating connection...")
                    
                # Connect to VPN
                result = run_command(
                    ["mullvad", "connect"],
                    timeout=min(5, total_timeout/4), check=True, capture_output=True
                )
                
                if result is None or isinstance(result, Exception):
                    self.ui.connection_status(server.hostname, "error")
                    return False
                
            except Exception:
                self.ui.connection_status(server.hostname, "error")
                return False
                
            elapsed_setup_time = time.time() - connection_start_time
            remaining_time = max(1, total_timeout - elapsed_setup_time)
            
            self.ui.info(f"Waiting for connection confirmation (total timeout: {total_timeout:.1f}s)...")

            poll_interval = 0.1  # Visual update every 100ms for smooth progress bar
            status_check_interval = 0.5  # Check mullvad status every 500ms to reduce subprocess overhead
            max_steps = int(remaining_time / poll_interval)
            last_status_check = 0.0

            for i in range(max_steps):
                current_time = time.time()
                total_elapsed = current_time - connection_start_time

                if total_elapsed >= total_timeout:
                    break

                # Only spawn subprocess at the defined interval to reduce CPU load
                if current_time - last_status_check >= status_check_interval:
                    last_status_check = current_time
                    try:
                        output = subprocess.check_output(["mullvad", "status"], text=True, timeout=2)
                        if "Connected" in output:
                            server.connection_time = total_elapsed
                            logger.info(f"Successfully connected to server in {total_elapsed:.2f} seconds")
                            print(f"\r{' ' * get_terminal_width()}", end='\r')
                            self.ui.connection_status(server.hostname, "success", total_elapsed)
                            return True
                    except Exception:
                        pass

                self.ui.progress_bar(
                    total_elapsed, total_timeout,
                    prefix=f"{get_symbol('connecting')} Connection: ",
                    suffix=f"{total_elapsed:.1f}s / {total_timeout:.1f}s"
                )
                time.sleep(poll_interval)

            print(f"\r{' ' * get_terminal_width()}", end='\r')  # Clear progress bar
            self.ui.connection_status(server.hostname, "timeout")
            self.ui.info(f"Server {server.hostname} did not respond within the timeout of {total_timeout:.1f}s")

            logger.warning(f"Failed to connect to server within {total_timeout:.1f} seconds")
            server.connection_time = 0
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error while connecting to server: {e}")
            self.ui.connection_status(server.hostname, "error")
            self.ui.error(f"Connection error: {str(e).split(':')[0]}")
            return False

    def test_server(self, server):
        """Test a single server's performance with connection stabilization period"""
        viable = True  # Assume server is viable initially
        
        if not self.connect_to_server(server):
            logger.warning(f"Skipping tests for {server.hostname} due to connection failure")
            return SpeedTestResult(0, 0, 0, 0, 100), MtrResult(0, 100, 0), False

        self.ui.info(f"Allowing connection to stabilize before testing...")

        stabilization_time = 8  # seconds to allow for connection optimization
        self._emit_json_status("stabilizing", f"Stabilizing: {server.hostname}",
                              hostname=server.hostname)

        self.ui.spinner(
            f"{get_symbol('connecting')} Stabilizing connection",
            lambda stop_event: stop_event.wait(stabilization_time),
            timeout=stabilization_time,
        )
        self.ui.success("Connection stabilized and ready for testing")

        # Run speed test
        self._emit_json_status("speedtest_running", f"Speed testing: {server.hostname}",
                              hostname=server.hostname)
        speedtest_result = self._run_speedtest(distance_km=server.distance_km)
        
        if speedtest_result.download_speed < self.min_download_speed and speedtest_result.download_speed > 0:
            self.ui.info(f"Insufficient speed: {speedtest_result.download_speed:.2f} Mbps < {self.min_download_speed} Mbps")
            self.ui.info(f"Server {server.hostname} is classified as non-viable")
            viable = False
        
        # Run MTR test if speed test was successful
        if speedtest_result.download_speed == 0:
            self.ui.info(f"Speed test unsuccessful, MTR test skipped")
            mtr_result = MtrResult(0, 100, 0)
        else:
            self._emit_json_status("mtr_running", f"MTR test: {server.hostname}",
                                  hostname=server.hostname)
            mtr_result = self._run_mtr()
        
        if speedtest_result.download_speed > 0 and mtr_result.avg_latency > 0:
            self.successful_servers += 1
            if viable:
                self.ui.success(f"Test successful for {server.hostname} ✓")
            else:
                self.ui.info(f"Test successful but insufficient speed for {server.hostname}")
        else:
            self.ui.info(f"Server {server.hostname} did not respond correctly")
            viable = False
            
        return speedtest_result, mtr_result, viable

    def _save_results_to_db(self, session_id, server, speedtest, mtr, viable):
        """Save server test results to SQLite database"""
        if session_id is None: return False

        try:
            with self._with_db_cursor() as c:
                c.execute('''INSERT INTO server_results (
                    session_id, hostname, country, city, distance_km, connection_time,
                    download_speed, upload_speed, ping, jitter, speedtest_packet_loss,
                    mtr_latency, mtr_packet_loss, mtr_hops, viable
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                    session_id, server.hostname, server.country, server.city, server.distance_km,
                    server.connection_time, speedtest.download_speed, speedtest.upload_speed,
                    speedtest.ping, speedtest.jitter, speedtest.packet_loss,
                    mtr.avg_latency, mtr.packet_loss, mtr.hops, 1 if viable else 0
                ))
            logger.debug(f"Saved results for server {server.hostname} to database")
            return True

        except Exception as e:
            logger.error(f"Error saving results to database: {e}")
            return False

    def _prepare_session(self, max_servers, max_distance):
        """Prepare testing session and return session data"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        protocol = "WireGuard"
        results_file = RUNTIME_DIR / f"mullvad_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}_wireguard.log"
        if max_servers is None:
            max_servers = DEFAULT_MAX_SERVERS

        self.successful_servers = 0

        protocol_servers = [s for s in self.servers if s.hostname.split('-')[2] == 'wg']
        if not protocol_servers:
            self.log_and_error(f"No servers found for protocol {protocol}")
            return None

        avg_time = self.run_connection_calibration()

        self.ui.header("MULLVAD VPN TEST PARAMETERS")
        params = [
            f"Date                : {timestamp}",
            f"Location            : {self.reference_location}",
            f"Protocol            : {protocol}",
            f"Minimum servers     : {self.min_viable_servers} viable",
            f"Initial servers     : {max_servers}",
            f"Connection timeout  : {self.connection_timeout:.1f}s",
            f"Maximum distance    : {max_distance if max_distance else 'No limit'} km",
            f"Results file        : {results_file}"
        ]
        for param in params:
            self.ui.info(param)
        self.ui.info("")

        try:
            with self._with_db_cursor() as c:
                c.execute("INSERT INTO test_sessions (timestamp, reference_location, reference_lat, reference_lon, protocol) VALUES (?, ?, ?, ?, ?)", (
                    timestamp, self.reference_location,
                    self.reference_coords[0], self.reference_coords[1], protocol
                ))
                session_id = c.lastrowid
            logger.info(f"Created new test session with ID {session_id}")
        except Exception as e:
            logger.error(f"Error creating test session in database: {e}")
            session_id = None

        f = open(results_file, 'w')
        f.write("Mullvad VPN Server Performance Test Results\n")
        f.write(f"Test Date: {timestamp}\n")
        f.write(f"Reference Location: {self.reference_location}\n")
        f.write(f"Target Host for MTR: {self.target_host}\n")
        f.write(f"Protocol: {protocol}\n")
        f.write(f"Connection Timeout: {self.connection_timeout:.1f}s")
        if avg_time:
            f.write(f" (calibrated from average {avg_time:.2f}s)")
        f.write("\n")
        f.write(f"Minimum Viable Servers Required: {self.min_viable_servers}\n")
        f.write(f"Initial Servers to Test: {max_servers}\n")
        if max_distance:
            f.write(f"Maximum Distance: {max_distance} km\n")
        f.write("=" * 80 + "\n\n")

        if max_distance is not None:
            all_servers_filtered = [s for s in protocol_servers if s.distance_km <= max_distance]
        else:
            all_servers_filtered = protocol_servers

        initial_servers = self._select_servers(
            all_servers_filtered,
            max_per_country=5,
            max_total_servers=max_servers
        )
        remaining_servers = [s for s in all_servers_filtered if s not in initial_servers]

        self._emit_json_status("selection", f"Selected {len(initial_servers)} servers",
                              count=len(initial_servers), total_available=len(all_servers_filtered),
                              max_distance=max_distance, continent=getattr(self, 'user_continent', 'Unknown'))

        self.ui.header("STARTING TESTS")
        message = (
            f"Starting tests on {len(initial_servers)} servers" +
            (f" within {max_distance} km" if max_distance else "")
        )
        self.log_and_info(message)

        return session_id, results_file, f, initial_servers, remaining_servers

    def _test_server_list(self, servers, file_handle, session_id, tested_servers, initial_total, viable_servers):
        """Test a list of servers and return updated viable count"""
        for server in servers:
            tested_servers.append(server)
            idx = len(tested_servers)

            logger.info(f"\nTesting server {idx}/{initial_total}: {server.hostname}")

            self.ui.header(f"TEST {idx}/{initial_total if idx <= initial_total else '+'}")
            self.ui.info(f"Server: {server.hostname}")
            self.ui.info(f"Location: {server.city}, {server.country}")
            self.ui.info(f"Distance: {server.distance_km:.0f} km")

            country_code = server.hostname.split('-')[0]
            continent = COUNTRY_TO_CONTINENT.get(country_code, 'Unknown')
            self._emit_json_status("testing", f"Testing {server.hostname}",
                                  hostname=server.hostname, city=server.city,
                                  country=server.country, continent=continent,
                                  distance_km=round(server.distance_km, 1),
                                  index=idx, total=initial_total)

            speedtest_result, mtr_result, viable = self.test_server(server)
            self.results[server.hostname] = (speedtest_result, mtr_result, viable)

            if viable:
                viable_servers += 1

            if session_id:
                self._save_results_to_db(session_id, server, speedtest_result, mtr_result, viable)
            self._write_server_results_to_file(file_handle, server, speedtest_result, mtr_result, viable)

            if self.machine_readable:
                self._emit_json_result(server, speedtest_result, mtr_result, viable)

            self._emit_json_status("progress", f"{idx} tested, {viable_servers} viable",
                                  tested=idx, viable=viable_servers,
                                  successful=self.successful_servers,
                                  target=self.min_viable_servers)

            self.ui.info(
                f"Progress: {idx} servers tested ({self.successful_servers} successful, {viable_servers} viable)"
            )

            if viable_servers >= self.min_viable_servers and idx >= initial_total:
                logger.info(
                    f"Found {viable_servers} viable servers after testing {idx} servers. Stopping tests."
                )
                self.ui.success(
                    f"Goal achieved: {viable_servers}/{self.min_viable_servers} viable servers found."
                )
                break

            if len(tested_servers) >= self.max_servers_hard_limit:
                logger.warning(
                    f"Reached hard limit of {self.max_servers_hard_limit} servers tested without finding {self.min_viable_servers} viable servers"
                )
                self.ui.warning(
                    f"Maximum limit reached: {self.max_servers_hard_limit} servers tested"
                )
                self.ui.warning(
                    f"Unable to find {self.min_viable_servers} viable servers"
                )
                break

        return viable_servers

    def _extend_selection_if_needed(self, viable_servers, tested_servers, remaining_servers, file_handle, initial_total):
        """Select additional servers if more viable ones are needed"""
        if len(tested_servers) == initial_total:
            logger.info(
                f"Extending testing beyond initial {initial_total} servers to find {self.min_viable_servers} viable servers"
            )
            self.ui.warning(
                f"Only {viable_servers}/{self.min_viable_servers} viable servers found"
            )
            self.ui.info(
                f"Searching for servers on continents other than {self.user_continent}"
            )
            self._emit_json_status("extension", "Expanding search to other continents",
                                  viable=viable_servers, target=self.min_viable_servers,
                                  exclude_continent=self.user_continent)
            file_handle.write(
                f"\nNote: Extending testing beyond initial {initial_total} servers to find at least {self.min_viable_servers} viable servers.\n"
            )
            file_handle.write(
                f"Excluding servers from {self.user_continent} and selecting from other continents.\n\n"
            )

        remaining_to_test = min(
            self.max_servers_hard_limit - len(tested_servers),
            (self.min_viable_servers - viable_servers) * 3,
        )
        if remaining_to_test <= 0:
            return [], remaining_servers

        available = [s for s in remaining_servers if s not in tested_servers]
        additional_servers = self._select_servers(
            available,
            max_per_country=3,
            max_total_servers=remaining_to_test,
            exclude_continent=self.user_continent,
            tested_servers=tested_servers,
        )

        if additional_servers:
            countries_count = len({s.hostname.split('-')[0] for s in additional_servers})
            self.ui.info(
                f"Found {len(additional_servers)} servers from {countries_count} countries"
            )
            remaining_servers = [s for s in remaining_servers if s not in additional_servers]
            return additional_servers, remaining_servers

        self.log_and_warning("No more servers available for additional testing")
        return [], remaining_servers

    def _write_summary(self, results_file, viable_servers, tested_count):
        """Write summary of results and display final messages"""
        if self.results:
            self._print_summary(results_file, viable_servers)

            self.ui.header("TESTS COMPLETED")
            self.ui.success(
                f"Tests successfully completed: {self.successful_servers} functional servers out of {tested_count} tested"
            )
            if viable_servers >= self.min_viable_servers:
                self.ui.success(
                    f"Goal achieved: {viable_servers}/{self.min_viable_servers} viable servers (speed > {self.min_download_speed} Mbps)"
                )
            else:
                self.ui.warning(
                    f"Goal not achieved: {viable_servers}/{self.min_viable_servers} viable servers (speed > {self.min_download_speed} Mbps)"
                )
            self.ui.info(f"Detailed results saved in: {results_file}")

            if self.ui.interactive and self.open_results_prompt:
                print("\nWould you like to open the results file?")
                choice = input("Open file? (y/n): ").strip().lower()
                if choice.startswith('y'):
                    try:
                        if sys.platform == 'darwin':
                            subprocess.call(('open', str(results_file)))
                        elif sys.platform == 'win32':
                            os.startfile(str(results_file))
                        else:
                            subprocess.call(('xdg-open', str(results_file)))
                    except Exception as e:
                        self.ui.error(f"Unable to open file: {e}")
        else:
            self.log_and_error("No test results available to generate a summary.")

    def run_tests(self, max_servers=None, max_distance=None):
        """Run tests on servers"""
        session = self._prepare_session(max_servers, max_distance)
        if not session:
            return

        session_id, results_file, file_handle, initial_servers, remaining_servers = session
        tested_servers = []
        try:
            viable_servers = self._test_server_list(initial_servers, file_handle, session_id, tested_servers, len(initial_servers), 0)

            while viable_servers < self.min_viable_servers and len(tested_servers) < self.max_servers_hard_limit:
                additional_servers, remaining_servers = self._extend_selection_if_needed(
                    viable_servers, tested_servers, remaining_servers, file_handle, len(initial_servers)
                )
                if not additional_servers:
                    break
                viable_servers = self._test_server_list(
                    additional_servers, file_handle, session_id, tested_servers, len(initial_servers), viable_servers
                )
        finally:
            file_handle.close()
        self._write_summary(results_file, viable_servers, len(tested_servers))

    def _write_server_results_to_file(self, file, server, speedtest_result, mtr_result, viable):
        """Write server test results to the log file"""
        results = [
            f"Server: {server.hostname}",
            f"Location: {server.city}, {server.country}",
            f"Distance: {server.distance_km:.0f} km",
            f"Provider: {server.provider} ({server.ownership})",
            f"Protocol: {server.protocol}",
            f"Connection Time: {server.connection_time:.2f} seconds",
            f"Viable: {'Yes' if viable else 'No'}",
            "\nSpeedtest Results:",
            f"Download: {speedtest_result.download_speed:.2f} Mbps",
            f"Upload: {speedtest_result.upload_speed:.2f} Mbps",
            f"Ping: {speedtest_result.ping:.2f} ms",
            f"Jitter: {speedtest_result.jitter:.2f} ms",
            f"Packet Loss: {speedtest_result.packet_loss:.2f}%",
            "\nMTR Results:",
            f"Average Latency: {mtr_result.avg_latency:.2f} ms",
            f"Packet Loss: {mtr_result.packet_loss:.2f}%",
            f"Number of Hops: {mtr_result.hops}",
            "=" * 80 + "\n"
        ]
        file.write("\n".join(results) + "\n")
        file.flush()  # Ensure data is written immediately

    def _emit_json_result(self, server, speedtest_result, mtr_result, viable):
        """Emit a JSON line to stdout for machine-readable consumption (GUI integration)"""
        record = {
            "type": "result",
            "hostname": server.hostname,
            "country": server.country,
            "city": server.city,
            "distance_km": round(server.distance_km, 1),
            "connection_time": round(server.connection_time, 2),
            "download_speed": round(speedtest_result.download_speed, 2),
            "upload_speed": round(speedtest_result.upload_speed, 2),
            "ping": round(speedtest_result.ping, 2),
            "jitter": round(speedtest_result.jitter, 2),
            "packet_loss": round(speedtest_result.packet_loss, 2),
            "mtr_latency": round(mtr_result.avg_latency, 2),
            "mtr_packet_loss": round(mtr_result.packet_loss, 2),
            "mtr_hops": mtr_result.hops,
            "viable": viable,
        }
        print(json.dumps(record, separators=(',', ':')), flush=True)

    def _emit_json_status(self, phase, message, **extra):
        """Emit a JSON status line for GUI consumption"""
        if not self.machine_readable:
            return
        record = {"type": "status", "phase": phase, "message": message}
        record.update(extra)
        print(json.dumps(record, separators=(',', ':')), flush=True)

    def _print_summary_table(self, servers_list, title, file_handle=None, field_fn=None, header_list=None):
        """Generate a formatted summary table for terminal and log file"""
        if not servers_list: return
        
        # Default headers if not provided
        if not header_list: header_list = ["Server", "Country", "Distance", "Value"]
            
        # Calculate column widths
        col_widths = [
            max(len(header_list[0]), max([len(s[0]) for s in servers_list])),
            max(len(header_list[1]), max([len(self._server_by_hostname[s[0]].country) for s in servers_list])),
            max(len(header_list[2]), 10),  # Distance column
            max(len(header_list[3]), 10)   # Value column
        ]
        
        # Format header and separator
        header = "| " + " | ".join([header_list[i].ljust(col_widths[i]) for i in range(len(header_list))]) + " |"
        separator = "+-" + "-+-".join(["-" * col_widths[i] for i in range(len(header_list))]) + "-+"
        
        # Generate table rows
        rows = []
        for hostname, value in servers_list:
            server = self._server_by_hostname[hostname]
            formatted_value = field_fn(value) if field_fn else str(value)
            rows.append("| " + hostname.ljust(col_widths[0]) + " | " + \
                  server.country.ljust(col_widths[1]) + " | " + \
                  f"{server.distance_km:.0f} km".ljust(col_widths[2]) + " | " + \
                  formatted_value.ljust(col_widths[3]) + " |")
        
        # Write to file if specified
        if file_handle:
            file_handle.write(f"\n{title}\n")
            file_handle.write(separator + "\n")
            file_handle.write(header + "\n")
            file_handle.write(separator + "\n")
            for row in rows: file_handle.write(row + "\n")
            file_handle.write(separator + "\n")
            
        # Display in terminal
        self.ui.header(title)
        print(separator)
        print(colorize(header, Fore.CYAN))
        print(separator)
        for row in rows:
            print(row)
        print(separator)
        print("")  # Add a blank line
        
        return separator, header, rows

    def _print_summary(self, results_file, viable_servers):
        """Print a summary of the best performing servers"""
        if not self.results:
            logger.error("No results available for summary")
            return

        try:
            # Get viable hostnames
            viable_hostname_set = {hostname for hostname, (_, _, viable) in self.results.items() if viable}
            
            # Sort servers by different metrics
            sorted_servers = {
                'distance': sorted(
                    [(s.hostname, s.distance_km) for s in self.servers if s.hostname in viable_hostname_set],
                    key=lambda x: x[1]
                ),
                'download': sorted(
                    [(hostname, data[0].download_speed) for hostname, data in self.results.items() if hostname in viable_hostname_set],
                    key=lambda x: x[1], reverse=True
                ),
                'upload': sorted(
                    [(hostname, data[0].upload_speed) for hostname, data in self.results.items() if hostname in viable_hostname_set],
                    key=lambda x: x[1], reverse=True
                ),
                'latency': sorted(
                    [(hostname, data[1].avg_latency) for hostname, data in self.results.items() if hostname in viable_hostname_set],
                    key=lambda x: x[1] if x[1] > 0 else float('inf')
                ),
                'packet_loss': sorted(
                    [(hostname, data[0].packet_loss + data[1].packet_loss) for hostname, data in self.results.items() if hostname in viable_hostname_set],
                    key=lambda x: x[1]
                ),
                'connection_time': sorted(
                    [(hostname, self._server_by_hostname[hostname].connection_time) 
                    for hostname in viable_hostname_set if self._server_by_hostname[hostname].connection_time > 0],
                    key=lambda x: x[1]
                )
            }

            with open(results_file, 'a') as f:
                # Write summary header
                f.write("\nSUMMARY\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Reference Location: {self.reference_location}\n")
                f.write(f"Total Servers Tested: {len(self.results)}\n")
                f.write(f"Successful Servers: {self.successful_servers}\n")
                f.write(f"Viable Servers (>{self.min_download_speed} Mbps): {viable_servers}\n\n")

                if viable_servers > 0:
                    # Print summary tables for each metric
                    metrics = [
                        ('distance', "Top 5 Viable Servers by Distance", lambda x: f"{x:.0f} km"),
                        ('connection_time', "Top 5 Viable Servers by Connection Time", lambda x: f"{x:.2f} sec"),
                        ('download', "Top 5 Viable Servers by Download Speed", lambda x: f"{x:.2f} Mbps", ["Server", "Country", "Distance", "Download"]),
                        ('upload', "Top 5 Viable Servers by Upload Speed", lambda x: f"{x:.2f} Mbps", ["Server", "Country", "Distance", "Upload"]),
                        ('latency', "Top 5 Viable Servers by Latency", lambda x: f"{x:.2f} ms", ["Server", "Country", "Distance", "Latency"]),
                        ('packet_loss', "Top 5 Viable Servers by Reliability (Lowest Packet Loss)", lambda x: f"{x:.2f}%", ["Server", "Country", "Distance", "Loss"])
                    ]
                    
                    for metric, title, fmt_fn, *headers in metrics:
                        self._print_summary_table(
                            sorted_servers[metric][:5], title, f, field_fn=fmt_fn,
                            header_list=headers[0] if headers else None
                        )

                    # Calculate global statistics
                    valid_results = [(hostname, s, m) for hostname, (s, m, v) in self.results.items()
                                   if v and s.download_speed > 0 and m.avg_latency > 0]

                    if valid_results:
                        # Calculate averages
                        avg_download = statistics.mean(r[1].download_speed for r in valid_results)
                        avg_upload = statistics.mean(r[1].upload_speed for r in valid_results)
                        avg_latency = statistics.mean(r[2].avg_latency for r in valid_results)

                        successful_connections = [self._server_by_hostname[hostname].connection_time 
                                               for hostname in viable_hostname_set 
                                               if self._server_by_hostname[hostname].connection_time > 0]
                        avg_connection_time = statistics.mean(successful_connections) if successful_connections else 0

                        # Write statistics 
                        f.write("\nGLOBAL STATISTICS (viable servers only):\n")
                        f.write(f"Average Connection Time: {avg_connection_time:.2f} seconds\n")
                        f.write(f"Average Download Speed: {avg_download:.2f} Mbps\n")
                        f.write(f"Average Upload Speed: {avg_upload:.2f} Mbps\n")
                        f.write(f"Average Latency: {avg_latency:.2f} ms\n")
                        
                        self.ui.header("GLOBAL STATISTICS")
                        self.ui.info(f"Average connection time: {avg_connection_time:.2f} seconds")
                        self.ui.info(f"Average download speed: {avg_download:.2f} Mbps")
                        self.ui.info(f"Average upload speed: {avg_upload:.2f} Mbps")
                        self.ui.info(f"Average latency: {avg_latency:.2f} ms")
                        self.ui.info("")
                    else: f.write("\nNo valid test results available for statistics\n")

                    # Calculate best servers
                    best_servers = self._calculate_best_overall_servers(viable_hostname_set)
                    if best_servers:
                        self._print_summary_table(
                            best_servers[:5],
                            "Best Overall Viable Servers (Score combines Speed, Latency, and Reliability)",
                            f, field_fn=lambda x: f"{x:.2f}",
                            header_list=["Server", "Country", "Distance", "Score"]
                        )
                        
                        self.ui.header("BEST SERVERS DETAILS")
                        for hostname, score in best_servers[:3]:
                            server = self._server_by_hostname[hostname]
                            speed_result, mtr_result, _ = self.results[hostname]
                            print(
                                f"{colorize(hostname, Fore.CYAN)} ({server.city}, {server.country}): "
                                f"Score {colorize(f'{score:.2f}', Fore.GREEN)}"
                            )
                            print(
                                f"  → {colorize('↓'+f'{speed_result.download_speed:.1f} Mbps', Fore.GREEN)} "
                                f"{colorize('↑'+f'{speed_result.upload_speed:.1f} Mbps', Fore.BLUE)} "
                                f"{colorize('⏱'+f'{mtr_result.avg_latency:.1f} ms', Fore.YELLOW)}, "
                                f"Loss: {mtr_result.packet_loss:.1f}%"
                            )
                        print("")
                else:
                    f.write("\nNo viable servers found.\n")
                    f.write(f"Consider increasing the distance range or checking your connection.\n")

                    self.ui.warning("No viable servers found.")
                    self.ui.info("Consider increasing the distance range or checking your connection.")

        except Exception as e:
            self.log_and_error(f"Error generating summary: {e}")

    def _calculate_best_overall_servers(self, viable_hostname_set):
        """Calculate best overall servers using a weighted scoring system"""
        try:
            # Get maximum values for normalization
            max_download = max((res[0].download_speed for hostname, res in self.results.items() 
                               if hostname in viable_hostname_set and res[0].download_speed > 0), default=1)
            max_upload = max((res[0].upload_speed for hostname, res in self.results.items() 
                             if hostname in viable_hostname_set and res[0].upload_speed > 0), default=1)
            
            # Calculate scores with list comprehension for efficiency
            scores = {hostname: (
                (speed.download_speed / max_download) * 0.4 +  # 40% weight on download speed
                (speed.upload_speed / max_upload) * 0.2 +      # 20% weight on upload speed
                (1 / (1 + mtr.avg_latency / 100)) * 0.3 +      # 30% weight on ping
                (1 - ((speed.packet_loss + mtr.packet_loss) / 100)) * 0.1  # 10% weight on reliability
            ) for hostname, (speed, mtr, viable) in self.results.items() 
              if viable and speed.download_speed > 0 and mtr.avg_latency > 0}
                
            return sorted(scores.items(), key=lambda x: x[1], reverse=True)
        except Exception as e:
            logger.error(f"Error calculating best servers: {e}")
            return []

def input_custom_parameters(args, ui):
    """Interactive function to customize test parameters before the summary"""

    ui.header("CUSTOMIZATION OF TEST PARAMETERS")
    ui.info("You can customize the test parameters before starting.")
    ui.info("Press Enter to keep the default values.")
    print("")

    # Get location if not provided
    if args.location == DEFAULT_LOCATION:
        args.location = input_location(ui)

    ui.header("CUSTOMIZATION OF TEST CRITERIA")
    try:
        # Get parameters with validation in a compact format
        params = [
            ("Maximum number of servers", "max_servers", int),
            ("Hard limit on number of servers", "max_servers_hard_limit", int),
            ("Min. download speed (Mbps)", "min_download_speed", float),
            ("Connection timeout (seconds)", "connection_timeout", float),
            ("Minimum number of viable servers", "min_viable_servers", int)
        ]

        for prompt, param, converter in params:
            value = input(f"{prompt} [{getattr(args, param)}]: ").strip()
            if value:
                setattr(args, param, converter(value))

        # Handle max distance separately due to special None case
        if args.max_distance is None:
            max_distance_input = input("Maximum distance (km) [no limit]: ").strip()
            if max_distance_input:
                args.max_distance = float(max_distance_input)
        else:
            max_distance_input = input(f"Maximum distance (km) [{args.max_distance}]: ").strip()
            if max_distance_input:
                args.max_distance = None if max_distance_input.lower() in ['none', 'no', '0'] else float(max_distance_input)

        ui.success("Custom parameters saved.")
    except ValueError as e:
        ui.error(f"Input error: {e}")
        ui.warning("Using default values for invalid parameters.")

    return args

def check_dependencies():
    """Check if required dependencies are installed"""
    missing_deps = []
    for binary, dep_name in [
        ("speedtest-cli", "speedtest-cli"),
        ("mtr", "mtr"),
        ("mullvad", "Mullvad VPN CLI")
    ]:
        if shutil.which(binary) is None:
            missing_deps.append(dep_name)
    return missing_deps

def check_optional_dependencies():
    """Check for optional dependencies and suggest installation"""
    try: import colorama; return []
    except ImportError: return ["colorama (for colored output): pip install colorama"]

def main():
    """Main function"""
    # Set up command-line arguments early so --help works without dependencies
    parser = argparse.ArgumentParser(description='Test Mullvad VPN servers performance')
    
    # Basic options
    parser.add_argument('--location', type=str, default=DEFAULT_LOCATION,
                      help=f'Reference location for distance calculation (default: {DEFAULT_LOCATION})')
    parser.add_argument('--max-servers', type=int, default=DEFAULT_MAX_SERVERS,
                      help=f'Maximum number of servers to test (default: {DEFAULT_MAX_SERVERS})')
    
    # Advanced options  
    parser.add_argument('--default-lat', type=float, default=None,
                      help='Default latitude to use if geocoding fails')
    parser.add_argument('--default-lon', type=float, default=None,
                      help='Default longitude to use if geocoding fails')
    parser.add_argument('--max-distance', type=float, default=None,
                      help='Maximum distance in km for server testing (default: no limit)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--db', type=str, default=str(DEFAULT_DB_FILE),
                      help=f'SQLite database file path (default: {DEFAULT_DB_FILE})')
    
    # Mode options
    parser.add_argument('--interactive', action='store_true',
                      help='Enable interactive mode with prompts for location input')
    parser.add_argument('--non-interactive', action='store_false', dest='interactive',
                      help='Disable interactive mode (useful for scripts)')
    
    # Testing criteria
    parser.add_argument('--max-servers-hard-limit', type=int, default=MAX_SERVERS_HARD_LIMIT,
                      help=f'Hard limit on the number of servers to test (default: {MAX_SERVERS_HARD_LIMIT})')
    parser.add_argument('--min-download-speed', type=float, default=MIN_DOWNLOAD_SPEED,
                      help=f'Minimum download speed in Mbps for viable servers (default: {MIN_DOWNLOAD_SPEED})')
    parser.add_argument('--connection-timeout', type=float, default=DEFAULT_CONNECTION_TIME,
                      help=f'Default connection timeout in seconds (default: {DEFAULT_CONNECTION_TIME})')
    parser.add_argument('--min-viable-servers', type=int, default=MIN_VIABLE_SERVERS,
                      help=f'Minimum number of viable servers required (default: {MIN_VIABLE_SERVERS})')
    parser.add_argument('--countdown-seconds', type=int, default=5,
                      help='Interactive countdown before tests start (default: 5)')
    parser.add_argument('--no-open-results', action='store_false', dest='open_results',
                      help='Do not prompt to open results file at the end')
    parser.add_argument('--machine-readable', action='store_true', default=False,
                      help='Emit JSON lines to stdout for each server result (for GUI integration)')

    # Default to interactive mode if no args are provided
    parser.set_defaults(interactive=len(sys.argv) <= 1)
    args = parser.parse_args()

    # Create runtime directory for logs, database, and cache files
    RUNTIME_DIR.mkdir(exist_ok=True)
    
    # Configure logging now that runtime dir exists
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                       handlers=[logging.FileHandler(RUNTIME_DIR / 'mullvad_speed_test.log')])

    ui = DisplayManager(args.interactive)

    # Check required dependencies after parsing arguments
    missing_deps = check_dependencies()
    if missing_deps:
        ui.error("Missing dependencies detected:")
        for dep in missing_deps:
            ui.error(f"- {dep}")
        print("\nPlease install these dependencies before running the script.")
        if "speedtest-cli" in missing_deps:
            print("Install speedtest-cli: pip install speedtest-cli")
        if "mtr" in missing_deps:
            print("Install mtr: use your package manager")
        if "Mullvad VPN CLI" in missing_deps:
            print("Install Mullvad VPN from https://mullvad.net")
        sys.exit(1)

    # Print welcome message
    print_welcome(ui)

    # Check optional dependencies
    suggested_deps = check_optional_dependencies()
    if suggested_deps:
        ui.info("Recommended optional dependencies:")
        for dep in suggested_deps:
            print(f"- {dep}")
        print("")

    # Customize parameters in interactive mode
    if args.interactive:
        args = input_custom_parameters(args, ui)
        display_parameters_summary(args, ui, countdown_seconds=max(0, args.countdown_seconds))

    # Create tester and run tests
    tester = MullvadTester(
        reference_location=args.location, default_lat=args.default_lat, default_lon=args.default_lon,
        verbose=args.verbose, db_file=args.db, interactive=args.interactive,
        max_servers_hard_limit=args.max_servers_hard_limit, min_download_speed=args.min_download_speed,
        connection_timeout=args.connection_timeout, min_viable_servers=args.min_viable_servers,
        open_results_prompt=args.open_results,
        machine_readable=args.machine_readable
    )
    tester.run_tests(max_servers=args.max_servers, max_distance=args.max_distance)

if __name__ == "__main__":
    main()
