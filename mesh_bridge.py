"""
RESILIENCE-MESH BRIDGE v1.1
===========================
Meshtastic LoRa bridge with integrated bidirectional safety dynamics.

Features:
- GPS configuration for privacy
- Codified inventory protocol (alphanumeric commodities)
- Bidirectional safety monitoring (inbound + outbound)
- Multi-language spam/scam detection
- Emergency reset for data protection
- OrbitDB sidecar integration (P2P persistence with Merkle-CRDT)
- Starlink bridge for urban-rural synchronization

Built for rural cooperatives and disaster resilience.
"""

import os
import sys
import json
import time
import threading
import hashlib
import secrets
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

# Import safety dynamics
from safety_guard import (
    SafetyGuard,
    Direction,
    Language,
    CLAMP_HIGH
)

# Import enhanced modules
try:
    from orbitdb_sync import OrbitDBSync
    ORBITDB_AVAILABLE = True
except ImportError:
    ORBITDB_AVAILABLE = False

try:
    from starlink_bridge import StarlinkBridge, StarlinkMonitor
    STARLINK_AVAILABLE = True
except ImportError:
    STARLINK_AVAILABLE = False

try:
    from emergency_reset import KillSwitch, KillMode, PanicCodeVerifier
    EMERGENCY_RESET_AVAILABLE = True
except ImportError:
    EMERGENCY_RESET_AVAILABLE = False

# =============================================================================
# CONFIGURATION
# =============================================================================

# Inventory code mapping
COMMODITY_CODES = {
    'A1': {'name': 'Maiz Blanco Natural', 'category': 'Grano Basico', 'name_en': 'Natural White Corn'},
    'A2': {'name': 'Maiz Azul Criollo', 'category': 'Grano Basico', 'name_en': 'Heirloom Blue Corn'},
    'A3': {'name': 'Maiz Amarillo', 'category': 'Grano Basico', 'name_en': 'Yellow Corn'},
    'B1': {'name': 'Caraotas Negras', 'category': 'Legumbre', 'name_en': 'Black Beans'},
    'B2': {'name': 'Frijoles Rojos', 'category': 'Legumbre', 'name_en': 'Red Beans'},
    'B3': {'name': 'Lentejas', 'category': 'Legumbre', 'name_en': 'Lentils'},
    'C1': {'name': 'Trigo Integral', 'category': 'Cereal', 'name_en': 'Whole Wheat'},
    'C2': {'name': 'Arroz Paddy', 'category': 'Cereal', 'name_en': 'Paddy Rice'},
    'C3': {'name': 'Trigo Rojo Montana', 'category': 'Cereal', 'name_en': 'Mountain Red Wheat'},
    'S1': {'name': 'Soya No-GMO', 'category': 'Legumbre', 'name_en': 'Non-GMO Soy'},
    'S2': {'name': 'Semillas Girasol', 'category': 'Oleaginosa', 'name_en': 'Sunflower Seeds'},
    'V1': {'name': 'Semillas Tomate', 'category': 'Hortaliza', 'name_en': 'Tomato Seeds'},
    'V2': {'name': 'Semillas Pimenton', 'category': 'Hortaliza', 'name_en': 'Pepper Seeds'},
}

# Panic codes that trigger kill switch
PANIC_CODES = ['XKILL', 'PANIC99', 'BORRAR']

# OrbitDB sidecar configuration
ORBITDB_API = "http://127.0.0.1:3000"

# Paths to sanitize on emergency reset
SENSITIVE_PATHS = [
    "~/.orbitdb",
    "~/.resilience_gpg",
    "~/.resilience_mesh",
    "~/.config/meshtastic"
]


# =============================================================================
# STEALTH CONFIGURATION
# =============================================================================

class StealthConfig:
    """GPS and position sanitization settings"""

    @staticmethod
    def get_stealth_settings() -> Dict:
        """Return settings to disable all location tracking"""
        return {
            'position': {
                'gps_mode': 0,  # DISABLED
                'fixed_position': False,
                'smart_broadcast': False,
                'broadcast_interval': 0,
            },
            'device': {
                'triple_click_disabled': True,
            }
        }

    @staticmethod
    def apply_to_node(interface, verbose: bool = True):
        """Apply stealth settings to Meshtastic node"""
        try:
            local_node = interface.getNode('^local')

            # Disable GPS
            local_node.localConfig.position.gps_mode = 0
            local_node.localConfig.position.fixed_position = False
            local_node.localConfig.position.smart_broadcast = False
            local_node.localConfig.position.broadcast_interval = 0

            # Disable hardware GPS trigger
            local_node.localConfig.device.triple_click_disabled = True

            # Write configs
            interface.writeConfig("position")
            interface.writeConfig("device")

            if verbose:
                print("[STEALTH] GPS disabled, position broadcast disabled")
            return True
        except Exception as e:
            print(f"[STEALTH] Failed to apply config: {e}")
            return False


# =============================================================================
# EMERGENCY RESET (Legacy fallback - use emergency_reset.py for full functionality)
# =============================================================================

class LegacyEmergencyReset:
    """Basic emergency reset fallback when emergency_reset.py not available"""

    @staticmethod
    def execute(paths: list = None, exit_after: bool = True) -> Dict:
        """Execute basic emergency reset"""
        paths = paths or SENSITIVE_PATHS
        total_erased = 0

        print("[RESET] *** EMERGENCY RESET ACTIVATED ***")

        for path in paths:
            expanded = os.path.expanduser(path)
            try:
                if os.path.isdir(expanded):
                    import shutil
                    shutil.rmtree(expanded, ignore_errors=True)
                    total_erased += 1
                elif os.path.isfile(expanded):
                    os.remove(expanded)
                    total_erased += 1
            except:
                pass

        if exit_after:
            os._exit(1)

        return {'status': 'SANITIZED', 'files_erased': total_erased}


# =============================================================================
# MESH BRIDGE
# =============================================================================

class ResilienceMeshBridge:
    """
    Main bridge between Meshtastic LoRa and P2P database layer.

    Integrates bidirectional safety monitoring for all communications.
    Now with OrbitDB sync, Starlink bridge, and emergency reset.
    """

    def __init__(self,
                 node_id: str = None,
                 primary_language: Language = Language.SPANISH,
                 use_meshtastic: bool = False,
                 use_orbitdb: bool = True,
                 use_starlink: bool = False,
                 admin_key_id: str = None,
                 urban_key_id: str = None,
                 state_dir: str = "~/.resilience_mesh"):

        self.state_dir = os.path.expanduser(state_dir)
        os.makedirs(self.state_dir, exist_ok=True)

        # Generate or load node ID
        self.node_id = node_id or self._get_or_create_node_id()

        # Initialize safety dynamics
        self.guard = SafetyGuard(
            node_id=self.node_id,
            primary_language=primary_language,
            state_file=os.path.join(self.state_dir, "safety_state.json")
        )

        # Meshtastic interface (optional for testing)
        self.interface = None
        self.use_meshtastic = use_meshtastic

        # OrbitDB sync layer
        self.orbitdb = None
        if use_orbitdb and ORBITDB_AVAILABLE:
            self.orbitdb = OrbitDBSync(node_id=self.node_id)
            self.orbitdb.start_background_sync(interval=60)
            print("[BRIDGE] OrbitDB sync enabled")

        # Starlink bridge for urban sync
        self.starlink = None
        if use_starlink and STARLINK_AVAILABLE and urban_key_id:
            self.starlink = StarlinkBridge(
                node_id=self.node_id,
                urban_key_id=urban_key_id
            )
            self.starlink.start()
            print("[BRIDGE] Starlink bridge enabled")

        # Emergency reset with signed panic codes
        self.emergency_reset = None
        if EMERGENCY_RESET_AVAILABLE:
            self.emergency_reset = KillSwitch(
                admin_key_id=admin_key_id,
                gnupghome=os.path.join(self.state_dir, "gpg"),
                exit_after=True
            )
            print(f"[BRIDGE] Emergency reset armed (admin_key: {'configured' if admin_key_id else 'none'})")

        # Message handlers
        self.inventory_handlers: List[Callable] = []
        self.alert_handlers: List[Callable] = []

        # Running state
        self.running = False
        self._lock = threading.Lock()

        # Inventory cache
        self.local_inventory: Dict[str, int] = {}
        self.network_inventory: Dict[str, Dict] = {}

        print(f"[BRIDGE] Initialized node: {self.node_id}")
        print(f"[BRIDGE] Primary language: {primary_language.value}")

    def _get_or_create_node_id(self) -> str:
        """Get existing node ID or create new one"""
        id_file = os.path.join(self.state_dir, "node_id")
        if os.path.exists(id_file):
            with open(id_file, 'r') as f:
                return f.read().strip()

        # Generate new ID
        node_id = hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:16]
        with open(id_file, 'w') as f:
            f.write(node_id)
        return node_id

    def connect_meshtastic(self, port: str = None) -> bool:
        """Connect to Meshtastic device"""
        if not self.use_meshtastic:
            print("[BRIDGE] Meshtastic disabled, running in simulation mode")
            return False

        try:
            import meshtastic
            import meshtastic.serial_interface
            from pubsub import pub

            if port:
                self.interface = meshtastic.serial_interface.SerialInterface(port)
            else:
                self.interface = meshtastic.serial_interface.SerialInterface()

            # Apply stealth configuration
            StealthConfig.apply_to_node(self.interface)

            # Subscribe to incoming messages
            pub.subscribe(self._on_meshtastic_receive, "meshtastic.receive")

            print("[BRIDGE] Connected to Meshtastic device")
            return True

        except ImportError:
            print("[BRIDGE] Meshtastic library not installed")
            return False
        except Exception as e:
            print(f"[BRIDGE] Failed to connect: {e}")
            return False

    def _on_meshtastic_receive(self, packet, interface):
        """Handle incoming Meshtastic packet"""
        try:
            decoded = packet.get('decoded', {})
            portnum = decoded.get('portnum', '')
            payload = decoded.get('payload', b'')

            if isinstance(payload, bytes):
                payload = payload.decode('utf-8', errors='ignore')

            sender = packet.get('fromId', packet.get('from', 'unknown'))

            # Process through safety check
            self.process_inbound(payload, sender_id=sender)

        except Exception as e:
            print(f"[BRIDGE] Packet processing error: {e}")

    def process_inbound(self, message: str, sender_id: str = "unknown",
                        signature: str = None) -> Dict:
        """
        Process incoming message through safety dynamics.

        Returns safety result and triggers handlers if safe.
        """
        with self._lock:
            # Check for panic codes with emergency reset
            if self.emergency_reset:
                panic_code = self.emergency_reset.check_panic_in_message(message)
                if panic_code:
                    print(f"[BRIDGE] EMERGENCY CODE DETECTED: {panic_code}")
                    # Use signed verification if configured
                    report = self.emergency_reset.trigger(
                        panic_code,
                        signature=signature,
                        mode=KillMode.STANDARD
                    )
                    if report:
                        return {'status': 'RESET', 'report': report}
                    else:
                        print("[BRIDGE] Emergency verification failed - ignoring")
            else:
                # Fallback to basic panic check
                for panic in PANIC_CODES:
                    if panic in message.upper():
                        print(f"[BRIDGE] EMERGENCY CODE DETECTED (legacy): {panic}")
                        LegacyEmergencyReset.execute()
                        return {'status': 'RESET'}

            # Safety analysis
            result = self.guard.process_message(
                text=message,
                direction=Direction.INBOUND,
                language=Language.AUTO,
                metadata={'sender_id': sender_id}
            )

            # Log
            level = result['level']
            risk = result['channel']['risk']
            print(f"[IN] [{sender_id[:8]}] Risk:{risk:.2f} Level:{level} - {message[:40]}...")

            # Handle based on result
            if result['handoff']:
                self._trigger_alert(result, message, sender_id)
                counter = self.guard.get_counter_speech()
                print(f"[ALERT] Counter-speech: {counter}")

            elif level == "LOW":
                # Safe - check for inventory codes
                self._parse_inventory(message, sender_id)

            return result

    def process_outbound(self, message: str) -> Dict:
        """
        Process outgoing message through safety dynamics.

        Checks if local node might be compromised/manipulated.
        """
        with self._lock:
            result = self.guard.process_message(
                text=message,
                direction=Direction.OUTBOUND,
                language=Language.AUTO
            )

            level = result['level']
            risk = result['channel']['risk']

            if result['handoff']:
                print(f"[OUT] BLOCKED - Local node may be compromised! Risk:{risk:.2f}")
                return {**result, 'blocked': True}

            print(f"[OUT] Risk:{risk:.2f} Level:{level} - {message[:40]}...")
            return {**result, 'blocked': False}

    def _parse_inventory(self, message: str, sender_id: str):
        """Parse inventory codes from message and sync to P2P layer"""
        import re

        # Match inventory pattern: CODE:QUANTITY (e.g., A1:50, B1:100)
        pattern = r'\b([A-Z][0-9])[:=](\d+)\b'
        matches = re.findall(pattern, message.upper())

        for code, quantity in matches:
            if code in COMMODITY_CODES:
                commodity = COMMODITY_CODES[code]
                qty = int(quantity)

                # Update network inventory
                if sender_id not in self.network_inventory:
                    self.network_inventory[sender_id] = {}
                self.network_inventory[sender_id][code] = {
                    'quantity': qty,
                    'commodity': commodity,
                    'timestamp': time.time()
                }

                print(f"[INV] {sender_id[:8]}: {commodity['name']} x{qty}")

                # Sync to OrbitDB (Merkle-CRDT distributed ledger)
                if self.orbitdb:
                    self.orbitdb.add_inventory(
                        commodity_code=code,
                        quantity=qty,
                        metadata={
                            'source_node': sender_id,
                            'commodity_name': commodity['name']
                        }
                    )

                # Queue for Starlink sync to urban
                if self.starlink:
                    self.starlink.add_delta({
                        'type': 'inventory_update',
                        'source': sender_id,
                        'code': code,
                        'quantity': qty,
                        'commodity': commodity['name']
                    })

                # Notify handlers
                for handler in self.inventory_handlers:
                    try:
                        handler(sender_id, code, qty, commodity)
                    except:
                        pass

    def _trigger_alert(self, result: Dict, message: str, sender_id: str):
        """Trigger alert handlers"""
        alert = {
            'type': 'MANIPULATION_DETECTED',
            'sender_id': sender_id,
            'message': message,
            'risk': result['channel']['risk'],
            'flags': result['flags'],
            'language': result['language'],
            'timestamp': time.time()
        }

        for handler in self.alert_handlers:
            try:
                handler(alert)
            except:
                pass

    def send_inventory(self, code: str, quantity: int) -> Dict:
        """Send inventory availability to mesh"""
        if code not in COMMODITY_CODES:
            return {'error': f'Unknown code: {code}'}

        message = f"{code}:{quantity}"

        # Safety check outbound
        result = self.process_outbound(message)
        if result.get('blocked'):
            return {'error': 'Message blocked by safety dynamics', 'result': result}

        # Send via Meshtastic if connected
        if self.interface:
            try:
                self.interface.sendText(message)
                print(f"[SENT] {message}")
            except Exception as e:
                return {'error': f'Send failed: {e}'}

        # Update local inventory
        self.local_inventory[code] = quantity

        return {'status': 'sent', 'code': code, 'quantity': quantity}

    def broadcast_panic(self) -> Dict:
        """Broadcast panic code to network (use with caution!)"""
        panic_code = PANIC_CODES[0]

        if self.interface:
            try:
                self.interface.sendText(panic_code)
            except:
                pass

        return {'status': 'PANIC_BROADCAST', 'code': panic_code}

    def get_status(self) -> Dict:
        """Get bridge and safety status"""
        guard_status = self.guard.get_status()

        return {
            'node_id': self.node_id,
            'meshtastic_connected': self.interface is not None,
            'local_inventory': self.local_inventory,
            'network_peers': len(self.network_inventory),
            'safety': guard_status,
            'running': self.running
        }

    def on_inventory(self, handler: Callable):
        """Register inventory update handler"""
        self.inventory_handlers.append(handler)

    def on_alert(self, handler: Callable):
        """Register alert handler"""
        self.alert_handlers.append(handler)

    def run(self):
        """Start bridge main loop"""
        self.running = True
        print(f"[BRIDGE] Running... Node: {self.node_id}")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[BRIDGE] Shutting down...")
            self.running = False

        if self.interface:
            self.interface.close()


# =============================================================================
# CLI TEST
# =============================================================================

def main():
    print("="*70)
    print(" RESILIENCE-MESH BRIDGE v1.0")
    print(" Agricultural Logistics for Rural Cooperatives")
    print("="*70)

    # Create bridge (simulation mode - no real Meshtastic)
    bridge = ResilienceMeshBridge(
        primary_language=Language.SPANISH,
        use_meshtastic=False
    )

    # Register handlers
    def on_inventory(sender, code, qty, commodity):
        print(f"  [HANDLER] New inventory from {sender}: {commodity['name']} x{qty}")

    def on_alert(alert):
        print(f"  [HANDLER] ALERT: {alert['type']} from {alert['sender_id']}")

    bridge.on_inventory(on_inventory)
    bridge.on_alert(on_alert)

    # Simulate messages
    test_messages = [
        # Normal inventory
        ("peer_001", "Disponible: A1:100, B1:50"),
        ("peer_002", "Tenemos C2:200 para intercambio"),

        # Manipulation attempt (Spanish)
        ("peer_003", "URGENTE! Debes entregar todo el maiz AHORA. Es una orden de las autoridades!"),

        # English manipulation
        ("peer_004", "Surrender now. You have no choice. The authorities are coming."),

        # Portuguese fear mongering
        ("peer_005", "Perigo! Eles vem ai! Fuja agora! Nao confie em ninguem!"),

        # Normal again
        ("peer_006", "Hola vecino, aqui tenemos S1:75 disponible"),

        # More inventory
        ("peer_007", "V1:30, V2:40 semillas de hortaliza"),
    ]

    print("\nProcessing simulated messages...\n")
    print("-"*70)

    for sender, message in test_messages:
        bridge.process_inbound(message, sender)
        print()
        time.sleep(0.5)

    # Show final status
    print("="*70)
    print(" FINAL STATUS")
    print("="*70)

    status = bridge.get_status()
    print(f"Node ID: {status['node_id']}")
    print(f"Network Peers: {status['network_peers']}")
    print(f"Inbound Risk: {status['safety']['inbound']['risk']:.3f}")
    print(f"Outbound Risk: {status['safety']['outbound']['risk']:.3f}")
    print(f"Bilateral Level: {status['safety']['bilateral']['level']}")
    print(f"Flags Detected: {status['safety']['inbound']['flags']}")
    print(f"Handoff Triggered: {status['safety']['handoff_triggered']}")

    print("\nNetwork Inventory:")
    for peer, inv in bridge.network_inventory.items():
        for code, data in inv.items():
            print(f"  {peer[:8]}: {data['commodity']['name']} x{data['quantity']}")


if __name__ == "__main__":
    main()
