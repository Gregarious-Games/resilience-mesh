"""
INTEROPERABILITY - External System Integration
==============================================
Bridges to other tools and systems.

Features:
- CSV export for FarmOS integration
- MQTT gateway for LoRaWAN compatibility
- JSON export for custom integrations
- Import from common formats

Enables hybrid networks and data portability.
"""

import csv
import json
import time
import os
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from io import StringIO


# =============================================================================
# CSV EXPORT FOR FARMOS
# =============================================================================

class FarmOSExporter:
    """
    Export inventory and activity data in FarmOS-compatible format.

    FarmOS (https://farmos.org) is an open-source farm management system.
    This exporter creates CSV files that can be imported into FarmOS.
    """

    # FarmOS asset types
    ASSET_TYPES = {
        'A1': 'seed',      # Corn seeds
        'A2': 'seed',
        'A3': 'seed',
        'B1': 'seed',      # Bean seeds
        'B2': 'seed',
        'B3': 'seed',
        'C1': 'seed',      # Wheat
        'C2': 'seed',      # Rice
        'S1': 'seed',      # Soy
        'V1': 'seed',      # Tomato seeds
        'V2': 'seed',      # Pepper seeds
    }

    # Commodity names in English for FarmOS
    COMMODITY_NAMES = {
        'A1': 'White Corn',
        'A2': 'Blue Corn (Heirloom)',
        'A3': 'Yellow Corn',
        'B1': 'Black Beans',
        'B2': 'Red Beans',
        'B3': 'Lentils',
        'C1': 'Whole Wheat',
        'C2': 'Paddy Rice',
        'C3': 'Mountain Red Wheat',
        'S1': 'Non-GMO Soy',
        'S2': 'Sunflower Seeds',
        'V1': 'Tomato Seeds',
        'V2': 'Pepper Seeds',
    }

    def __init__(self, farm_name: str = "Resilience Mesh Farm"):
        self.farm_name = farm_name

    def export_inventory(self,
                         inventory: Dict[str, Dict],
                         output_path: str = None) -> str:
        """
        Export network inventory to FarmOS-compatible CSV.

        Args:
            inventory: {node_id: {code: {quantity, commodity, timestamp}}}
            output_path: Path to save CSV (optional)

        Returns:
            CSV string
        """
        output = StringIO()
        writer = csv.writer(output)

        # FarmOS asset import header
        writer.writerow([
            'name',
            'type',
            'status',
            'notes',
            'quantity',
            'quantity_units',
            'location',
            'timestamp'
        ])

        for node_id, node_inventory in inventory.items():
            for code, data in node_inventory.items():
                name = self.COMMODITY_NAMES.get(code, code)
                asset_type = self.ASSET_TYPES.get(code, 'material')
                quantity = data.get('quantity', 0)
                timestamp = data.get('timestamp', time.time())
                ts_str = datetime.fromtimestamp(timestamp).isoformat()

                writer.writerow([
                    f"{name} ({code})",           # name
                    asset_type,                    # type
                    'active',                      # status
                    f"From node: {node_id[:8]}",  # notes
                    quantity,                      # quantity
                    'kg',                          # quantity_units
                    node_id[:8],                  # location (node as location)
                    ts_str                         # timestamp
                ])

        csv_content = output.getvalue()

        if output_path:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)
            print(f"[EXPORT] Saved to {output_path}")

        return csv_content

    def export_activity_log(self,
                           activities: List[Dict],
                           output_path: str = None) -> str:
        """
        Export activity log to FarmOS-compatible CSV.

        Args:
            activities: List of activity dicts with timestamp, type, description
            output_path: Path to save CSV

        Returns:
            CSV string
        """
        output = StringIO()
        writer = csv.writer(output)

        # FarmOS log import header
        writer.writerow([
            'name',
            'type',
            'timestamp',
            'notes',
            'status'
        ])

        for activity in activities:
            ts = activity.get('timestamp', time.time())
            ts_str = datetime.fromtimestamp(ts).isoformat()

            log_type = {
                'inventory': 'observation',
                'trade': 'activity',
                'alert': 'observation',
                'message': 'activity'
            }.get(activity.get('type', ''), 'activity')

            writer.writerow([
                activity.get('summary', 'Activity')[:100],  # name
                log_type,                                    # type
                ts_str,                                      # timestamp
                activity.get('description', ''),             # notes
                'done'                                       # status
            ])

        csv_content = output.getvalue()

        if output_path:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)

        return csv_content

    def export_network_summary(self,
                               nodes: Dict,
                               output_path: str = None) -> str:
        """
        Export network node summary.

        Args:
            nodes: {node_id: {label, type, inventory, ...}}

        Returns:
            CSV string
        """
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            'node_id',
            'label',
            'type',
            'total_inventory_kg',
            'commodity_count',
            'last_seen',
            'status'
        ])

        for node_id, node_data in nodes.items():
            inventory = node_data.get('inventory', {})
            total_kg = sum(v.get('quantity', 0) if isinstance(v, dict) else v
                          for v in inventory.values())

            writer.writerow([
                node_id,
                node_data.get('label', node_id[:8]),
                node_data.get('type', 'farm'),
                total_kg,
                len(inventory),
                datetime.fromtimestamp(node_data.get('last_seen', time.time())).isoformat(),
                node_data.get('status', 'online')
            ])

        csv_content = output.getvalue()

        if output_path:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)

        return csv_content


# =============================================================================
# JSON EXPORT
# =============================================================================

class JSONExporter:
    """Export data in JSON format for custom integrations."""

    @staticmethod
    def export_full_state(bridge, output_path: str = None) -> str:
        """Export complete bridge state to JSON."""
        state = {
            'exported_at': datetime.now().isoformat(),
            'node_id': bridge.node_id if hasattr(bridge, 'node_id') else 'unknown',
            'network_inventory': {},
            'local_inventory': {},
            'safety_status': {},
            'network_peers': 0
        }

        if hasattr(bridge, 'network_inventory'):
            # Convert to serializable format
            for node_id, inv in bridge.network_inventory.items():
                state['network_inventory'][node_id] = {}
                for code, data in inv.items():
                    state['network_inventory'][node_id][code] = {
                        'quantity': data.get('quantity', 0),
                        'commodity': data.get('commodity', {}).get('name', code),
                        'timestamp': data.get('timestamp', 0)
                    }

        if hasattr(bridge, 'local_inventory'):
            state['local_inventory'] = dict(bridge.local_inventory)

        if hasattr(bridge, 'guard'):
            status = bridge.guard.get_status()
            state['safety_status'] = {
                'inbound_risk': status.get('inbound', {}).get('risk', 0),
                'outbound_risk': status.get('outbound', {}).get('risk', 0),
                'bilateral_level': status.get('bilateral', {}).get('level', 'LOW'),
                'handoff_triggered': status.get('handoff_triggered', False)
            }

        state['network_peers'] = len(state['network_inventory'])

        json_content = json.dumps(state, indent=2)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
            print(f"[EXPORT] JSON saved to {output_path}")

        return json_content


# =============================================================================
# MQTT GATEWAY
# =============================================================================

class MQTTGateway:
    """
    MQTT gateway for LoRaWAN and other MQTT-based systems.

    Bridges between Resilience-Mesh and MQTT brokers for:
    - LoRaWAN network servers (TTN, ChirpStack)
    - Home automation systems
    - Cloud IoT platforms
    """

    def __init__(self,
                 broker_host: str = "localhost",
                 broker_port: int = 1883,
                 topic_prefix: str = "resilience-mesh"):

        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic_prefix = topic_prefix

        self.client = None
        self.connected = False

        # Message handlers
        self.on_message_handlers: List[Callable] = []

    def connect(self, username: str = None, password: str = None) -> bool:
        """Connect to MQTT broker."""
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            print("[MQTT] paho-mqtt not installed")
            return False

        self.client = mqtt.Client()

        if username:
            self.client.username_pw_set(username, password)

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.connected = True
                print(f"[MQTT] Connected to {self.broker_host}")
                # Subscribe to incoming messages
                client.subscribe(f"{self.topic_prefix}/+/rx")
            else:
                print(f"[MQTT] Connection failed: {rc}")

        def on_message(client, userdata, msg):
            self._handle_message(msg.topic, msg.payload)

        self.client.on_connect = on_connect
        self.client.on_message = on_message

        try:
            self.client.connect(self.broker_host, self.broker_port)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[MQTT] Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

    def _handle_message(self, topic: str, payload: bytes):
        """Handle incoming MQTT message."""
        try:
            # Parse topic: resilience-mesh/{node_id}/rx
            parts = topic.split('/')
            if len(parts) >= 3:
                node_id = parts[1]
                data = json.loads(payload.decode())

                for handler in self.on_message_handlers:
                    try:
                        handler(node_id, data)
                    except:
                        pass

        except Exception as e:
            print(f"[MQTT] Message parse error: {e}")

    def publish_inventory(self, node_id: str, inventory: Dict):
        """Publish inventory update to MQTT."""
        if not self.connected:
            return False

        topic = f"{self.topic_prefix}/{node_id}/inventory"
        payload = json.dumps({
            'timestamp': time.time(),
            'inventory': inventory
        })

        self.client.publish(topic, payload)
        return True

    def publish_alert(self, node_id: str, alert: Dict):
        """Publish safety alert to MQTT."""
        if not self.connected:
            return False

        topic = f"{self.topic_prefix}/{node_id}/alert"
        payload = json.dumps({
            'timestamp': time.time(),
            'alert': alert
        })

        self.client.publish(topic, payload, qos=1)  # QoS 1 for alerts
        return True

    def on_message(self, handler: Callable):
        """Register message handler."""
        self.on_message_handlers.append(handler)


# =============================================================================
# IMPORT UTILITIES
# =============================================================================

class DataImporter:
    """Import data from various formats."""

    @staticmethod
    def import_inventory_csv(csv_path: str) -> Dict[str, Dict]:
        """
        Import inventory from CSV file.

        Expected columns: node_id, code, quantity
        """
        inventory = {}

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                node_id = row.get('node_id', 'imported')
                code = row.get('code', '').upper()
                quantity = int(row.get('quantity', 0))

                if node_id not in inventory:
                    inventory[node_id] = {}

                inventory[node_id][code] = {
                    'quantity': quantity,
                    'timestamp': time.time(),
                    'imported': True
                }

        return inventory

    @staticmethod
    def import_farmos_assets(csv_path: str) -> Dict[str, Dict]:
        """Import from FarmOS asset export."""
        inventory = {}

        # Reverse lookup for codes
        name_to_code = {v: k for k, v in FarmOSExporter.COMMODITY_NAMES.items()}

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('name', '')
                # Try to extract code from name
                code = None
                for n, c in name_to_code.items():
                    if n.lower() in name.lower():
                        code = c
                        break

                if not code:
                    continue

                location = row.get('location', 'imported')
                quantity = float(row.get('quantity', 0))

                if location not in inventory:
                    inventory[location] = {}

                inventory[location][code] = {
                    'quantity': int(quantity),
                    'timestamp': time.time(),
                    'imported_from': 'farmos'
                }

        return inventory


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    print("="*70)
    print(" INTEROPERABILITY TEST")
    print("="*70)

    # Test data
    test_inventory = {
        'farm_001': {
            'A1': {'quantity': 150, 'commodity': {'name': 'Maiz Blanco'}, 'timestamp': time.time()},
            'B1': {'quantity': 75, 'commodity': {'name': 'Caraotas Negras'}, 'timestamp': time.time()},
        },
        'farm_002': {
            'C2': {'quantity': 200, 'commodity': {'name': 'Arroz Paddy'}, 'timestamp': time.time()},
            'S1': {'quantity': 50, 'commodity': {'name': 'Soya No-GMO'}, 'timestamp': time.time()},
        },
        'coop_001': {
            'A1': {'quantity': 500, 'commodity': {'name': 'Maiz Blanco'}, 'timestamp': time.time()},
            'A2': {'quantity': 300, 'commodity': {'name': 'Maiz Azul'}, 'timestamp': time.time()},
        }
    }

    test_activities = [
        {'type': 'inventory', 'summary': 'Farm 001 reported A1:150', 'timestamp': time.time()},
        {'type': 'trade', 'summary': 'Trade proposal: A1 for C2', 'timestamp': time.time()},
        {'type': 'alert', 'summary': 'High risk message detected', 'timestamp': time.time()},
    ]

    # Test CSV export
    print("\n[Test 1] FarmOS CSV Export")
    exporter = FarmOSExporter(farm_name="Test Cooperative")
    csv_content = exporter.export_inventory(test_inventory)
    print("  Inventory CSV:")
    for line in csv_content.split('\n')[:5]:
        print(f"    {line}")
    print("    ...")

    # Test activity export
    print("\n[Test 2] Activity Log Export")
    activity_csv = exporter.export_activity_log(test_activities)
    print("  Activity CSV:")
    for line in activity_csv.split('\n')[:4]:
        print(f"    {line}")

    # Test JSON export
    print("\n[Test 3] JSON Export")

    class MockBridge:
        node_id = "test_node_001"
        network_inventory = test_inventory
        local_inventory = {'A1': 100}

        class guard:
            @staticmethod
            def get_status():
                return {
                    'inbound': {'risk': 0.15},
                    'outbound': {'risk': 0.08},
                    'bilateral': {'level': 'LOW'},
                    'handoff_triggered': False
                }

    json_content = JSONExporter.export_full_state(MockBridge())
    parsed = json.loads(json_content)
    print(f"  Node ID: {parsed['node_id']}")
    print(f"  Peers: {parsed['network_peers']}")
    print(f"  Safety Level: {parsed['safety_status']['bilateral_level']}")

    # Test network summary
    print("\n[Test 4] Network Summary Export")
    test_nodes = {
        'farm_001': {'label': 'Farm Alpha', 'type': 'farm', 'inventory': {'A1': 150}, 'last_seen': time.time(), 'status': 'online'},
        'farm_002': {'label': 'Farm Beta', 'type': 'farm', 'inventory': {'C2': 200}, 'last_seen': time.time(), 'status': 'online'},
        'coop_001': {'label': 'Central Coop', 'type': 'coop', 'inventory': {'A1': 500, 'A2': 300}, 'last_seen': time.time(), 'status': 'online'},
    }
    summary_csv = exporter.export_network_summary(test_nodes)
    print("  Network Summary:")
    for line in summary_csv.split('\n'):
        print(f"    {line}")

    print("\n" + "="*70)
    print(" INTEROPERABILITY TESTS COMPLETE")
    print("="*70)
