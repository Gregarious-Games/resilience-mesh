"""
Resilience-Mesh - Decentralized Agricultural Logistics
=======================================================

A resilient mesh network for rural cooperatives and disaster response.

Modules:
    safety_guard: Bidirectional multi-language safety dynamics
    safety_hardening: Enhanced protection (rate limiting, reputation)
    mesh_bridge: Main LoRa/Meshtastic bridge
    orbitdb_sync: P2P persistence layer
    starlink_bridge: Satellite uplink
    emergency_reset: Data protection system
    dashboard: Terminal monitoring interface
    low_power: Battery-aware optimization
"""

__version__ = "1.1.0"
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

# Optional imports (may not be needed in all deployments)
try:
    from .safety_hardening import (
        HardenedSafetyGuard,
        SafetyHardening,
        ReputationLevel,
    )
except ImportError:
    pass

try:
    from .dashboard import Dashboard, generate_text_report
except ImportError:
    pass

try:
    from .low_power import (
        LowPowerManager,
        PowerMode,
        quick_safety_check,
    )
except ImportError:
    pass

__all__ = [
    # Core classes
    "SafetyGuard",
    "ResilienceMeshBridge",

    # Enhanced classes
    "HardenedSafetyGuard",
    "SafetyHardening",
    "Dashboard",
    "LowPowerManager",

    # Enums
    "Direction",
    "Language",
    "ReputationLevel",
    "PowerMode",

    # Constants
    "PHI",
    "GAMMA",
    "CLAMP_HIGH",
    "CLAMP_LOW",
    "COMMODITY_CODES",
    "PANIC_CODES",

    # Utilities
    "generate_text_report",
    "quick_safety_check",
]
