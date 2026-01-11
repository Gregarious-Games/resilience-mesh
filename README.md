# Resilience-Mesh 🌱🛰️

> Red de logística agrícola descentralizada para cooperativas rurales y resiliencia ante desastres.

> Decentralized agricultural logistics network for rural cooperatives and disaster resilience.

[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)

## Vision / Visión

**English**: Building resilient agricultural communities through decentralized communication and transparent logistics. When disasters strike or infrastructure fails, communities need reliable ways to coordinate food distribution.

**Español**: Construyendo comunidades agrícolas resilientes a través de comunicación descentralizada y logística transparente. Cuando ocurren desastres o falla la infraestructura, las comunidades necesitan formas confiables de coordinar la distribución de alimentos.

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
┌─────────────────────────────────────────────────────────────────┐
│                    RESILIENCE-MESH ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     LoRa/Meshtastic      ┌─────────────┐      │
│  │  Farm Node  │◄─────────────────────────►│  Farm Node  │      │
│  │ (Cooperativa)│    Long-Range Radio     │ (Cooperativa)│      │
│  └──────┬──────┘                           └──────┬──────┘      │
│         │                                         │             │
│         │  ┌─────────────────────────────────┐   │             │
│         └──►│      SAFETY GUARD LAYER        │◄──┘             │
│             │   Multi-Language Protection    │                  │
│             │   (ES/EN/PT) Anti-Spam/Scam    │                  │
│             └───────────────┬───────────────┘                  │
│                             │                                   │
│             ┌───────────────▼───────────────┐                  │
│             │      OrbitDB / IPFS           │                  │
│             │   Distributed Ledger          │                  │
│             │   (Works Offline!)            │                  │
│             └───────────────┬───────────────┘                  │
│                             │                                   │
│             ┌───────────────▼───────────────┐                  │
│             │     SATELLITE BRIDGE          │                  │
│             │   Urban-Rural Sync            │                  │
│             │   (Starlink/VSAT)             │                  │
│             └───────────────────────────────┘                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Features / Características

### 1. 📡 Long-Range Communication / Comunicación de Largo Alcance
- **LoRa/Meshtastic**: 10+ km range without cellular infrastructure
- **Mesh Topology**: Messages relay through multiple nodes
- **Low Power**: Solar-powered nodes for remote areas

### 2. 🛡️ Safety Guard (Multi-Language)
- **Spam/Scam Detection**: Protects against fraudulent messages
- **Multi-Language**: Spanish, English, Portuguese
- **Bidirectional**: Monitors incoming and outgoing messages
- **Mathematical Foundation**: PHI (1.618), GAMMA (0.103) for stable detection

| Signal Type | Description |
|-------------|-------------|
| spam | Unwanted bulk messages |
| scam | Fraudulent attempts |
| urgency_abuse | False emergency pressure |
| impersonation | Fake identity claims |

### 3. 📦 Inventory Protocol / Protocolo de Inventario

Simple codes for agricultural products:

| Code | Product / Producto | Category / Categoría |
|------|-------------------|---------------------|
| A1 | White Corn / Maíz Blanco | Grain / Grano |
| A2 | Blue Corn / Maíz Azul | Grain / Grano |
| B1 | Black Beans / Frijoles Negros | Legume / Legumbre |
| B2 | Red Beans / Frijoles Rojos | Legume / Legumbre |
| C1 | Wheat / Trigo | Cereal |
| C2 | Rice / Arroz | Cereal |
| S1 | Soy / Soya | Legume / Legumbre |
| V1 | Tomato Seeds / Semillas Tomate | Vegetable / Hortaliza |

**Example message**: `"Disponible: A1:100, B1:50"` = 100kg white corn, 50kg black beans

### 4. 💾 Distributed Storage / Almacenamiento Distribuido
- **OrbitDB/IPFS**: No central server to fail
- **Merkle-CRDT**: Automatic conflict resolution
- **Offline-First**: Works without internet, syncs when available

### 5. 🛰️ Satellite Bridge / Puente Satelital
- **Starlink Integration**: Connect remote farms to urban markets
- **Encrypted Sync**: Secure data transmission
- **Automatic Retry**: Handles intermittent connectivity

### 6. 🔄 Emergency Reset / Reinicio de Emergencia
- **Data Protection**: Secure deletion when devices are lost/stolen
- **Configurable**: Choose what data to protect
- **Verification**: Prevents accidental triggers

## Installation / Instalación

```bash
git clone https://github.com/YOUR_REPO/resilience-mesh.git
cd resilience-mesh
pip install -r requirements.txt
```

### Optional / Opcional
```bash
# For Meshtastic hardware
pip install meshtastic

# For distributed storage
npm install orbit-db ipfs-core

# For satellite bridge
pip install paho-mqtt python-gnupg
```

## Quick Start / Inicio Rápido

### Python Example
```python
from safety_guard import SafetyGuard, Direction, Language
from mesh_bridge import ResilienceMeshBridge

# Initialize / Inicializar
bridge = ResilienceMeshBridge(
    primary_language=Language.SPANISH,
    use_meshtastic=False  # True for real hardware
)

# Register inventory handler / Registrar manejador de inventario
@bridge.on_inventory
def handle_inventory(sender, code, qty, commodity):
    print(f"📦 {sender}: {commodity['name']} x{qty}kg")

# Process message / Procesar mensaje
bridge.process_inbound("Disponible: A1:100, B1:50", sender_id="farm_001")
```

### Run Tests / Ejecutar Pruebas
```bash
python test_scenarios.py
```

## Mathematical Foundation / Fundamento Matemático

The safety system uses constants derived from the Golden Ratio:

```python
PHI   = 1.6180339887498949     # Golden ratio / Proporción áurea
GAMMA = 1/(6*PHI) = 0.103      # Stability constant / Constante de estabilidad

# Thresholds / Umbrales
ALERT_HIGH = 1 - GAMMA = 0.897  # High alert threshold
ALERT_LOW  = GAMMA = 0.103      # Minimum baseline
```

These create **asymmetric memory**:
- Safety concerns decay slowly (persistent protection)
- Normal messages process quickly (responsive system)

## Contributing / Contribuir

We welcome contributions! Areas where help is needed:

- 🌍 **Translations**: More languages for rural communities
- 📱 **Mobile App**: React Native or Flutter interface
- 🔧 **Hardware**: Solar-powered node designs
- 📊 **Analytics**: Dashboard for cooperatives
- 🧪 **Testing**: More test scenarios

## Roadmap / Hoja de Ruta

- [ ] Mobile app for farmers / App móvil para agricultores
- [ ] Integration with agricultural markets / Integración con mercados agrícolas
- [ ] Weather alert system / Sistema de alertas meteorológicas
- [ ] Multilingual voice messages / Mensajes de voz multilingües
- [ ] Solar node hardware design / Diseño de nodo solar

## Community / Comunidad

This project is built for and with rural communities. We believe in:

- **Transparency**: Open source, open data, open governance
- **Resilience**: Systems that work when infrastructure fails
- **Cooperation**: Technology that strengthens communities
- **Dignity**: Every farmer deserves reliable communication

## License / Licencia

MIT License - Free to use, modify, and distribute.

See [LICENSE](LICENSE) for details.

## Acknowledgments / Agradecimientos

- Meshtastic community for LoRa protocol
- OrbitDB/IPFS for distributed storage
- Rural cooperatives who inspired this work
- All contributors to agricultural resilience

---

**"Connecting farms, building resilience, feeding communities."**

**"Conectando granjas, construyendo resiliencia, alimentando comunidades."**

🌱🛰️
