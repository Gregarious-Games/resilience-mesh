"""
STARLINK BRIDGE - Urban-Rural Synchronization Layer
====================================================
Monitors Starlink User Terminal (UT) connectivity and synchronizes
local OrbitDB deltas with urban MQTT broker when connected.

Features:
- gRPC connectivity detection via 192.168.100.1
- Encrypted payload with recipient's GPG public key
- MQTT publish to private broker
- Automatic retry with exponential backoff
"""

import time
import json
import threading
import hashlib
import base64
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

# Attempt imports (may not be available on all systems)
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("[STARLINK] Warning: paho-mqtt not installed")

try:
    import gnupg
    GPG_AVAILABLE = True
except ImportError:
    GPG_AVAILABLE = False
    print("[STARLINK] Warning: python-gnupg not installed")


# =============================================================================
# CONFIGURATION
# =============================================================================

# Starlink UT gRPC endpoint
STARLINK_IP = "192.168.100.1"
STARLINK_GRPC_PORT = 9200

# MQTT broker (private, encrypted)
MQTT_BROKER = "mqtt.soberania.mesh"  # Your private broker
MQTT_PORT = 8883  # TLS
MQTT_TOPIC_PREFIX = "soberania/sync"

# Sync intervals
CHECK_INTERVAL = 30  # seconds
SYNC_INTERVAL = 300  # 5 minutes when connected
BACKOFF_MAX = 3600  # 1 hour max backoff


class ConnectivityState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    OBSTRUCTED = "obstructed"
    NO_SATELLITE = "no_satellite"
    ERROR = "error"


@dataclass
class StarlinkStatus:
    """Starlink dish status"""
    state: ConnectivityState
    uptime: float = 0
    downlink_throughput: float = 0
    uplink_throughput: float = 0
    pop_ping_latency: float = 0
    obstruction_percent: float = 0
    timestamp: float = 0

    def is_usable(self) -> bool:
        """Check if connection is good enough for sync"""
        return (
            self.state == ConnectivityState.CONNECTED and
            self.uplink_throughput > 0.1 and  # At least 100 Kbps up
            self.pop_ping_latency < 1000  # Less than 1 second latency
        )


# =============================================================================
# STARLINK gRPC INTERFACE
# =============================================================================

class StarlinkMonitor:
    """
    Monitor Starlink dish status via gRPC.

    The dish exposes a gRPC API at 192.168.100.1:9200 for status queries.
    Uses starlink-grpc-tools compatible protocol.
    """

    def __init__(self, ip: str = STARLINK_IP, port: int = STARLINK_GRPC_PORT):
        self.ip = ip
        self.port = port
        self._last_status: Optional[StarlinkStatus] = None

    def get_status(self) -> StarlinkStatus:
        """
        Query Starlink dish status.

        In production, this would use grpcio to call GetStatus.
        For now, implements a socket-based check as fallback.
        """
        import socket

        status = StarlinkStatus(
            state=ConnectivityState.DISCONNECTED,
            timestamp=time.time()
        )

        try:
            # Simple connectivity check
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.ip, self.port))
            sock.close()

            if result == 0:
                # Port is open - dish is reachable
                # In production, would parse gRPC GetStatus response
                status.state = ConnectivityState.CONNECTED
                status.uptime = 1.0
                status.downlink_throughput = 100.0  # Mbps estimate
                status.uplink_throughput = 20.0
                status.pop_ping_latency = 50.0  # ms
                status.obstruction_percent = 0.0

            else:
                status.state = ConnectivityState.DISCONNECTED

        except socket.timeout:
            status.state = ConnectivityState.NO_SATELLITE
        except Exception as e:
            status.state = ConnectivityState.ERROR
            print(f"[STARLINK] Status check error: {e}")

        self._last_status = status
        return status

    def wait_for_connection(self, timeout: float = 300) -> bool:
        """Wait for usable connection"""
        start = time.time()
        while time.time() - start < timeout:
            status = self.get_status()
            if status.is_usable():
                return True
            time.sleep(10)
        return False


# =============================================================================
# GPG ENCRYPTION
# =============================================================================

class PayloadEncryption:
    """
    GPG-based payload encryption for secure sync.

    Encrypts sync payloads with the urban recipient's public key.
    """

    def __init__(self, gnupghome: str = "~/.soberania_gpg"):
        self.gnupghome = gnupghome
        self.gpg = None
        if GPG_AVAILABLE:
            import os
            self.gpg = gnupg.GPG(gnupghome=os.path.expanduser(gnupghome))

    def encrypt_payload(self, data: Dict, recipient_key_id: str) -> Optional[str]:
        """Encrypt JSON payload for recipient"""
        if not self.gpg:
            # Fallback: base64 encode (NOT secure, for testing only)
            return base64.b64encode(json.dumps(data).encode()).decode()

        try:
            json_data = json.dumps(data)
            encrypted = self.gpg.encrypt(
                json_data,
                recipients=[recipient_key_id],
                always_trust=True,
                armor=True
            )
            if encrypted.ok:
                return str(encrypted)
            else:
                print(f"[ENCRYPT] Failed: {encrypted.status}")
        except Exception as e:
            print(f"[ENCRYPT] Error: {e}")

        return None

    def sign_payload(self, data: Dict, passphrase: Optional[str] = None) -> Optional[str]:
        """Sign payload with local key"""
        if not self.gpg:
            return None

        try:
            json_data = json.dumps(data)
            signed = self.gpg.sign(
                json_data,
                passphrase=passphrase,
                detach=True
            )
            if signed:
                return str(signed)
        except Exception as e:
            print(f"[SIGN] Error: {e}")

        return None

    def verify_signature(self, data: str, signature: str) -> bool:
        """Verify detached signature"""
        if not self.gpg:
            return False

        try:
            verified = self.gpg.verify(signature, data.encode())
            return verified.valid
        except:
            return False


# =============================================================================
# MQTT UPLINK
# =============================================================================

class MQTTUplink:
    """
    MQTT client for publishing sync payloads to urban broker.

    Uses TLS for transport security, GPG for payload encryption.
    """

    def __init__(self,
                 broker: str = MQTT_BROKER,
                 port: int = MQTT_PORT,
                 node_id: str = "unknown"):
        self.broker = broker
        self.port = port
        self.node_id = node_id
        self.client = None
        self._connected = False

        if MQTT_AVAILABLE:
            self.client = mqtt.Client(client_id=f"soberania_{node_id[:8]}")
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            print(f"[MQTT] Connected to {self.broker}")
        else:
            print(f"[MQTT] Connection failed: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        print(f"[MQTT] Disconnected: {rc}")

    def _on_publish(self, client, userdata, mid):
        print(f"[MQTT] Published message {mid}")

    def connect(self, use_tls: bool = True) -> bool:
        """Connect to MQTT broker"""
        if not self.client:
            return False

        try:
            if use_tls:
                self.client.tls_set()

            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()

            # Wait for connection
            for _ in range(10):
                if self._connected:
                    return True
                time.sleep(1)

        except Exception as e:
            print(f"[MQTT] Connect error: {e}")

        return False

    def disconnect(self):
        """Disconnect from broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self._connected = False

    def publish_sync(self, payload: str, topic_suffix: str = "inventory") -> bool:
        """Publish encrypted payload to broker"""
        if not self.client or not self._connected:
            return False

        topic = f"{MQTT_TOPIC_PREFIX}/{topic_suffix}/{self.node_id}"

        try:
            result = self.client.publish(topic, payload, qos=1)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"[MQTT] Publish error: {e}")
            return False

    def is_connected(self) -> bool:
        return self._connected


# =============================================================================
# STARLINK BRIDGE
# =============================================================================

class StarlinkBridge:
    """
    Main bridge orchestrating Starlink monitoring, encryption, and MQTT sync.

    Workflow:
    1. Monitor Starlink connectivity
    2. When connected, fetch local OrbitDB deltas
    3. Encrypt with urban recipient's public key
    4. Publish to private MQTT broker
    """

    def __init__(self,
                 node_id: str,
                 urban_key_id: str,
                 mqtt_broker: str = MQTT_BROKER,
                 gnupghome: str = "~/.soberania_gpg"):
        self.node_id = node_id
        self.urban_key_id = urban_key_id

        # Components
        self.monitor = StarlinkMonitor()
        self.encryption = PayloadEncryption(gnupghome)
        self.mqtt = MQTTUplink(broker=mqtt_broker, node_id=node_id)

        # State
        self._running = False
        self._sync_thread = None
        self._last_sync = 0
        self._pending_deltas: List[Dict] = []

        # Callbacks
        self._on_sync_handlers: List[Callable] = []

    def add_delta(self, delta: Dict):
        """Add sync delta to queue"""
        delta['timestamp'] = time.time()
        delta['node_id'] = self.node_id
        self._pending_deltas.append(delta)

    def _prepare_payload(self) -> Optional[Dict]:
        """Prepare payload from pending deltas"""
        if not self._pending_deltas:
            return None

        payload = {
            'type': 'inventory_sync',
            'node_id': self.node_id,
            'timestamp': time.time(),
            'deltas': self._pending_deltas.copy(),
            'checksum': hashlib.sha256(
                json.dumps(self._pending_deltas).encode()
            ).hexdigest()[:16]
        }

        return payload

    def _sync_cycle(self):
        """Single sync cycle"""
        # Check Starlink connectivity
        status = self.monitor.get_status()

        if not status.is_usable():
            print(f"[BRIDGE] No connection: {status.state.value}")
            return False

        # Prepare payload
        payload = self._prepare_payload()
        if not payload:
            print("[BRIDGE] No pending deltas")
            return True

        # Encrypt payload
        encrypted = self.encryption.encrypt_payload(payload, self.urban_key_id)
        if not encrypted:
            print("[BRIDGE] Encryption failed")
            return False

        # Connect to MQTT if needed
        if not self.mqtt.is_connected():
            if not self.mqtt.connect():
                print("[BRIDGE] MQTT connection failed")
                return False

        # Publish
        if self.mqtt.publish_sync(encrypted):
            print(f"[BRIDGE] Synced {len(self._pending_deltas)} deltas")
            self._pending_deltas.clear()
            self._last_sync = time.time()

            for handler in self._on_sync_handlers:
                try:
                    handler(payload)
                except:
                    pass
            return True

        return False

    def start(self, sync_interval: float = SYNC_INTERVAL):
        """Start bridge monitoring and sync"""
        if self._running:
            return

        self._running = True

        def bridge_loop():
            backoff = CHECK_INTERVAL
            while self._running:
                try:
                    if self._sync_cycle():
                        backoff = sync_interval
                    else:
                        backoff = min(backoff * 2, BACKOFF_MAX)
                except Exception as e:
                    print(f"[BRIDGE] Error: {e}")
                    backoff = min(backoff * 2, BACKOFF_MAX)

                time.sleep(backoff)

        self._sync_thread = threading.Thread(target=bridge_loop, daemon=True)
        self._sync_thread.start()
        print("[BRIDGE] Started")

    def stop(self):
        """Stop bridge"""
        self._running = False
        self.mqtt.disconnect()
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        print("[BRIDGE] Stopped")

    def force_sync(self) -> bool:
        """Force immediate sync attempt"""
        return self._sync_cycle()

    def on_sync(self, handler: Callable):
        """Register sync handler"""
        self._on_sync_handlers.append(handler)

    def get_status(self) -> Dict:
        """Get bridge status"""
        starlink = self.monitor.get_status()
        return {
            'node_id': self.node_id,
            'starlink': {
                'state': starlink.state.value,
                'usable': starlink.is_usable(),
                'latency': starlink.pop_ping_latency
            },
            'mqtt_connected': self.mqtt.is_connected(),
            'pending_deltas': len(self._pending_deltas),
            'last_sync': self._last_sync,
            'running': self._running
        }


# =============================================================================
# TEST
# =============================================================================
def main():
    print("="*60)
    print(" STARLINK BRIDGE TEST")
    print("="*60)

    # Test Starlink monitor
    print("\n[TEST] Checking Starlink connectivity...")
    monitor = StarlinkMonitor()
    status = monitor.get_status()

    print(f"  State: {status.state.value}")
    print(f"  Usable: {status.is_usable()}")
    if status.is_usable():
        print(f"  Uplink: {status.uplink_throughput} Mbps")
        print(f"  Latency: {status.pop_ping_latency} ms")

    # Test encryption
    print("\n[TEST] Testing payload encryption...")
    encryption = PayloadEncryption()
    test_payload = {
        'type': 'test',
        'data': 'Hello from the mesh',
        'timestamp': time.time()
    }

    # Without GPG (base64 fallback)
    encrypted = encryption.encrypt_payload(test_payload, "test_key")
    if encrypted:
        print(f"  Payload encrypted: {len(encrypted)} bytes")
    else:
        print("  Encryption not available")

    # Test full bridge (simulation)
    print("\n[TEST] Bridge status...")
    bridge = StarlinkBridge(
        node_id="test_farm_001",
        urban_key_id="urban_coordinator"
    )

    # Add test deltas
    bridge.add_delta({'commodity': 'A1', 'quantity': 100})
    bridge.add_delta({'commodity': 'B1', 'quantity': 50})

    status = bridge.get_status()
    print(f"  Starlink: {status['starlink']['state']}")
    print(f"  Pending deltas: {status['pending_deltas']}")
    print(f"  MQTT connected: {status['mqtt_connected']}")


if __name__ == "__main__":
    main()
