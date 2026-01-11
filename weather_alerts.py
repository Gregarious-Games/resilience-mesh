"""
WEATHER & ALERT INTEGRATION
===========================
Pull weather forecasts and emergency alerts when online.

Features:
- OpenWeatherMap integration for local forecasts
- USGS earthquake/flood alerts
- Frost/heat warnings for crop protection
- Broadcast alerts to mesh network
- Offline caching for intermittent connectivity

Free tier friendly - minimal API calls.
"""

import time
import json
import os
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Optional HTTP library
try:
    import urllib.request
    import urllib.error
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

# OpenWeatherMap free tier: 1000 calls/day
OPENWEATHER_API = "https://api.openweathermap.org/data/2.5"
OPENWEATHER_ONECALL = "https://api.openweathermap.org/data/3.0/onecall"

# USGS Earthquake API (free, no key needed)
USGS_API = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# National Weather Service (US, free, no key needed)
NWS_API = "https://api.weather.gov"

# Cache settings
CACHE_DIR = "~/.resilience_mesh/weather_cache"
CACHE_DURATION = 1800  # 30 minutes


class AlertType(Enum):
    FROST = "frost"
    HEAT = "heat"
    RAIN = "rain"
    STORM = "storm"
    FLOOD = "flood"
    EARTHQUAKE = "earthquake"
    WIND = "wind"
    DROUGHT = "drought"
    GENERAL = "general"


class AlertSeverity(Enum):
    INFO = "info"           # Informational
    ADVISORY = "advisory"   # Be prepared
    WATCH = "watch"         # Conditions favorable
    WARNING = "warning"     # Imminent danger


@dataclass
class WeatherAlert:
    """Weather or emergency alert"""
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    action: str              # Recommended action
    timestamp: float
    expires: float = 0       # When alert expires
    source: str = "unknown"
    location: str = ""

    def to_broadcast(self, lang: str = "es") -> str:
        """Format for mesh broadcast"""
        icons = {
            AlertType.FROST: "FROST",
            AlertType.HEAT: "CALOR",
            AlertType.RAIN: "LLUVIA",
            AlertType.STORM: "TORMENTA",
            AlertType.FLOOD: "INUNDACION",
            AlertType.EARTHQUAKE: "SISMO",
            AlertType.WIND: "VIENTO",
            AlertType.DROUGHT: "SEQUIA",
            AlertType.GENERAL: "ALERTA",
        }
        icon = icons.get(self.alert_type, "ALERTA")
        return f"[{icon}] {self.title}: {self.action}"

    def to_dict(self) -> Dict:
        return {
            'type': self.alert_type.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'action': self.action,
            'timestamp': self.timestamp,
            'expires': self.expires,
            'source': self.source,
            'location': self.location
        }


# =============================================================================
# WEATHER SERVICE
# =============================================================================

class WeatherService:
    """
    Fetch weather data and generate agricultural alerts.

    Designed for intermittent connectivity:
    - Caches responses locally
    - Minimal API calls
    - Graceful offline fallback
    """

    def __init__(self,
                 api_key: str = None,
                 lat: float = None,
                 lon: float = None,
                 location_name: str = "Local"):

        self.api_key = api_key or os.environ.get("OPENWEATHER_API_KEY", "")
        self.lat = lat
        self.lon = lon
        self.location_name = location_name

        # Alert thresholds (Celsius)
        self.frost_threshold = 2.0      # Below this = frost warning
        self.heat_threshold = 35.0      # Above this = heat warning
        self.wind_threshold = 50.0      # km/h - strong wind
        self.rain_threshold = 20.0      # mm in 24h - heavy rain

        # Cache
        self.cache_dir = os.path.expanduser(CACHE_DIR)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache: Dict[str, Dict] = {}

        # Alert handlers
        self.alert_handlers: List[Callable] = []

        # Generated alerts
        self.active_alerts: List[WeatherAlert] = []

    def on_alert(self, handler: Callable):
        """Register alert handler"""
        self.alert_handlers.append(handler)

    def _trigger_alert(self, alert: WeatherAlert):
        """Trigger alert handlers"""
        self.active_alerts.append(alert)
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except:
                pass

    def _http_get(self, url: str, timeout: int = 10) -> Optional[Dict]:
        """Simple HTTP GET with JSON response"""
        if not HTTP_AVAILABLE:
            return None

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'ResilienceMesh/1.0'})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            print(f"[WEATHER] HTTP error: {e}")
            return None

    def _get_cached(self, key: str) -> Optional[Dict]:
        """Get from cache if fresh"""
        cache_file = os.path.join(self.cache_dir, f"{key}.json")

        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                if time.time() - data.get('_cached_at', 0) < CACHE_DURATION:
                    return data
            except:
                pass
        return None

    def _set_cached(self, key: str, data: Dict):
        """Save to cache"""
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        data['_cached_at'] = time.time()
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except:
            pass

    def fetch_weather(self) -> Optional[Dict]:
        """Fetch current weather from OpenWeatherMap"""
        if not self.api_key or not self.lat or not self.lon:
            return None

        # Check cache
        cache_key = f"weather_{self.lat}_{self.lon}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Fetch from API
        url = f"{OPENWEATHER_API}/weather?lat={self.lat}&lon={self.lon}&appid={self.api_key}&units=metric"
        data = self._http_get(url)

        if data:
            self._set_cached(cache_key, data)
            print(f"[WEATHER] Fetched weather for {self.location_name}")

        return data

    def fetch_forecast(self) -> Optional[Dict]:
        """Fetch 5-day forecast"""
        if not self.api_key or not self.lat or not self.lon:
            return None

        cache_key = f"forecast_{self.lat}_{self.lon}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        url = f"{OPENWEATHER_API}/forecast?lat={self.lat}&lon={self.lon}&appid={self.api_key}&units=metric"
        data = self._http_get(url)

        if data:
            self._set_cached(cache_key, data)

        return data

    def fetch_earthquakes(self, min_magnitude: float = 4.0, radius_km: float = 200) -> List[Dict]:
        """Fetch recent earthquakes from USGS"""
        if not self.lat or not self.lon:
            return []

        cache_key = f"earthquakes_{self.lat}_{self.lon}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached.get('features', [])

        # Last 24 hours
        url = (f"{USGS_API}?format=geojson"
               f"&latitude={self.lat}&longitude={self.lon}"
               f"&maxradiuskm={radius_km}"
               f"&minmagnitude={min_magnitude}"
               f"&starttime={datetime.utcnow().strftime('%Y-%m-%d')}")

        data = self._http_get(url)
        if data:
            self._set_cached(cache_key, data)
            return data.get('features', [])

        return []

    def analyze_weather(self, weather_data: Dict) -> List[WeatherAlert]:
        """Analyze weather data and generate agricultural alerts"""
        alerts = []
        now = time.time()

        if not weather_data:
            return alerts

        main = weather_data.get('main', {})
        wind = weather_data.get('wind', {})
        weather = weather_data.get('weather', [{}])[0]

        temp = main.get('temp', 20)
        feels_like = main.get('feels_like', temp)
        humidity = main.get('humidity', 50)
        wind_speed = wind.get('speed', 0) * 3.6  # m/s to km/h
        condition = weather.get('main', '').lower()

        # Frost warning
        if temp <= self.frost_threshold:
            alerts.append(WeatherAlert(
                alert_type=AlertType.FROST,
                severity=AlertSeverity.WARNING if temp <= 0 else AlertSeverity.ADVISORY,
                title=f"Helada: {temp:.1f}C",
                description=f"Temperatura bajo {self.frost_threshold}C",
                action="Proteger cultivos sensibles. Cubrir plantas.",
                timestamp=now,
                expires=now + 21600,  # 6 hours
                source="OpenWeatherMap",
                location=self.location_name
            ))

        # Heat warning
        if temp >= self.heat_threshold:
            alerts.append(WeatherAlert(
                alert_type=AlertType.HEAT,
                severity=AlertSeverity.WARNING if temp >= 40 else AlertSeverity.ADVISORY,
                title=f"Calor extremo: {temp:.1f}C",
                description=f"Temperatura sobre {self.heat_threshold}C",
                action="Regar temprano. Sombra para ganado. Hidratacion.",
                timestamp=now,
                expires=now + 21600,
                source="OpenWeatherMap",
                location=self.location_name
            ))

        # Wind warning
        if wind_speed >= self.wind_threshold:
            alerts.append(WeatherAlert(
                alert_type=AlertType.WIND,
                severity=AlertSeverity.WARNING if wind_speed >= 70 else AlertSeverity.ADVISORY,
                title=f"Viento fuerte: {wind_speed:.0f} km/h",
                description="Vientos fuertes esperados",
                action="Asegurar invernaderos. Proteger estructuras.",
                timestamp=now,
                expires=now + 10800,
                source="OpenWeatherMap",
                location=self.location_name
            ))

        # Storm warning
        if 'storm' in condition or 'thunder' in condition:
            alerts.append(WeatherAlert(
                alert_type=AlertType.STORM,
                severity=AlertSeverity.WARNING,
                title="Tormenta electrica",
                description=weather.get('description', 'Tormenta'),
                action="Refugiarse. No trabajar en campo abierto.",
                timestamp=now,
                expires=now + 7200,
                source="OpenWeatherMap",
                location=self.location_name
            ))

        return alerts

    def analyze_earthquakes(self, quakes: List[Dict]) -> List[WeatherAlert]:
        """Generate alerts from earthquake data"""
        alerts = []
        now = time.time()

        for quake in quakes:
            props = quake.get('properties', {})
            mag = props.get('mag', 0)
            place = props.get('place', 'Unknown')
            quake_time = props.get('time', 0) / 1000  # ms to s

            # Only recent quakes (last 6 hours)
            if now - quake_time > 21600:
                continue

            severity = AlertSeverity.INFO
            if mag >= 6.0:
                severity = AlertSeverity.WARNING
            elif mag >= 5.0:
                severity = AlertSeverity.WATCH
            elif mag >= 4.0:
                severity = AlertSeverity.ADVISORY

            alerts.append(WeatherAlert(
                alert_type=AlertType.EARTHQUAKE,
                severity=severity,
                title=f"Sismo M{mag:.1f}",
                description=f"Magnitud {mag:.1f} cerca de {place}",
                action="Verificar estructuras. Revisar almacenes.",
                timestamp=quake_time,
                expires=now + 3600,
                source="USGS",
                location=place
            ))

        return alerts

    def check_all(self) -> List[WeatherAlert]:
        """Run all checks and return alerts"""
        all_alerts = []

        # Weather
        weather = self.fetch_weather()
        if weather:
            all_alerts.extend(self.analyze_weather(weather))

        # Earthquakes
        quakes = self.fetch_earthquakes()
        all_alerts.extend(self.analyze_earthquakes(quakes))

        # Trigger handlers
        for alert in all_alerts:
            self._trigger_alert(alert)

        return all_alerts

    def get_broadcast_messages(self, lang: str = "es") -> List[str]:
        """Get all active alerts formatted for mesh broadcast"""
        return [alert.to_broadcast(lang) for alert in self.active_alerts]


# =============================================================================
# ALERT BROADCASTER
# =============================================================================

class AlertBroadcaster:
    """
    Integrate weather alerts with mesh bridge.

    Periodically checks for alerts and broadcasts to network.
    """

    def __init__(self,
                 weather_service: WeatherService,
                 bridge = None,
                 check_interval: int = 1800):  # 30 min

        self.weather = weather_service
        self.bridge = bridge
        self.check_interval = check_interval

        self.last_check = 0
        self.broadcast_alerts: List[str] = []  # Already broadcast
        self.running = False

    def check_and_broadcast(self):
        """Check for new alerts and broadcast"""
        alerts = self.weather.check_all()

        for alert in alerts:
            msg = alert.to_broadcast()

            # Don't repeat broadcasts
            if msg in self.broadcast_alerts:
                continue

            self.broadcast_alerts.append(msg)

            # Broadcast via bridge
            if self.bridge:
                print(f"[ALERT] Broadcasting: {msg}")
                # Use bridge's send method if available
                if hasattr(self.bridge, 'send_text'):
                    self.bridge.send_text(msg)

            # Keep broadcast history manageable
            if len(self.broadcast_alerts) > 100:
                self.broadcast_alerts = self.broadcast_alerts[-50:]

    def run_loop(self):
        """Run periodic alert checking"""
        self.running = True
        print(f"[ALERT] Starting alert broadcaster (interval: {self.check_interval}s)")

        try:
            while self.running:
                now = time.time()
                if now - self.last_check >= self.check_interval:
                    self.check_and_broadcast()
                    self.last_check = now

                time.sleep(60)  # Check every minute if time to run

        except KeyboardInterrupt:
            pass
        finally:
            self.running = False


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    print("="*70)
    print(" WEATHER & ALERT INTEGRATION TEST")
    print("="*70)

    # Demo without API key (will use cache/mock)
    service = WeatherService(
        lat=19.4326,   # Mexico City
        lon=-99.1332,
        location_name="Ciudad de Mexico"
    )

    # Manual alert creation for demo
    print("\n[Test 1] Alert Creation")
    test_alert = WeatherAlert(
        alert_type=AlertType.FROST,
        severity=AlertSeverity.WARNING,
        title="Helada: -2C",
        description="Temperatura bajo cero esperada",
        action="Proteger cultivos. Cubrir plantas sensibles.",
        timestamp=time.time(),
        source="Test"
    )
    print(f"  Alert: {test_alert.title}")
    print(f"  Broadcast: {test_alert.to_broadcast()}")

    # Mock weather analysis
    print("\n[Test 2] Weather Analysis")
    mock_weather = {
        'main': {'temp': 1.5, 'humidity': 85},
        'wind': {'speed': 15},  # m/s = 54 km/h
        'weather': [{'main': 'Clear', 'description': 'clear sky'}]
    }
    alerts = service.analyze_weather(mock_weather)
    for alert in alerts:
        print(f"  [{alert.severity.value}] {alert.title}")
        print(f"    Action: {alert.action}")

    # Mock earthquake
    print("\n[Test 3] Earthquake Alert")
    mock_quake = [{
        'properties': {
            'mag': 5.2,
            'place': '50km NE of Oaxaca',
            'time': time.time() * 1000  # Now
        }
    }]
    eq_alerts = service.analyze_earthquakes(mock_quake)
    for alert in eq_alerts:
        print(f"  [{alert.severity.value}] {alert.title}")
        print(f"    {alert.description}")

    # Broadcast format
    print("\n[Test 4] Broadcast Messages")
    service.active_alerts = alerts + eq_alerts
    for msg in service.get_broadcast_messages():
        print(f"  -> {msg}")

    print("\n" + "="*70)
    print(" To use with real data:")
    print(" export OPENWEATHER_API_KEY='your_key'")
    print(" service = WeatherService(api_key='...', lat=..., lon=...)")
    print("="*70)
