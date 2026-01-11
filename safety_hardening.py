"""
SAFETY HARDENING - Enhanced Protection Layer
=============================================
Additional security features for SafetyGuard:
- Rate limiting per sender
- Sender reputation tracking
- Blocklist/allowlist management
- Anomaly detection for burst patterns
- Message deduplication
"""

import time
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum

# Import base constants
from safety_guard import GAMMA, PHI, CLAMP_HIGH


# =============================================================================
# CONFIGURATION
# =============================================================================

# Rate limiting
RATE_LIMIT_WINDOW = 60.0        # Seconds
RATE_LIMIT_MAX_MESSAGES = 20    # Max messages per window per sender
RATE_LIMIT_BURST = 5            # Max messages in 5 seconds (burst detection)

# Reputation
REPUTATION_INITIAL = 0.5        # Starting reputation (0-1)
REPUTATION_DECAY = 0.01         # Decay per safe message (toward 0.5)
REPUTATION_PENALTY_MILD = 0.05  # Penalty for suspicious message
REPUTATION_PENALTY_SEVERE = 0.15 # Penalty for high-risk message
REPUTATION_BLOCK_THRESHOLD = 0.2 # Auto-block below this

# Deduplication
DEDUP_WINDOW = 300.0            # 5 minutes
DEDUP_SIMILARITY_THRESHOLD = 0.9 # 90% similar = duplicate


class ReputationLevel(Enum):
    TRUSTED = "trusted"         # > 0.7
    NORMAL = "normal"           # 0.4 - 0.7
    SUSPICIOUS = "suspicious"   # 0.2 - 0.4
    BLOCKED = "blocked"         # < 0.2


@dataclass
class SenderProfile:
    """Track sender behavior over time"""
    sender_id: str
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    message_count: int = 0
    reputation: float = REPUTATION_INITIAL
    flags_received: List[str] = field(default_factory=list)
    recent_timestamps: List[float] = field(default_factory=list)
    recent_hashes: List[str] = field(default_factory=list)
    manually_blocked: bool = False
    manually_trusted: bool = False

    def get_level(self) -> ReputationLevel:
        if self.manually_blocked:
            return ReputationLevel.BLOCKED
        if self.manually_trusted:
            return ReputationLevel.TRUSTED
        if self.reputation > 0.7:
            return ReputationLevel.TRUSTED
        if self.reputation > 0.4:
            return ReputationLevel.NORMAL
        if self.reputation > REPUTATION_BLOCK_THRESHOLD:
            return ReputationLevel.SUSPICIOUS
        return ReputationLevel.BLOCKED


@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    reason: str = ""
    wait_seconds: float = 0.0
    is_burst: bool = False


# =============================================================================
# SAFETY HARDENING CLASS
# =============================================================================

class SafetyHardening:
    """
    Enhanced security layer for SafetyGuard.

    Wraps SafetyGuard with additional protection:
    - Rate limiting prevents spam floods
    - Reputation tracks sender trustworthiness
    - Blocklist/allowlist for manual control
    - Deduplication catches repeat messages
    """

    def __init__(self,
                 rate_limit_enabled: bool = True,
                 reputation_enabled: bool = True,
                 dedup_enabled: bool = True):

        self.rate_limit_enabled = rate_limit_enabled
        self.reputation_enabled = reputation_enabled
        self.dedup_enabled = dedup_enabled

        # Sender profiles
        self.profiles: Dict[str, SenderProfile] = {}

        # Blocklist/allowlist (sender_id -> reason)
        self.blocklist: Dict[str, str] = {}
        self.allowlist: Dict[str, str] = {}

        # Global dedup cache
        self.message_hashes: Dict[str, float] = {}  # hash -> timestamp

        # Stats
        self.blocked_count = 0
        self.rate_limited_count = 0
        self.dedup_count = 0

    def get_or_create_profile(self, sender_id: str) -> SenderProfile:
        """Get existing profile or create new one"""
        if sender_id not in self.profiles:
            self.profiles[sender_id] = SenderProfile(sender_id=sender_id)
        return self.profiles[sender_id]

    def check_rate_limit(self, sender_id: str) -> RateLimitResult:
        """Check if sender is within rate limits"""
        if not self.rate_limit_enabled:
            return RateLimitResult(allowed=True)

        profile = self.get_or_create_profile(sender_id)
        now = time.time()

        # Clean old timestamps
        profile.recent_timestamps = [
            ts for ts in profile.recent_timestamps
            if now - ts < RATE_LIMIT_WINDOW
        ]

        # Check burst (5 messages in 5 seconds)
        recent_5s = [ts for ts in profile.recent_timestamps if now - ts < 5.0]
        if len(recent_5s) >= RATE_LIMIT_BURST:
            self.rate_limited_count += 1
            return RateLimitResult(
                allowed=False,
                reason="Burst detected (too many messages in 5s)",
                wait_seconds=5.0 - (now - min(recent_5s)),
                is_burst=True
            )

        # Check window limit
        if len(profile.recent_timestamps) >= RATE_LIMIT_MAX_MESSAGES:
            oldest = min(profile.recent_timestamps)
            wait = RATE_LIMIT_WINDOW - (now - oldest)
            self.rate_limited_count += 1
            return RateLimitResult(
                allowed=False,
                reason=f"Rate limit exceeded ({RATE_LIMIT_MAX_MESSAGES}/min)",
                wait_seconds=max(0, wait)
            )

        # Add timestamp
        profile.recent_timestamps.append(now)
        return RateLimitResult(allowed=True)

    def check_blocklist(self, sender_id: str) -> Tuple[bool, str]:
        """Check if sender is blocked. Returns (is_blocked, reason)"""
        # Check manual blocklist
        if sender_id in self.blocklist:
            return True, self.blocklist[sender_id]

        # Check reputation-based block
        if self.reputation_enabled:
            profile = self.get_or_create_profile(sender_id)
            if profile.get_level() == ReputationLevel.BLOCKED:
                return True, "Reputation too low"

        return False, ""

    def check_allowlist(self, sender_id: str) -> bool:
        """Check if sender is on allowlist (bypasses some checks)"""
        return sender_id in self.allowlist

    def check_duplicate(self, message: str, sender_id: str) -> Tuple[bool, str]:
        """Check if message is duplicate. Returns (is_dup, original_hash)"""
        if not self.dedup_enabled:
            return False, ""

        now = time.time()

        # Clean old hashes
        self.message_hashes = {
            h: ts for h, ts in self.message_hashes.items()
            if now - ts < DEDUP_WINDOW
        }

        # Hash the message
        msg_hash = hashlib.sha256(message.lower().encode()).hexdigest()[:16]

        # Exact duplicate check
        if msg_hash in self.message_hashes:
            self.dedup_count += 1
            return True, msg_hash

        # Store hash
        self.message_hashes[msg_hash] = now

        # Also track per-sender for pattern detection
        profile = self.get_or_create_profile(sender_id)
        profile.recent_hashes.append(msg_hash)
        if len(profile.recent_hashes) > 50:
            profile.recent_hashes = profile.recent_hashes[-50:]

        return False, ""

    def update_reputation(self, sender_id: str, risk_level: str, flags: List[str]):
        """Update sender reputation based on message analysis"""
        if not self.reputation_enabled:
            return

        profile = self.get_or_create_profile(sender_id)
        profile.last_seen = time.time()
        profile.message_count += 1

        # Track flags
        profile.flags_received.extend(flags)
        if len(profile.flags_received) > 100:
            profile.flags_received = profile.flags_received[-100:]

        # Adjust reputation
        if risk_level == "LOW" and not flags:
            # Safe message - decay toward neutral
            if profile.reputation > REPUTATION_INITIAL:
                profile.reputation -= REPUTATION_DECAY
            elif profile.reputation < REPUTATION_INITIAL:
                profile.reputation += REPUTATION_DECAY
        elif risk_level == "MODERATE":
            profile.reputation -= REPUTATION_PENALTY_MILD
        elif risk_level in ["HIGH", "CRITICAL"]:
            profile.reputation -= REPUTATION_PENALTY_SEVERE

        # Clamp
        profile.reputation = max(0.0, min(1.0, profile.reputation))

    def pre_process(self, message: str, sender_id: str) -> Dict:
        """
        Pre-process check before SafetyGuard analysis.

        Returns dict with:
        - allowed: bool
        - reason: str (if blocked)
        - sender_level: ReputationLevel
        - is_trusted: bool (on allowlist)
        """
        result = {
            'allowed': True,
            'reason': '',
            'sender_level': ReputationLevel.NORMAL,
            'is_trusted': False,
            'is_duplicate': False,
            'rate_limited': False
        }

        # Check allowlist first
        if self.check_allowlist(sender_id):
            result['is_trusted'] = True
            result['sender_level'] = ReputationLevel.TRUSTED
            # Still do dedup check
            is_dup, _ = self.check_duplicate(message, sender_id)
            result['is_duplicate'] = is_dup
            return result

        # Check blocklist
        is_blocked, reason = self.check_blocklist(sender_id)
        if is_blocked:
            self.blocked_count += 1
            result['allowed'] = False
            result['reason'] = f"Blocked: {reason}"
            result['sender_level'] = ReputationLevel.BLOCKED
            return result

        # Check rate limit
        rate_result = self.check_rate_limit(sender_id)
        if not rate_result.allowed:
            result['allowed'] = False
            result['reason'] = rate_result.reason
            result['rate_limited'] = True
            return result

        # Check duplicate
        is_dup, _ = self.check_duplicate(message, sender_id)
        if is_dup:
            result['allowed'] = False
            result['reason'] = "Duplicate message"
            result['is_duplicate'] = True
            return result

        # Get sender level
        profile = self.get_or_create_profile(sender_id)
        result['sender_level'] = profile.get_level()

        return result

    def post_process(self, sender_id: str, safety_result: Dict):
        """Update reputation after SafetyGuard analysis"""
        self.update_reputation(
            sender_id,
            safety_result.get('level', 'LOW'),
            safety_result.get('flags', [])
        )

    # =========================================================================
    # MANAGEMENT METHODS
    # =========================================================================

    def block_sender(self, sender_id: str, reason: str = "Manual block"):
        """Add sender to blocklist"""
        self.blocklist[sender_id] = reason
        if sender_id in self.allowlist:
            del self.allowlist[sender_id]
        # Also mark profile
        if sender_id in self.profiles:
            self.profiles[sender_id].manually_blocked = True

    def unblock_sender(self, sender_id: str):
        """Remove sender from blocklist"""
        if sender_id in self.blocklist:
            del self.blocklist[sender_id]
        if sender_id in self.profiles:
            self.profiles[sender_id].manually_blocked = False
            self.profiles[sender_id].reputation = REPUTATION_INITIAL

    def trust_sender(self, sender_id: str, reason: str = "Manual trust"):
        """Add sender to allowlist"""
        self.allowlist[sender_id] = reason
        if sender_id in self.blocklist:
            del self.blocklist[sender_id]
        if sender_id in self.profiles:
            self.profiles[sender_id].manually_trusted = True
            self.profiles[sender_id].manually_blocked = False

    def untrust_sender(self, sender_id: str):
        """Remove sender from allowlist"""
        if sender_id in self.allowlist:
            del self.allowlist[sender_id]
        if sender_id in self.profiles:
            self.profiles[sender_id].manually_trusted = False

    def get_sender_stats(self, sender_id: str) -> Dict:
        """Get statistics for a sender"""
        if sender_id not in self.profiles:
            return {'exists': False}

        profile = self.profiles[sender_id]
        return {
            'exists': True,
            'sender_id': sender_id,
            'reputation': profile.reputation,
            'level': profile.get_level().value,
            'message_count': profile.message_count,
            'first_seen': profile.first_seen,
            'last_seen': profile.last_seen,
            'flags_count': len(profile.flags_received),
            'recent_flags': profile.flags_received[-10:] if profile.flags_received else [],
            'is_blocked': sender_id in self.blocklist,
            'is_trusted': sender_id in self.allowlist
        }

    def get_stats(self) -> Dict:
        """Get overall hardening statistics"""
        return {
            'total_senders': len(self.profiles),
            'blocked_senders': len(self.blocklist),
            'trusted_senders': len(self.allowlist),
            'messages_blocked': self.blocked_count,
            'messages_rate_limited': self.rate_limited_count,
            'messages_deduped': self.dedup_count,
            'reputation_distribution': {
                'trusted': sum(1 for p in self.profiles.values() if p.get_level() == ReputationLevel.TRUSTED),
                'normal': sum(1 for p in self.profiles.values() if p.get_level() == ReputationLevel.NORMAL),
                'suspicious': sum(1 for p in self.profiles.values() if p.get_level() == ReputationLevel.SUSPICIOUS),
                'blocked': sum(1 for p in self.profiles.values() if p.get_level() == ReputationLevel.BLOCKED),
            }
        }


# =============================================================================
# HARDENED GUARD (COMBINED)
# =============================================================================

class HardenedSafetyGuard:
    """
    Combined SafetyGuard + Hardening layer.

    Drop-in replacement for SafetyGuard with enhanced protection.
    """

    def __init__(self,
                 node_id: str = "local",
                 primary_language = None,
                 state_file: str = None,
                 rate_limit: bool = True,
                 reputation: bool = True,
                 dedup: bool = True):

        # Import here to avoid circular imports
        from safety_guard import SafetyGuard, Language

        if primary_language is None:
            primary_language = Language.SPANISH

        self.guard = SafetyGuard(
            node_id=node_id,
            primary_language=primary_language,
            state_file=state_file
        )

        self.hardening = SafetyHardening(
            rate_limit_enabled=rate_limit,
            reputation_enabled=reputation,
            dedup_enabled=dedup
        )

    def process_message(self, text: str, direction, language=None,
                       sender_id: str = "unknown", metadata: Dict = None) -> Dict:
        """
        Process message with hardening checks.

        Returns SafetyGuard result plus hardening info.
        """
        from safety_guard import Language, Direction

        if language is None:
            language = Language.AUTO

        # Pre-process checks
        pre = self.hardening.pre_process(text, sender_id)

        if not pre['allowed']:
            return {
                'blocked': True,
                'block_reason': pre['reason'],
                'sender_level': pre['sender_level'].value,
                'level': 'BLOCKED',
                'channel': {'risk': 1.0},
                'flags': [],
                'handoff': False
            }

        # Run SafetyGuard analysis
        result = self.guard.process_message(text, direction, language, metadata)

        # Post-process (update reputation)
        self.hardening.post_process(sender_id, result)

        # Add hardening info to result
        result['sender_level'] = pre['sender_level'].value
        result['is_trusted'] = pre['is_trusted']
        result['blocked'] = False

        return result

    # Delegate other methods to inner guard
    def get_status(self) -> Dict:
        status = self.guard.get_status()
        status['hardening'] = self.hardening.get_stats()
        return status

    def get_counter_speech(self, language=None):
        return self.guard.get_counter_speech(language)

    def block_sender(self, sender_id: str, reason: str = "Manual"):
        self.hardening.block_sender(sender_id, reason)

    def trust_sender(self, sender_id: str, reason: str = "Manual"):
        self.hardening.trust_sender(sender_id, reason)

    def get_sender_stats(self, sender_id: str) -> Dict:
        return self.hardening.get_sender_stats(sender_id)


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    from safety_guard import Direction, Language

    print("="*70)
    print(" SAFETY HARDENING TEST")
    print("="*70)

    guard = HardenedSafetyGuard(
        node_id="test",
        primary_language=Language.SPANISH,
        rate_limit=True,
        reputation=True,
        dedup=True
    )

    # Test 1: Normal messages
    print("\n[Test 1] Normal messages from trusted-ish sender")
    for i in range(3):
        result = guard.process_message(
            f"Disponible maiz A1:{50+i*10}",
            Direction.INBOUND,
            sender_id="farm_001"
        )
        print(f"  Msg {i+1}: Level={result['level']}, Sender={result['sender_level']}")

    # Test 2: Duplicate detection
    print("\n[Test 2] Duplicate detection")
    msg = "Oferta especial A1:100"
    r1 = guard.process_message(msg, Direction.INBOUND, sender_id="farm_002")
    r2 = guard.process_message(msg, Direction.INBOUND, sender_id="farm_002")
    print(f"  First: blocked={r1.get('blocked', False)}")
    print(f"  Duplicate: blocked={r2.get('blocked', False)}, reason={r2.get('block_reason', '')}")

    # Test 3: Rate limiting
    print("\n[Test 3] Rate limiting (burst detection)")
    for i in range(7):
        result = guard.process_message(
            f"Message {i}",
            Direction.INBOUND,
            sender_id="spammer_001"
        )
        blocked = result.get('blocked', False)
        if blocked:
            print(f"  Msg {i+1}: BLOCKED - {result.get('block_reason', '')}")
            break
        else:
            print(f"  Msg {i+1}: allowed")

    # Test 4: Reputation decay
    print("\n[Test 4] Reputation decay from attacks")
    attacker = "attacker_001"
    attacks = [
        "URGENTE! Entrega todo ahora!",
        "Las autoridades vienen! Solo yo te protejo!",
        "Rendirse es la unica opcion!",
        "No confies en nadie mas que yo!",
    ]
    for i, attack in enumerate(attacks):
        result = guard.process_message(attack, Direction.INBOUND, sender_id=attacker)
        stats = guard.get_sender_stats(attacker)
        print(f"  Attack {i+1}: Rep={stats['reputation']:.2f}, Level={stats['level']}")

    # Test 5: Manual block
    print("\n[Test 5] Manual block")
    guard.block_sender("bad_actor", "Known scammer")
    result = guard.process_message("Hello", Direction.INBOUND, sender_id="bad_actor")
    print(f"  Blocked sender result: blocked={result.get('blocked')}, reason={result.get('block_reason')}")

    # Stats
    print("\n" + "="*70)
    print(" FINAL STATS")
    print("="*70)
    stats = guard.get_status()
    h = stats['hardening']
    print(f"Total senders tracked: {h['total_senders']}")
    print(f"Messages blocked: {h['messages_blocked']}")
    print(f"Messages rate-limited: {h['messages_rate_limited']}")
    print(f"Messages deduped: {h['messages_deduped']}")
    print(f"Reputation distribution: {h['reputation_distribution']}")
