# Resilience-Mesh 🌱🛰️

> Red de logistica agricola descentralizada para cooperativas rurales y resiliencia ante desastres.

> Decentralized agricultural logistics network for rural cooperatives and disaster resilience.

[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Version](https://img.shields.io/badge/Version-1.1.0-orange)]()

## Vision / Vision

**English**: Building resilient agricultural communities through decentralized communication and transparent logistics. When disasters strike or infrastructure fails, communities need reliable ways to coordinate food distribution.

**Espanol**: Construyendo comunidades agricolas resilientes a traves de comunicacion descentralizada y logistica transparente. Cuando ocurren desastres o falla la infraestructura, las comunidades necesitan formas confiables de coordinar la distribucion de alimentos.

## Use Cases / Casos de Uso

### 🌾 Rural Cooperatives / Cooperativas Rurales
- Coordinate harvest sharing between farms
- Track seed and grain inventory across the network
- Enable peer-to-peer trading without central servers

### 🌪️ Disaster Resilience / Resiliencia ante Desastres
- Maintain communication when cell towers fail
- Coordinate emergency food distribution
- Sync data when satellite connectivity is intermittent

### 🤝 Transparent Agriculture / Agricultura Transparente
- Verifiable supply chain from farm to community
- Democratic inventory management
- Open audit trail via distributed ledger

## Architecture / Arquitectura

```
+---------------------------------------------------------------------+
|                    RESILIENCE-MESH ARCHITECTURE                      |
+---------------------------------------------------------------------+
|                                                                      |
|  +-------------+     LoRa/Meshtastic      +-------------+            |
|  |  Farm Node  |<------------------------>|  Farm Node  |            |
|  | (Cooperativa)|    Long-Range Radio     | (Cooperativa)|            |
|  +------+------+                           +------+------+            |
|         |                                         |                   |
|         |  +-----------------------------------+  |                   |
|         +->|      SAFETY GUARD LAYER          |<-+                   |
|            |   Multi-Language Protection      |                       |
|            |   (ES/EN/PT) Anti-Spam/Scam      |                       |
|            +----------------+-----------------+                       |
|                             |                                         |
|            +----------------v-----------------+                       |
|            |      OrbitDB / IPFS              |                       |
|            |   Distributed Ledger             |                       |
|            |   (Works Offline!)               |                       |
|            +----------------+-----------------+                       |
|                             |                                         |
|            +----------------v-----------------+                       |
|            |     SATELLITE BRIDGE             |                       |
|            |   Urban-Rural Sync               |                       |
|            |   (Starlink/VSAT)                |                       |
|            +----------------------------------+                       |
|                                                                      |
+----------------------------------------------------------------------+
```

## Features / Caracteristicas

### 1. 📡 Long-Range Communication
- **LoRa/Meshtastic**: 10+ km range without cellular infrastructure
- **Mesh Topology**: Messages relay through multiple nodes
- **Low Power**: Solar-powered nodes for remote areas

### 2. 🛡️ Safety Guard (Multi-Language)
- **Spam/Scam Detection**: Protects against fraudulent messages
- **Multi-Language**: Spanish, English, Portuguese
- **Bidirectional**: Monitors incoming and outgoing messages
- **Hardened**: Rate limiting, sender reputation, blocklist

| Signal Type | Description |
|-------------|-------------|
| spam | Unwanted bulk messages |
| scam | Fraudulent attempts |
| urgency_abuse | False emergency pressure |
| impersonation | Fake identity claims |

### 3. 📦 Inventory Protocol

Simple codes for agricultural products:

| Code | Product | Category |
|------|---------|----------|
| A1 | White Corn / Maiz Blanco | Grain |
| A2 | Blue Corn / Maiz Azul | Grain |
| B1 | Black Beans / Frijoles Negros | Legume |
| B2 | Red Beans / Frijoles Rojos | Legume |
| C1 | Wheat / Trigo | Cereal |
| C2 | Rice / Arroz | Cereal |
| S1 | Soy / Soya | Legume |
| V1 | Tomato Seeds | Vegetable |

**Example**: `"Disponible: A1:100, B1:50"` = 100kg white corn, 50kg black beans

### 4. 💾 Distributed Storage
- **OrbitDB/IPFS**: No central server to fail
- **Merkle-CRDT**: Automatic conflict resolution
- **Offline-First**: Works without internet, syncs when available

### 5. 🛰️ Satellite Bridge
- **Starlink Integration**: Connect remote farms to urban markets
- **Encrypted Sync**: Secure data transmission
- **Automatic Retry**: Handles intermittent connectivity

### 6. 🌤️ Weather & Alert Integration (NEW in v1.1)
- **OpenWeatherMap**: Frost, heat, storm warnings
- **USGS Earthquakes**: Seismic alerts for disaster-prone areas
- **Broadcast to Mesh**: Automatic alert distribution

### 7. 🗳️ Governance Lite (NEW in v1.1)
- **Proposals**: Trade, resource allocation, membership
- **Voting**: Quorum-based democratic decisions
- **Signed Votes**: Tamper-proof on OrbitDB ledger

### 8. 📊 Dashboard & Monitoring (NEW in v1.1)
- **Terminal Dashboard**: Real-time network status
- **Activity Log**: Message and inventory tracking
- **Safety Visualization**: Risk levels and alerts

### 9. 🔋 Low-Power Optimization (NEW in v1.1)
- **Power Modes**: FULL, BALANCED, LOW_POWER, ULTRA_LOW
- **Battery-Aware**: Auto-switches based on charge level
- **Message Batching**: Efficient processing for solar nodes

### 10. 🔄 Interoperability (NEW in v1.1)
- **CSV Export**: FarmOS-compatible inventory export
- **MQTT Gateway**: LoRaWAN and IoT integration
- **JSON API**: Custom system integration

---

## Hardware Guide / Guia de Hardware

### Recommended Setup (~$50-80 USD)

| Component | Recommendation | Price |
|-----------|---------------|-------|
| Board | **LilyGo T-Beam v1.1** (ESP32 + LoRa + GPS) | ~$35 |
| Solar Panel | 6W 5V panel with USB output | ~$15 |
| Battery | 18650 Li-ion 3000mAh (included with T-Beam) | - |
| Enclosure | IP65 waterproof junction box | ~$10 |
| Antenna | 868/915MHz LoRa antenna (region-specific) | ~$5 |

### Alternative Boards

| Board | Pros | Cons | Price |
|-------|------|------|-------|
| **Heltec LoRa32 V3** | Cheap, OLED display | No GPS, smaller battery | ~$20 |
| **RAK WisBlock** | Modular, industrial | More expensive | ~$50+ |
| **TTGO T-Deck** | Built-in keyboard | Overkill for nodes | ~$60 |

### Solar Power Sizing

For 24/7 operation in moderate sun:
```
Node consumption:  ~50mA average (with sleep)
Daily usage:       50mA x 24h = 1200mAh
Solar input:       6W panel = ~1000mA peak
Battery backup:    3000mAh = ~2.5 days without sun
```

### Enclosure Options

1. **DIY**: IP65 junction box + cable glands (~$10)
2. **3D Printed**: Search Thingiverse for "T-Beam enclosure"
3. **Commercial**: Meshtastic-specific cases from Etsy/AliExpress

### Flashing Meshtastic

```bash
# Install Meshtastic flasher
pip install meshtastic

# Flash firmware (auto-detects board)
meshtastic --flash

# Configure for resilience-mesh
meshtastic --set lora.region US   # or EU_868, etc.
meshtastic --set position.gps_enabled false  # Privacy
meshtastic --ch-set name "RESILIENCE" --ch-index 0
```

### Related Projects
- [Meshtastic](https://meshtastic.org) - LoRa mesh firmware
- [Disaster.Radio](https://disaster.radio) - Solar mesh nodes
- [LoRa Alliance](https://lora-alliance.org) - LoRaWAN specs

---

## Installation / Instalacion

```bash
git clone https://github.com/Gregarious-Games/resilience-mesh.git
cd resilience-mesh
pip install -r requirements.txt
```

### Optional Dependencies
```bash
# For Meshtastic hardware
pip install meshtastic

# For distributed storage
npm install orbit-db ipfs-core

# For satellite bridge & weather
pip install paho-mqtt python-gnupg requests

# For MQTT gateway
pip install paho-mqtt
```

## Quick Start / Inicio Rapido

### Basic Usage
```python
from safety_guard import SafetyGuard, Direction, Language
from mesh_bridge import ResilienceMeshBridge

# Initialize
bridge = ResilienceMeshBridge(
    primary_language=Language.SPANISH,
    use_meshtastic=False  # True for real hardware
)

# Register handlers
@bridge.on_inventory
def handle_inventory(sender, code, qty, commodity):
    print(f"Received: {commodity['name']} x{qty}kg from {sender}")

# Process message
bridge.process_inbound("Disponible: A1:100, B1:50", sender_id="farm_001")
```

### With Hardened Safety
```python
from safety_hardening import HardenedSafetyGuard

guard = HardenedSafetyGuard(
    rate_limit=True,      # Prevent spam floods
    reputation=True,      # Track sender trustworthiness
    dedup=True           # Catch duplicate messages
)

result = guard.process_message(message, Direction.INBOUND, sender_id="peer_001")
```

### Low-Power Mode
```python
from low_power import LowPowerManager, PowerMode

manager = LowPowerManager(initial_mode=PowerMode.BALANCED)

# Queue messages for batched processing
manager.queue_message("A1:100", sender_id="farm_001")

# Process when ready
results = manager.process_batch()
```

### Weather Alerts
```python
from weather_alerts import WeatherService

weather = WeatherService(
    api_key="your_openweathermap_key",
    lat=19.4326, lon=-99.1332,
    location_name="Mexico City"
)

alerts = weather.check_all()
for alert in alerts:
    print(f"[{alert.severity.value}] {alert.title}: {alert.action}")
```

### Governance Voting
```python
from governance import GovernanceEngine, ProposalType, VoteChoice

gov = GovernanceEngine(node_id="farm_001", member_list=["farm_001", "farm_002", "coop_001"])

# Create trade proposal
proposal = gov.create_trade_proposal(
    offer={'A1': 50},
    request={'C2': 30}
)
gov.submit_proposal(proposal.proposal_id)

# Vote
gov.vote(proposal.proposal_id, VoteChoice.YES)
```

### Run Tests
```bash
python test_scenarios.py      # Core tests
python safety_hardening.py    # Hardening tests
python simulator.py           # Network simulation
python governance.py          # Governance tests
```

### Run Simulator (50+ nodes)
```python
from simulator import MeshSimulator

sim = MeshSimulator()
sim.create_network(num_farms=30, num_coops=4, num_relays=8)
sim.simulate_dropout(dropout_rate=0.2)

results = sim.run_stress_test(message_count=1000)
print(f"Delivery rate: {results['delivery_rate']:.1%}")
```

---

## Module Overview

| Module | Description |
|--------|-------------|
| `safety_guard.py` | Bidirectional multi-language safety detection |
| `safety_hardening.py` | Rate limiting, reputation, blocklist |
| `mesh_bridge.py` | Main LoRa/Meshtastic bridge |
| `orbitdb_sync.py` | P2P persistence with Merkle-CRDT |
| `starlink_bridge.py` | Satellite uplink for urban sync |
| `emergency_reset.py` | Data protection system |
| `dashboard.py` | Terminal monitoring interface |
| `low_power.py` | Battery-aware optimization |
| `weather_alerts.py` | Weather and emergency alerts |
| `governance.py` | Voting and proposal system |
| `simulator.py` | Multi-node network simulation |
| `interop.py` | CSV/MQTT/JSON integration |

---

## Mathematical Foundation

The safety system uses constants derived from the Golden Ratio:

```python
PHI   = 1.6180339887498949     # Golden ratio
GAMMA = 1/(6*PHI) = 0.103      # Stability constant

# Thresholds
ALERT_HIGH = 1 - GAMMA = 0.897  # Mandatory intervention
ALERT_LOW  = GAMMA = 0.103      # Minimum baseline
```

**Asymmetric memory**: Safety concerns decay slowly, risk responds quickly.

---

## Roadmap / Hoja de Ruta

- [x] Multi-language safety detection (ES/EN/PT)
- [x] Weather alert integration
- [x] Network simulator (50+ nodes)
- [x] Governance voting system
- [x] Low-power optimization
- [x] FarmOS CSV export
- [ ] Mobile app (React Native / Flutter)
- [ ] Voice message support
- [ ] LoRaWAN gateway bridge
- [ ] Field testing framework
- [ ] Anonymous metrics collection (opt-in)

---

## Contributing / Contribuir

We welcome contributions! Priority areas:

- 🌍 **Translations**: More languages for rural communities
- 📱 **Mobile App**: React Native or Flutter interface
- 🔧 **Hardware**: Solar-powered node designs and testing
- 📊 **Field Testing**: Real-world deployment metrics
- 🧪 **Simulation**: More network scenarios

---

## Community / Comunidad

This project is built for and with rural communities. We believe in:

- **Transparency**: Open source, open data, open governance
- **Resilience**: Systems that work when infrastructure fails
- **Cooperation**: Technology that strengthens communities
- **Dignity**: Every farmer deserves reliable communication

---

## License / Licencia

MIT License - Free to use, modify, and distribute.

See [LICENSE](LICENSE) for details.

---

## Acknowledgments / Agradecimientos

- Meshtastic community for LoRa protocol
- OrbitDB/IPFS for distributed storage
- OpenWeatherMap for weather data
- Rural cooperatives who inspired this work
- All contributors to agricultural resilience

---

**"Connecting farms, building resilience, feeding communities."**

**"Conectando granjas, construyendo resiliencia, alimentando comunidades."**

🌱🛰️
