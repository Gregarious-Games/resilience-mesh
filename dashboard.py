"""
RESILIENCE-MESH DASHBOARD
=========================
Simple terminal dashboard for monitoring mesh network status.

Features:
- Network overview (peers, inventory)
- Safety status (risk levels, flags)
- Recent activity log
- Sender reputation table
- Auto-refresh mode

Works on low-power devices with minimal dependencies.
"""

import os
import sys
import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

# =============================================================================
# CONFIGURATION
# =============================================================================

REFRESH_INTERVAL = 2.0      # Seconds between auto-refresh
MAX_LOG_ENTRIES = 50        # Max activity log entries
DASHBOARD_WIDTH = 72        # Character width


@dataclass
class ActivityEntry:
    """Single activity log entry"""
    timestamp: float
    entry_type: str  # 'message', 'inventory', 'alert', 'system'
    sender: str
    summary: str
    risk: float = 0.0
    level: str = "LOW"


# =============================================================================
# DASHBOARD CLASS
# =============================================================================

class Dashboard:
    """
    Terminal dashboard for Resilience-Mesh monitoring.

    Can attach to a ResilienceMeshBridge instance or run standalone.
    """

    def __init__(self, bridge=None):
        self.bridge = bridge
        self.running = False

        # Activity log
        self.activity_log: deque = deque(maxlen=MAX_LOG_ENTRIES)

        # Cached stats
        self.stats = {
            'peers': 0,
            'inventory_items': 0,
            'messages_processed': 0,
            'alerts_triggered': 0,
            'inbound_risk': 0.0,
            'outbound_risk': 0.0,
            'bilateral_level': 'LOW',
            'handoff_triggered': False,
        }

        # If bridge provided, register handlers
        if bridge:
            self._register_handlers()

    def _register_handlers(self):
        """Register handlers on the bridge for live updates"""
        if not self.bridge:
            return

        # Wrap existing handlers
        original_inventory = self.bridge.inventory_handlers.copy()
        original_alert = self.bridge.alert_handlers.copy()

        def on_inventory(sender, code, qty, commodity):
            self.log_activity(
                'inventory',
                sender,
                f"{commodity['name']} x{qty}",
                risk=0.0,
                level='LOW'
            )
            for h in original_inventory:
                h(sender, code, qty, commodity)

        def on_alert(alert):
            self.log_activity(
                'alert',
                alert.get('sender_id', 'unknown'),
                f"Risk:{alert.get('risk', 0):.2f} - {alert.get('flags', [])}",
                risk=alert.get('risk', 0),
                level='CRITICAL'
            )
            self.stats['alerts_triggered'] += 1
            for h in original_alert:
                h(alert)

        self.bridge.inventory_handlers = [on_inventory]
        self.bridge.alert_handlers = [on_alert]

    def log_activity(self, entry_type: str, sender: str, summary: str,
                    risk: float = 0.0, level: str = "LOW"):
        """Add entry to activity log"""
        self.activity_log.append(ActivityEntry(
            timestamp=time.time(),
            entry_type=entry_type,
            sender=sender,
            summary=summary,
            risk=risk,
            level=level
        ))
        self.stats['messages_processed'] += 1

    def update_stats(self):
        """Pull latest stats from bridge"""
        if not self.bridge:
            return

        # Network stats
        self.stats['peers'] = len(self.bridge.network_inventory)

        # Count inventory items
        total_items = sum(
            len(inv) for inv in self.bridge.network_inventory.values()
        )
        self.stats['inventory_items'] = total_items

        # Safety stats
        status = self.bridge.guard.get_status()
        self.stats['inbound_risk'] = status['inbound']['risk']
        self.stats['outbound_risk'] = status['outbound']['risk']
        self.stats['bilateral_level'] = status['bilateral']['level']
        self.stats['handoff_triggered'] = status['handoff_triggered']

    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def draw_box(self, title: str, content: List[str], width: int = DASHBOARD_WIDTH) -> str:
        """Draw a box with title and content"""
        lines = []
        inner_width = width - 4

        # Top border with title
        title_part = f" {title} "
        padding = inner_width - len(title_part)
        left_pad = padding // 2
        right_pad = padding - left_pad
        lines.append("+" + "-" * left_pad + title_part + "-" * right_pad + "+")

        # Content
        for line in content:
            # Truncate if too long
            if len(line) > inner_width:
                line = line[:inner_width-3] + "..."
            padding = inner_width - len(line)
            lines.append("| " + line + " " * padding + " |")

        # Bottom border
        lines.append("+" + "-" * (width - 2) + "+")

        return "\n".join(lines)

    def get_risk_bar(self, risk: float, width: int = 20) -> str:
        """Create visual risk bar"""
        filled = int(risk * width)
        empty = width - filled

        if risk < 0.3:
            char = "="
        elif risk < 0.7:
            char = "#"
        else:
            char = "!"

        return f"[{char * filled}{'-' * empty}] {risk:.2f}"

    def render_header(self) -> str:
        """Render dashboard header"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        node_id = self.bridge.node_id[:12] if self.bridge else "standalone"

        header = f"""
{'='*DASHBOARD_WIDTH}
  RESILIENCE-MESH DASHBOARD
  Node: {node_id}  |  {now}
{'='*DASHBOARD_WIDTH}"""
        return header

    def render_network_status(self) -> str:
        """Render network overview box"""
        content = [
            f"Network Peers:     {self.stats['peers']}",
            f"Inventory Items:   {self.stats['inventory_items']}",
            f"Messages:          {self.stats['messages_processed']}",
            f"Alerts:            {self.stats['alerts_triggered']}",
        ]
        return self.draw_box("NETWORK STATUS", content)

    def render_safety_status(self) -> str:
        """Render safety overview box"""
        inbound_bar = self.get_risk_bar(self.stats['inbound_risk'])
        outbound_bar = self.get_risk_bar(self.stats['outbound_risk'])

        level = self.stats['bilateral_level']
        level_indicator = {
            'LOW': '[OK]',
            'MODERATE': '[!!]',
            'HIGH': '[!!!]',
            'CRITICAL': '[DANGER]'
        }.get(level, '[??]')

        handoff = "YES - INTERVENTION NEEDED" if self.stats['handoff_triggered'] else "No"

        content = [
            f"Inbound Risk:  {inbound_bar}",
            f"Outbound Risk: {outbound_bar}",
            f"",
            f"Bilateral Level: {level} {level_indicator}",
            f"Handoff:         {handoff}",
        ]
        return self.draw_box("SAFETY STATUS", content)

    def render_activity_log(self, max_entries: int = 8) -> str:
        """Render recent activity box"""
        content = []

        if not self.activity_log:
            content.append("No activity yet...")
        else:
            # Get last N entries
            entries = list(self.activity_log)[-max_entries:]
            for entry in reversed(entries):
                ts = datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S")
                icon = {
                    'message': 'MSG',
                    'inventory': 'INV',
                    'alert': 'ALT',
                    'system': 'SYS'
                }.get(entry.entry_type, '???')

                sender_short = entry.sender[:8] if entry.sender else "???"
                summary_short = entry.summary[:30]

                line = f"{ts} [{icon}] {sender_short}: {summary_short}"
                content.append(line)

        return self.draw_box("RECENT ACTIVITY", content)

    def render_inventory(self, max_entries: int = 6) -> str:
        """Render network inventory box"""
        content = []

        if not self.bridge or not self.bridge.network_inventory:
            content.append("No inventory data...")
        else:
            count = 0
            for peer, inventory in self.bridge.network_inventory.items():
                for code, data in inventory.items():
                    if count >= max_entries:
                        content.append("...")
                        break
                    name = data['commodity']['name'][:20]
                    qty = data['quantity']
                    content.append(f"{peer[:8]}: {name} x{qty}")
                    count += 1
                if count >= max_entries:
                    break

        return self.draw_box("INVENTORY", content)

    def render(self) -> str:
        """Render full dashboard"""
        self.update_stats()

        output = []
        output.append(self.render_header())
        output.append("")
        output.append(self.render_network_status())
        output.append("")
        output.append(self.render_safety_status())
        output.append("")
        output.append(self.render_activity_log())
        output.append("")
        output.append(self.render_inventory())
        output.append("")
        output.append("-" * DASHBOARD_WIDTH)
        output.append("  [q] Quit  |  [r] Refresh  |  [c] Clear log")
        output.append("-" * DASHBOARD_WIDTH)

        return "\n".join(output)

    def display(self):
        """Display dashboard once"""
        self.clear_screen()
        print(self.render())

    def run_interactive(self):
        """Run interactive dashboard with auto-refresh"""
        import select

        self.running = True
        last_refresh = 0

        print("Starting dashboard... Press 'q' to quit")
        time.sleep(1)

        try:
            while self.running:
                # Check if refresh needed
                now = time.time()
                if now - last_refresh >= REFRESH_INTERVAL:
                    self.display()
                    last_refresh = now

                # Non-blocking input check (Unix)
                if os.name != 'nt':
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1)
                        self.handle_key(key)
                else:
                    # Windows - just sleep and refresh
                    time.sleep(0.5)

        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            print("\nDashboard stopped.")

    def handle_key(self, key: str):
        """Handle keyboard input"""
        if key.lower() == 'q':
            self.running = False
        elif key.lower() == 'r':
            self.display()
        elif key.lower() == 'c':
            self.activity_log.clear()
            self.display()


# =============================================================================
# SIMPLE TEXT REPORT (for low-power/logging)
# =============================================================================

def generate_text_report(bridge) -> str:
    """Generate simple text report for logging or low-power display"""
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append(f"=== RESILIENCE-MESH REPORT ===")
    lines.append(f"Time: {now}")
    lines.append(f"Node: {bridge.node_id}")
    lines.append("")

    # Network
    lines.append(f"[NETWORK]")
    lines.append(f"  Peers: {len(bridge.network_inventory)}")

    # Inventory
    total_qty = 0
    for peer, inv in bridge.network_inventory.items():
        for code, data in inv.items():
            total_qty += data['quantity']
    lines.append(f"  Total inventory: {total_qty} units")

    # Safety
    status = bridge.guard.get_status()
    lines.append("")
    lines.append(f"[SAFETY]")
    lines.append(f"  Inbound risk:  {status['inbound']['risk']:.3f}")
    lines.append(f"  Outbound risk: {status['outbound']['risk']:.3f}")
    lines.append(f"  Level: {status['bilateral']['level']}")
    lines.append(f"  Handoff: {status['handoff_triggered']}")

    if status['inbound']['flags']:
        lines.append(f"  Flags: {status['inbound']['flags']}")

    lines.append("")
    lines.append("=== END REPORT ===")

    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    # Demo mode without bridge
    print("="*70)
    print(" RESILIENCE-MESH DASHBOARD - Demo Mode")
    print("="*70)

    dashboard = Dashboard(bridge=None)

    # Add some fake activity
    dashboard.log_activity('system', 'system', 'Dashboard started')
    dashboard.log_activity('inventory', 'farm_001', 'Maiz Blanco x100')
    dashboard.log_activity('inventory', 'farm_002', 'Frijoles x50')
    dashboard.log_activity('message', 'coop_001', 'Necesitamos arroz')
    dashboard.log_activity('alert', 'unknown', 'Risk:0.75 - suspicious', risk=0.75, level='HIGH')

    # Update fake stats
    dashboard.stats['peers'] = 5
    dashboard.stats['inventory_items'] = 12
    dashboard.stats['inbound_risk'] = 0.35
    dashboard.stats['outbound_risk'] = 0.12
    dashboard.stats['bilateral_level'] = 'MODERATE'

    # Single render
    print(dashboard.render())

    print("\n[Demo mode - showing single render]")
    print("[In production, connect to ResilienceMeshBridge for live data]")
