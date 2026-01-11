"""
Resilience-Mesh - Decentralized Agricultural Logistics
=======================================================

A resilient mesh network for rural cooperatives and disaster response.

Modules:
    safety_guard: Bidirectional multi-language safety dynamics
    mesh_bridge: Main LoRa/Meshtastic bridge
    orbitdb_sync: P2P persistence layer
    starlink_bridge: Satellite uplink
    emergency_reset: Data protection system
"""

__version__ = "1.0.0"
__author__ = "Resilience-Mesh Contributors"
__license__ = "MIT"

from .safety_guard import (
    SafetyGuard,
    Direction,
    Language,
    PHI,
    GAMMA,
    CLAMP_HIGH,
    CLAMP_LOW,
)

from .mesh_bridge import (
    ResilienceMeshBridge,
    COMMODITY_CODES,
    PANIC_CODES,
)

__all__ = [
    # Core classes
    "SafetyGuard",
    "ResilienceMeshBridge",

    # Enums
    "Direction",
    "Language",

    # Constants
    "PHI",
    "GAMMA",
    "CLAMP_HIGH",
    "CLAMP_LOW",
    "COMMODITY_CODES",
    "PANIC_CODES",
]
