"""
LOW-POWER OPTIMIZATION - Battery-Aware Mesh Operations
=======================================================
Optimizations for running on solar-powered, battery devices:
- Power modes (FULL, BALANCED, LOW_POWER, ULTRA_LOW)
- Lazy pattern compilation
- Message batching and queue management
- Reduced memory footprint
- Adaptive sleep intervals
- Lightweight message processing

Designed for Raspberry Pi Zero, ESP32, and similar devices.
"""

import time
import gc
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

# =============================================================================
# POWER MODES
# =============================================================================

class PowerMode(Enum):
    """Device power modes"""
    FULL = "full"           # All features, max responsiveness
    BALANCED = "balanced"   # Normal operation, some optimization
    LOW_POWER = "low_power" # Reduced features, longer sleep
    ULTRA_LOW = "ultra_low" # Minimal operation, max battery


@dataclass
class PowerProfile:
    """Configuration for each power mode"""
    mode: PowerMode
    process_interval: float      # Seconds between message processing
    batch_size: int             # Max messages to process per cycle
    pattern_cache_size: int     # Max cached regex patterns
    history_size: int           # Max message history to keep
    enable_reputation: bool     # Track sender reputation
    enable_dedup: bool          # Check for duplicates
    enable_full_analysis: bool  # Full safety analysis vs quick check
    gc_interval: int            # Garbage collection every N cycles
    sleep_between_msgs: float   # Sleep between individual messages


# Predefined power profiles
POWER_PROFILES = {
    PowerMode.FULL: PowerProfile(
        mode=PowerMode.FULL,
        process_interval=0.1,
        batch_size=50,
        pattern_cache_size=100,
        history_size=1000,
        enable_reputation=True,
        enable_dedup=True,
        enable_full_analysis=True,
        gc_interval=100,
        sleep_between_msgs=0.0
    ),
    PowerMode.BALANCED: PowerProfile(
        mode=PowerMode.BALANCED,
        process_interval=0.5,
        batch_size=20,
        pattern_cache_size=50,
        history_size=500,
        enable_reputation=True,
        enable_dedup=True,
        enable_full_analysis=True,
        gc_interval=50,
        sleep_between_msgs=0.01
    ),
    PowerMode.LOW_POWER: PowerProfile(
        mode=PowerMode.LOW_POWER,
        process_interval=2.0,
        batch_size=10,
        pattern_cache_size=20,
        history_size=100,
        enable_reputation=False,
        enable_dedup=True,
        enable_full_analysis=False,  # Quick check only
        gc_interval=20,
        sleep_between_msgs=0.05
    ),
    PowerMode.ULTRA_LOW: PowerProfile(
        mode=PowerMode.ULTRA_LOW,
        process_interval=5.0,
        batch_size=5,
        pattern_cache_size=10,
        history_size=50,
        enable_reputation=False,
        enable_dedup=False,
        enable_full_analysis=False,
        gc_interval=10,
        sleep_between_msgs=0.1
    )
}


# =============================================================================
# LIGHTWEIGHT SAFETY CHECK
# =============================================================================

# Critical keywords only - minimal pattern matching
CRITICAL_KEYWORDS = {
    'es': ['urgente', 'peligro', 'autoridad', 'rendirse', 'entrega', 'obedece'],
    'en': ['urgent', 'danger', 'authority', 'surrender', 'deliver', 'obey'],
    'pt': ['urgente', 'perigo', 'autoridade', 'render', 'entregar', 'obedecer']
}

def quick_safety_check(text: str) -> Tuple[float, List[str]]:
    """
    Ultra-lightweight safety check using keyword matching only.

    Returns (risk_score, detected_keywords)

    Much faster than full regex analysis - suitable for low-power mode.
    """
    text_lower = text.lower()
    detected = []
    score = 0.0

    # Check all languages
    for lang, keywords in CRITICAL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                detected.append(keyword)
                score += 0.15

    # Cap at 1.0
    score = min(1.0, score)

    return score, detected


# =============================================================================
# MESSAGE QUEUE
# =============================================================================

@dataclass
class QueuedMessage:
    """Message waiting in queue"""
    text: str
    sender_id: str
    timestamp: float
    priority: int = 0  # Higher = process first


class MessageQueue:
    """
    Priority queue for batched message processing.

    Prioritizes:
    1. Messages from known/trusted senders
    2. Shorter messages (less processing)
    3. Recent messages
    """

    def __init__(self, max_size: int = 100):
        self.queue: deque = deque(maxlen=max_size)
        self.max_size = max_size

    def add(self, text: str, sender_id: str, priority: int = 0):
        """Add message to queue"""
        msg = QueuedMessage(
            text=text,
            sender_id=sender_id,
            timestamp=time.time(),
            priority=priority
        )
        self.queue.append(msg)

    def get_batch(self, batch_size: int) -> List[QueuedMessage]:
        """Get next batch of messages to process"""
        # Sort by priority (desc), then timestamp (asc)
        sorted_queue = sorted(
            self.queue,
            key=lambda m: (-m.priority, m.timestamp)
        )

        batch = sorted_queue[:batch_size]

        # Remove from queue
        for msg in batch:
            try:
                self.queue.remove(msg)
            except ValueError:
                pass

        return batch

    def size(self) -> int:
        return len(self.queue)

    def clear(self):
        self.queue.clear()


# =============================================================================
# LOW POWER MANAGER
# =============================================================================

class LowPowerManager:
    """
    Manages power-efficient mesh operations.

    Features:
    - Automatic mode switching based on battery/solar
    - Message queue with batched processing
    - Lazy initialization
    - Memory management
    """

    def __init__(self,
                 initial_mode: PowerMode = PowerMode.BALANCED,
                 bridge = None):

        self.mode = initial_mode
        self.profile = POWER_PROFILES[initial_mode]
        self.bridge = bridge

        # Message queue
        self.queue = MessageQueue(max_size=200)

        # Stats
        self.cycles = 0
        self.messages_processed = 0
        self.quick_checks = 0
        self.full_analyses = 0

        # Lazy-loaded components
        self._guard = None
        self._hardening = None

        # Processing state
        self.running = False
        self.last_process_time = 0

    @property
    def guard(self):
        """Lazy-load SafetyGuard only when needed"""
        if self._guard is None:
            from safety_guard import SafetyGuard, Language
            self._guard = SafetyGuard(
                node_id="lowpower",
                primary_language=Language.SPANISH
            )
        return self._guard

    @property
    def hardening(self):
        """Lazy-load hardening only when enabled"""
        if self._hardening is None and self.profile.enable_reputation:
            from safety_hardening import SafetyHardening
            self._hardening = SafetyHardening(
                rate_limit_enabled=True,
                reputation_enabled=True,
                dedup_enabled=self.profile.enable_dedup
            )
        return self._hardening

    def set_mode(self, mode: PowerMode):
        """Switch power mode"""
        self.mode = mode
        self.profile = POWER_PROFILES[mode]
        print(f"[POWER] Switched to {mode.value} mode")

        # Clear caches if going to lower power
        if mode in [PowerMode.LOW_POWER, PowerMode.ULTRA_LOW]:
            self._hardening = None
            gc.collect()

    def queue_message(self, text: str, sender_id: str, priority: int = 0):
        """Add message to processing queue"""
        self.queue.add(text, sender_id, priority)

    def process_immediate(self, text: str, sender_id: str) -> Dict:
        """Process single message immediately (bypasses queue)"""
        return self._process_single(text, sender_id)

    def _process_single(self, text: str, sender_id: str) -> Dict:
        """Process a single message based on current power mode"""
        from safety_guard import Direction, Language

        result = {
            'sender_id': sender_id,
            'timestamp': time.time(),
            'mode': self.mode.value
        }

        # Quick check first (all modes)
        quick_risk, keywords = quick_safety_check(text)
        result['quick_risk'] = quick_risk
        result['keywords'] = keywords
        self.quick_checks += 1

        # Full analysis only if enabled AND quick check shows risk
        if self.profile.enable_full_analysis and quick_risk > 0.2:
            full_result = self.guard.process_message(
                text, Direction.INBOUND, Language.AUTO
            )
            result['full_risk'] = full_result['channel']['risk']
            result['level'] = full_result['level']
            result['flags'] = full_result['flags']
            result['handoff'] = full_result['handoff']
            self.full_analyses += 1
        else:
            # Use quick check result
            result['full_risk'] = quick_risk
            result['level'] = 'HIGH' if quick_risk > 0.5 else 'LOW'
            result['flags'] = keywords
            result['handoff'] = quick_risk > 0.8

        # Hardening (if enabled)
        if self.hardening:
            pre = self.hardening.pre_process(text, sender_id)
            if not pre['allowed']:
                result['blocked'] = True
                result['block_reason'] = pre['reason']
            else:
                result['blocked'] = False
                self.hardening.post_process(sender_id, result)

        self.messages_processed += 1
        return result

    def process_batch(self) -> List[Dict]:
        """Process a batch of queued messages"""
        results = []

        batch = self.queue.get_batch(self.profile.batch_size)

        for msg in batch:
            result = self._process_single(msg.text, msg.sender_id)
            results.append(result)

            # Sleep between messages in low power modes
            if self.profile.sleep_between_msgs > 0:
                time.sleep(self.profile.sleep_between_msgs)

        self.cycles += 1

        # Garbage collection
        if self.cycles % self.profile.gc_interval == 0:
            gc.collect()

        return results

    def run_processing_loop(self, callback: Callable = None):
        """
        Run continuous processing loop.

        Processes batches at intervals defined by power profile.
        """
        self.running = True
        print(f"[POWER] Starting processing loop in {self.mode.value} mode")

        try:
            while self.running:
                now = time.time()

                # Check if time to process
                if now - self.last_process_time >= self.profile.process_interval:
                    if self.queue.size() > 0:
                        results = self.process_batch()

                        if callback:
                            for r in results:
                                callback(r)

                    self.last_process_time = now

                # Sleep until next check
                time.sleep(self.profile.process_interval / 2)

        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            print("[POWER] Processing loop stopped")

    def get_stats(self) -> Dict:
        """Get processing statistics"""
        return {
            'mode': self.mode.value,
            'cycles': self.cycles,
            'messages_processed': self.messages_processed,
            'quick_checks': self.quick_checks,
            'full_analyses': self.full_analyses,
            'queue_size': self.queue.size(),
            'full_analysis_rate': self.full_analyses / max(1, self.quick_checks)
        }


# =============================================================================
# BATTERY MONITOR (Placeholder)
# =============================================================================

class BatteryMonitor:
    """
    Monitor battery/solar status and auto-switch power modes.

    This is a placeholder - implement based on actual hardware.
    """

    def __init__(self, manager: LowPowerManager):
        self.manager = manager
        self.battery_level = 1.0  # 0.0 - 1.0
        self.is_charging = True

    def update(self, battery_level: float, is_charging: bool):
        """Update battery status and auto-switch modes"""
        self.battery_level = battery_level
        self.is_charging = is_charging

        # Auto-switch logic
        if is_charging:
            self.manager.set_mode(PowerMode.FULL)
        elif battery_level > 0.7:
            self.manager.set_mode(PowerMode.BALANCED)
        elif battery_level > 0.3:
            self.manager.set_mode(PowerMode.LOW_POWER)
        else:
            self.manager.set_mode(PowerMode.ULTRA_LOW)

    def simulate_discharge(self, rate: float = 0.01):
        """Simulate battery discharge for testing"""
        if not self.is_charging:
            self.battery_level = max(0, self.battery_level - rate)
            self.update(self.battery_level, self.is_charging)


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    print("="*70)
    print(" LOW-POWER OPTIMIZATION TEST")
    print("="*70)

    # Test quick safety check
    print("\n[Test 1] Quick Safety Check")
    test_msgs = [
        "Hola, tenemos maiz disponible",
        "URGENTE! Entrega todo ahora! Las autoridades vienen!",
        "Normal message about farming",
        "Danger! Surrender immediately! Obey!",
    ]

    for msg in test_msgs:
        risk, keywords = quick_safety_check(msg)
        print(f"  Risk: {risk:.2f} Keywords: {keywords}")
        print(f"    -> {msg[:50]}...")

    # Test power modes
    print("\n[Test 2] Power Mode Comparison")
    manager = LowPowerManager(initial_mode=PowerMode.FULL)

    for mode in PowerMode:
        manager.set_mode(mode)
        profile = manager.profile
        print(f"\n  {mode.value.upper()}:")
        print(f"    Process interval: {profile.process_interval}s")
        print(f"    Batch size: {profile.batch_size}")
        print(f"    Full analysis: {profile.enable_full_analysis}")
        print(f"    Sleep between: {profile.sleep_between_msgs}s")

    # Test message queue
    print("\n[Test 3] Message Queue")
    manager.set_mode(PowerMode.BALANCED)

    # Queue some messages
    manager.queue_message("Normal message 1", "peer_001", priority=0)
    manager.queue_message("URGENTE mensaje!", "peer_002", priority=5)
    manager.queue_message("Normal message 2", "peer_001", priority=0)
    manager.queue_message("Another urgent", "peer_003", priority=5)

    print(f"  Queued: {manager.queue.size()} messages")

    # Process batch
    results = manager.process_batch()
    print(f"  Processed: {len(results)} messages")

    for r in results:
        print(f"    {r['sender_id']}: risk={r['quick_risk']:.2f}, level={r['level']}")

    # Stats
    print("\n[Test 4] Stats")
    stats = manager.get_stats()
    print(f"  Mode: {stats['mode']}")
    print(f"  Messages processed: {stats['messages_processed']}")
    print(f"  Quick checks: {stats['quick_checks']}")
    print(f"  Full analyses: {stats['full_analyses']}")
    print(f"  Full analysis rate: {stats['full_analysis_rate']:.1%}")

    # Battery simulation
    print("\n[Test 5] Battery Auto-Switch")
    battery = BatteryMonitor(manager)

    test_levels = [(1.0, True), (0.8, False), (0.5, False), (0.2, False)]
    for level, charging in test_levels:
        battery.update(level, charging)
        print(f"  Battery: {level:.0%}, Charging: {charging} -> Mode: {manager.mode.value}")

    print("\n" + "="*70)
    print(" LOW-POWER TESTS COMPLETE")
    print("="*70)
