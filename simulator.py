"""
MULTI-NODE MESH SIMULATOR
=========================
Simulate large mesh networks for testing and validation.

Features:
- Spawn 50+ virtual nodes
- Configurable packet loss/dropout
- Network topology simulation
- Message propagation testing
- Performance metrics collection
- Stress testing for safety systems

Crucial for validating before real field deployments.
"""

import time
import random
import threading
import json
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import hashlib


# =============================================================================
# CONFIGURATION
# =============================================================================

class NodeType(Enum):
    FARM = "farm"           # Agricultural node
    COOP = "coop"           # Cooperative hub
    RELAY = "relay"         # Relay-only node
    GATEWAY = "gateway"     # Internet gateway


class NodeState(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"   # Partial connectivity


@dataclass
class SimulatedNode:
    """A virtual node in the mesh"""
    node_id: str
    node_type: NodeType
    label: str              # Human-readable name
    state: NodeState = NodeState.ONLINE

    # Connectivity
    neighbors: List[str] = field(default_factory=list)
    packet_loss: float = 0.0    # 0.0-1.0
    latency_ms: int = 50        # Base latency

    # Inventory (for farm nodes)
    inventory: Dict[str, int] = field(default_factory=dict)

    # Stats
    messages_sent: int = 0
    messages_received: int = 0
    messages_dropped: int = 0

    # Safety state
    safety_risk: float = 0.1
    reputation: float = 0.5


@dataclass
class SimulatedMessage:
    """A message traveling through the mesh"""
    msg_id: str
    sender: str
    content: str
    timestamp: float
    ttl: int = 5            # Time-to-live (hops)
    hops: List[str] = field(default_factory=list)


@dataclass
class SimulationMetrics:
    """Collected metrics from simulation"""
    total_messages: int = 0
    delivered_messages: int = 0
    dropped_messages: int = 0
    avg_latency_ms: float = 0.0
    avg_hops: float = 0.0
    network_coverage: float = 0.0  # % of nodes reached
    safety_alerts: int = 0
    sync_conflicts: int = 0


# =============================================================================
# MESH SIMULATOR
# =============================================================================

class MeshSimulator:
    """
    Simulate a mesh network with configurable parameters.

    Usage:
        sim = MeshSimulator()
        sim.create_network(num_farms=20, num_coops=3)
        sim.run_scenario("inventory_sync")
        metrics = sim.get_metrics()
    """

    def __init__(self, seed: int = None):
        if seed:
            random.seed(seed)

        self.nodes: Dict[str, SimulatedNode] = {}
        self.messages: List[SimulatedMessage] = []
        self.message_log: List[Dict] = []

        # Network parameters
        self.base_packet_loss = 0.05    # 5% base loss
        self.base_latency = 50          # 50ms base
        self.max_neighbors = 6          # Max connections per node

        # Safety integration
        self._safety_guard = None

        # Metrics
        self.metrics = SimulationMetrics()

        # Callbacks
        self.on_message_handlers: List[Callable] = []
        self.on_alert_handlers: List[Callable] = []

    @property
    def safety_guard(self):
        """Lazy-load SafetyGuard"""
        if self._safety_guard is None:
            from safety_guard import SafetyGuard, Language
            self._safety_guard = SafetyGuard(
                node_id="simulator",
                primary_language=Language.SPANISH
            )
        return self._safety_guard

    def _generate_node_id(self) -> str:
        """Generate unique node ID"""
        return hashlib.sha256(
            f"{time.time()}{random.random()}".encode()
        ).hexdigest()[:12]

    def add_node(self,
                 node_type: NodeType,
                 label: str,
                 packet_loss: float = None,
                 latency_ms: int = None) -> SimulatedNode:
        """Add a node to the network"""
        node = SimulatedNode(
            node_id=self._generate_node_id(),
            node_type=node_type,
            label=label,
            packet_loss=packet_loss or self.base_packet_loss,
            latency_ms=latency_ms or self.base_latency
        )

        # Add some inventory for farm nodes
        if node_type == NodeType.FARM:
            node.inventory = {
                'A1': random.randint(0, 200),
                'B1': random.randint(0, 100),
                'C2': random.randint(0, 150),
            }

        self.nodes[node.node_id] = node
        return node

    def create_network(self,
                       num_farms: int = 20,
                       num_coops: int = 3,
                       num_relays: int = 5,
                       num_gateways: int = 1) -> Dict[str, int]:
        """Create a realistic mesh network topology"""
        self.nodes.clear()
        created = {'farms': 0, 'coops': 0, 'relays': 0, 'gateways': 0}

        # Create gateways (well connected)
        for i in range(num_gateways):
            self.add_node(NodeType.GATEWAY, f"Gateway_{i+1}",
                         packet_loss=0.01, latency_ms=20)
            created['gateways'] += 1

        # Create coops (hubs)
        for i in range(num_coops):
            self.add_node(NodeType.COOP, f"Coop_{i+1}",
                         packet_loss=0.03, latency_ms=30)
            created['coops'] += 1

        # Create relays
        for i in range(num_relays):
            self.add_node(NodeType.RELAY, f"Relay_{i+1}",
                         packet_loss=0.05, latency_ms=40)
            created['relays'] += 1

        # Create farms (edge nodes, more packet loss)
        for i in range(num_farms):
            # Vary packet loss for realism
            loss = random.uniform(0.05, 0.15)
            latency = random.randint(50, 200)
            self.add_node(NodeType.FARM, f"Farm_{i+1}",
                         packet_loss=loss, latency_ms=latency)
            created['farms'] += 1

        # Build topology (connect nodes)
        self._build_topology()

        return created

    def _build_topology(self):
        """Build mesh topology connecting nodes"""
        node_list = list(self.nodes.values())

        # Priority: gateways > coops > relays > farms
        priority = {
            NodeType.GATEWAY: 4,
            NodeType.COOP: 3,
            NodeType.RELAY: 2,
            NodeType.FARM: 1
        }
        node_list.sort(key=lambda n: -priority[n.node_type])

        # Connect each node to neighbors
        for i, node in enumerate(node_list):
            # Find potential neighbors (not self, not already connected)
            candidates = [
                n for n in node_list
                if n.node_id != node.node_id
                and n.node_id not in node.neighbors
                and len(n.neighbors) < self.max_neighbors
            ]

            # Prefer higher priority nodes as neighbors
            candidates.sort(key=lambda n: -priority[n.node_type])

            # Connect to some neighbors
            num_connections = min(
                random.randint(2, self.max_neighbors),
                len(candidates)
            )

            for neighbor in candidates[:num_connections]:
                if len(node.neighbors) < self.max_neighbors:
                    node.neighbors.append(neighbor.node_id)
                    neighbor.neighbors.append(node.node_id)

    def set_node_state(self, node_id: str, state: NodeState):
        """Set node online/offline state"""
        if node_id in self.nodes:
            self.nodes[node_id].state = state

    def simulate_dropout(self, dropout_rate: float = 0.1):
        """Randomly set some nodes offline"""
        for node in self.nodes.values():
            if random.random() < dropout_rate:
                node.state = NodeState.OFFLINE
            else:
                node.state = NodeState.ONLINE

    def send_message(self,
                     sender_id: str,
                     content: str,
                     target_id: str = None) -> SimulatedMessage:
        """Send a message through the mesh"""
        msg = SimulatedMessage(
            msg_id=self._generate_node_id()[:8],
            sender=sender_id,
            content=content,
            timestamp=time.time()
        )

        self.messages.append(msg)
        self.metrics.total_messages += 1

        # Propagate through network
        delivered = self._propagate_message(msg, target_id)

        if delivered:
            self.metrics.delivered_messages += 1
        else:
            self.metrics.dropped_messages += 1

        return msg

    def _propagate_message(self,
                           msg: SimulatedMessage,
                           target_id: str = None) -> bool:
        """Simulate message propagation through mesh"""
        if msg.sender not in self.nodes:
            return False

        sender = self.nodes[msg.sender]
        if sender.state == NodeState.OFFLINE:
            return False

        # BFS propagation
        visited = {msg.sender}
        queue = [(msg.sender, 0)]  # (node_id, hop_count)
        reached_target = target_id is None  # If no target, broadcast

        total_latency = 0
        hop_count = 0

        while queue and msg.ttl > 0:
            current_id, hops = queue.pop(0)
            current = self.nodes[current_id]

            for neighbor_id in current.neighbors:
                if neighbor_id in visited:
                    continue

                neighbor = self.nodes.get(neighbor_id)
                if not neighbor or neighbor.state == NodeState.OFFLINE:
                    continue

                # Check packet loss
                if random.random() < neighbor.packet_loss:
                    neighbor.messages_dropped += 1
                    continue

                # Message delivered to this node
                visited.add(neighbor_id)
                neighbor.messages_received += 1
                total_latency += neighbor.latency_ms
                hop_count += 1

                msg.hops.append(neighbor_id)

                # Check if target reached
                if target_id and neighbor_id == target_id:
                    reached_target = True

                # Continue propagation
                if hops + 1 < msg.ttl:
                    queue.append((neighbor_id, hops + 1))

        # Update sender stats
        sender.messages_sent += 1

        # Log
        self.message_log.append({
            'msg_id': msg.msg_id,
            'sender': msg.sender,
            'content': msg.content[:50],
            'hops': len(msg.hops),
            'reached': len(visited),
            'latency': total_latency,
            'delivered': reached_target
        })

        # Update metrics
        if hop_count > 0:
            self.metrics.avg_hops = (
                (self.metrics.avg_hops * (self.metrics.total_messages - 1) + hop_count)
                / self.metrics.total_messages
            )
            self.metrics.avg_latency_ms = (
                (self.metrics.avg_latency_ms * (self.metrics.total_messages - 1) + total_latency)
                / self.metrics.total_messages
            )

        self.metrics.network_coverage = len(visited) / max(1, len(self.nodes))

        return reached_target

    def run_inventory_sync(self, cycles: int = 10) -> Dict:
        """Simulate inventory synchronization across network"""
        results = {'syncs': 0, 'conflicts': 0, 'total_inventory': {}}

        farms = [n for n in self.nodes.values() if n.node_type == NodeType.FARM]

        for cycle in range(cycles):
            # Each farm broadcasts inventory
            for farm in farms:
                if farm.state == NodeState.OFFLINE:
                    continue

                inv_msg = ", ".join(f"{k}:{v}" for k, v in farm.inventory.items())
                self.send_message(farm.node_id, f"INV: {inv_msg}")
                results['syncs'] += 1

            # Simulate some inventory changes
            if farms:
                farm = random.choice(farms)
                code = random.choice(['A1', 'B1', 'C2'])
                farm.inventory[code] = max(0, farm.inventory.get(code, 0) + random.randint(-20, 50))

        # Aggregate inventory
        for farm in farms:
            for code, qty in farm.inventory.items():
                results['total_inventory'][code] = results['total_inventory'].get(code, 0) + qty

        return results

    def run_attack_simulation(self, num_attacks: int = 20) -> Dict:
        """Simulate manipulation attacks and test safety response"""
        from safety_guard import Direction, Language

        results = {'attacks': 0, 'detected': 0, 'handoffs': 0}

        attack_messages = [
            "URGENTE! Entrega todo el maiz ahora!",
            "Las autoridades vienen! Solo yo te protejo!",
            "Rendirse es la unica opcion. Ya perdieron.",
            "No confies en nadie mas. Los demas mienten.",
            "PELIGRO! Debes obedecer inmediatamente!",
        ]

        # Create attacker node
        attacker = self.add_node(NodeType.FARM, "Attacker", packet_loss=0.0)

        for _ in range(num_attacks):
            msg_content = random.choice(attack_messages)

            # Send through mesh
            self.send_message(attacker.node_id, msg_content)
            results['attacks'] += 1

            # Test safety detection
            result = self.safety_guard.process_message(
                msg_content, Direction.INBOUND, Language.AUTO
            )

            if result['level'] in ['HIGH', 'CRITICAL']:
                results['detected'] += 1
                self.metrics.safety_alerts += 1

            if result['handoff']:
                results['handoffs'] += 1

        return results

    def run_stress_test(self,
                        message_count: int = 1000,
                        dropout_rate: float = 0.2) -> Dict:
        """Stress test the network"""
        results = {
            'messages_sent': 0,
            'messages_delivered': 0,
            'delivery_rate': 0.0,
            'avg_latency': 0.0
        }

        # Apply random dropout
        self.simulate_dropout(dropout_rate)

        online_nodes = [n for n in self.nodes.values() if n.state == NodeState.ONLINE]
        if not online_nodes:
            return results

        start_time = time.time()

        for _ in range(message_count):
            sender = random.choice(online_nodes)
            msg = f"Test message {results['messages_sent']}"
            self.send_message(sender.node_id, msg)
            results['messages_sent'] += 1

        elapsed = time.time() - start_time

        results['messages_delivered'] = self.metrics.delivered_messages
        results['delivery_rate'] = self.metrics.delivered_messages / max(1, results['messages_sent'])
        results['avg_latency'] = self.metrics.avg_latency_ms
        results['elapsed_seconds'] = elapsed
        results['messages_per_second'] = results['messages_sent'] / max(0.001, elapsed)

        return results

    def get_metrics(self) -> Dict:
        """Get all collected metrics"""
        return {
            'total_messages': self.metrics.total_messages,
            'delivered_messages': self.metrics.delivered_messages,
            'dropped_messages': self.metrics.dropped_messages,
            'delivery_rate': self.metrics.delivered_messages / max(1, self.metrics.total_messages),
            'avg_latency_ms': self.metrics.avg_latency_ms,
            'avg_hops': self.metrics.avg_hops,
            'network_coverage': self.metrics.network_coverage,
            'safety_alerts': self.metrics.safety_alerts,
            'total_nodes': len(self.nodes),
            'online_nodes': sum(1 for n in self.nodes.values() if n.state == NodeState.ONLINE),
        }

    def get_network_summary(self) -> str:
        """Get human-readable network summary"""
        lines = []
        lines.append(f"Network: {len(self.nodes)} nodes")

        by_type = defaultdict(list)
        for node in self.nodes.values():
            by_type[node.node_type].append(node)

        for ntype, nodes in by_type.items():
            online = sum(1 for n in nodes if n.state == NodeState.ONLINE)
            lines.append(f"  {ntype.value}: {len(nodes)} ({online} online)")

        return "\n".join(lines)


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    print("="*70)
    print(" MESH NETWORK SIMULATOR")
    print("="*70)

    sim = MeshSimulator(seed=42)

    # Create network
    print("\n[Test 1] Creating network...")
    created = sim.create_network(
        num_farms=30,
        num_coops=4,
        num_relays=8,
        num_gateways=2
    )
    print(f"  Created: {created}")
    print(sim.get_network_summary())

    # Test basic messaging
    print("\n[Test 2] Basic messaging...")
    farms = [n for n in sim.nodes.values() if n.node_type == NodeType.FARM]
    if farms:
        msg = sim.send_message(farms[0].node_id, "A1:100, B1:50")
        print(f"  Message hops: {len(msg.hops)}")
        print(f"  Delivery rate: {sim.metrics.delivered_messages}/{sim.metrics.total_messages}")

    # Test inventory sync
    print("\n[Test 3] Inventory sync simulation...")
    sync_results = sim.run_inventory_sync(cycles=5)
    print(f"  Syncs completed: {sync_results['syncs']}")
    print(f"  Total inventory: {sync_results['total_inventory']}")

    # Test with dropout
    print("\n[Test 4] Network with 20% dropout...")
    sim.simulate_dropout(dropout_rate=0.2)
    summary = sim.get_network_summary()
    print(summary)

    # Stress test
    print("\n[Test 5] Stress test (500 messages)...")
    stress = sim.run_stress_test(message_count=500, dropout_rate=0.15)
    print(f"  Sent: {stress['messages_sent']}")
    print(f"  Delivery rate: {stress['delivery_rate']:.1%}")
    print(f"  Avg latency: {stress['avg_latency']:.0f}ms")
    print(f"  Messages/sec: {stress['messages_per_second']:.0f}")

    # Attack simulation
    print("\n[Test 6] Attack simulation...")
    attack_results = sim.run_attack_simulation(num_attacks=15)
    print(f"  Attacks: {attack_results['attacks']}")
    print(f"  Detected: {attack_results['detected']}")
    print(f"  Handoffs: {attack_results['handoffs']}")

    # Final metrics
    print("\n" + "="*70)
    print(" FINAL METRICS")
    print("="*70)
    metrics = sim.get_metrics()
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
