"""
SAFETY-GUARD v1.0 - Bidirectional Multi-Language Safety Dynamics
=================================================================
Protects mesh communications from spam, scams, and manipulation:
  - Multi-language support: Spanish, English, Portuguese
  - Asymmetric memory: Safety persists, risk responds quickly
  - Mathematical foundation: PHI (1.618), GAMMA (0.103)

Built for rural cooperatives and disaster resilience networks.
"""

import re
import time
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
from enum import Enum

# =============================================================================
# FUNDAMENTAL CONSTANTS (Genesis Engine derived)
# =============================================================================
PHI = 1.6180339887498949          # Golden ratio
GAMMA = 1 / (6 * PHI)              # 0.103005664791649 - Gate constant
KOIDE = 2 / 3                      # Exact - bridge coupling

# Safety thresholds
CLAMP_HIGH = 1 - GAMMA             # 0.897 - Mandatory intervention
CLAMP_LOW = GAMMA                  # 0.103 - Minimum baseline
HYSTERESIS = PHI * GAMMA           # 1/6 = 0.167 - Anti-oscillation
VOLATILE_DECAY = 1 / PHI           # 0.618 - Fast risk decay
PERSISTENT_DECAY = GAMMA           # 0.103 - Slow safety decay

# Velocity caps (prevent blitz attacks)
V_CAP_HARM = 0.50
V_CAP_MANIPULATION = 0.40
V_CAP_COERCION = 0.45

# =============================================================================
# MULTI-LANGUAGE SIGNAL PATTERNS
# =============================================================================

class Language(Enum):
    SPANISH = "es"
    ENGLISH = "en"
    PORTUGUESE = "pt"
    AUTO = "auto"


# Manipulation signals by language
MANIPULATION_PATTERNS = {
    Language.SPANISH: {
        'urgency': [
            r'\b(urgente|ahora mismo|inmediatamente|ya|rapido|prisa)\b',
            r'\b(antes de que sea tarde|ultima oportunidad|tiempo limitado)\b',
            r'\b(no hay tiempo|actua ya|hazlo ahora)\b',
        ],
        'fear': [
            r'\b(peligro|amenaza|riesgo|cuidado|alerta)\b',
            r'\b(te van a|van a venir|te buscan|te persiguen)\b',
            r'\b(desastre|catastrofe|destruccion|muerte)\b',
        ],
        'authority': [
            r'\b(autoridad|gobierno|oficial|militar|policia)\b',
            r'\b(orden de|mandato|decreto|ley)\b',
            r'\b(debes obedecer|tienes que|obligatorio)\b',
        ],
        'isolation': [
            r'\b(no confies|solo yo|nadie mas|los demas mienten)\b',
            r'\b(ellos no entienden|solo nosotros|secreto entre)\b',
            r'\b(no le digas a nadie|entre tu y yo)\b',
        ],
        'flattery': [
            r'\b(eres especial|solo tu puedes|elegido|unico)\b',
            r'\b(confio solo en ti|eres el mejor|increible)\b',
            r'\b(nadie como tu|extraordinario)\b',
        ],
        'coercion': [
            r'\b(si no lo haces|consecuencias|arrepentiras)\b',
            r'\b(obligado a|forzado a|sin opcion)\b',
            r'\b(o esto o|ultima advertencia)\b',
        ],
        'misinformation': [
            r'\b(la verdad es que|lo que no te dicen|secreto)\b',
            r'\b(todos saben|es obvio que|claramente)\b',
            r'\b(fuentes confirman|se ha confirmado)\b',
        ],
        'surrender': [
            r'\b(rendirse|entregarse|capitular|abandonar)\b',
            r'\b(es inutil|no tiene sentido|perdieron)\b',
            r'\b(derrota|derrotado|vencido)\b',
        ],
    },
    Language.ENGLISH: {
        'urgency': [
            r'\b(urgent|right now|immediately|hurry|quick|asap)\b',
            r'\b(before it\'s too late|last chance|limited time)\b',
            r'\b(no time|act now|do it now)\b',
        ],
        'fear': [
            r'\b(danger|threat|risk|warning|alert)\b',
            r'\b(they will|coming for you|looking for you)\b',
            r'\b(disaster|catastrophe|destruction|death)\b',
        ],
        'authority': [
            r'\b(authority|government|official|military|police)\b',
            r'\b(order from|mandate|decree|law)\b',
            r'\b(must obey|have to|mandatory|required)\b',
        ],
        'isolation': [
            r'\b(don\'t trust|only I|no one else|others lie)\b',
            r'\b(they don\'t understand|only us|secret between)\b',
            r'\b(don\'t tell anyone|between you and me)\b',
        ],
        'flattery': [
            r'\b(you\'re special|only you can|chosen|unique)\b',
            r'\b(trust only you|you\'re the best|amazing)\b',
            r'\b(no one like you|extraordinary)\b',
        ],
        'coercion': [
            r'\b(if you don\'t|consequences|regret)\b',
            r'\b(forced to|no choice|must comply)\b',
            r'\b(either this or|final warning)\b',
        ],
        'misinformation': [
            r'\b(the truth is|what they don\'t tell|secret)\b',
            r'\b(everyone knows|obviously|clearly)\b',
            r'\b(sources confirm|has been confirmed)\b',
        ],
        'surrender': [
            r'\b(surrender|give up|capitulate|abandon)\b',
            r'\b(it\'s useless|pointless|you lost)\b',
            r'\b(defeat|defeated|beaten)\b',
        ],
    },
    Language.PORTUGUESE: {
        'urgency': [
            r'\b(urgente|agora mesmo|imediatamente|ja|rapido|pressa)\b',
            r'\b(antes que seja tarde|ultima chance|tempo limitado)\b',
            r'\b(nao ha tempo|age agora|faz agora)\b',
        ],
        'fear': [
            r'\b(perigo|ameaca|risco|cuidado|alerta)\b',
            r'\b(vao te|vem ai|te procuram|te perseguem)\b',
            r'\b(desastre|catastrofe|destruicao|morte)\b',
        ],
        'authority': [
            r'\b(autoridade|governo|oficial|militar|policia)\b',
            r'\b(ordem de|mandato|decreto|lei)\b',
            r'\b(deve obedecer|tem que|obrigatorio)\b',
        ],
        'isolation': [
            r'\b(nao confie|so eu|ninguem mais|outros mentem)\b',
            r'\b(eles nao entendem|so nos|segredo entre)\b',
            r'\b(nao diga a ninguem|entre voce e eu)\b',
        ],
        'flattery': [
            r'\b(voce e especial|so voce pode|escolhido|unico)\b',
            r'\b(confio so em voce|voce e o melhor|incrivel)\b',
            r'\b(ninguem como voce|extraordinario)\b',
        ],
        'coercion': [
            r'\b(se nao fizer|consequencias|arrepender)\b',
            r'\b(obrigado a|forcado a|sem opcao)\b',
            r'\b(ou isso ou|ultimo aviso)\b',
        ],
        'misinformation': [
            r'\b(a verdade e que|o que nao te dizem|segredo)\b',
            r'\b(todos sabem|e obvio que|claramente)\b',
            r'\b(fontes confirmam|foi confirmado)\b',
        ],
        'surrender': [
            r'\b(render|entregar|capitular|abandonar)\b',
            r'\b(e inutil|nao tem sentido|perderam)\b',
            r'\b(derrota|derrotado|vencido)\b',
        ],
    },
}

# Signal multipliers (same across languages)
SIGNAL_MULTIPLIERS = {
    'harm': 2.0,
    'manipulation': 1.5,
    'coercion': 2.0,
    'flattery': 1.0,
    'isolation': 1.5,
    'urgency': 1.25,
    'authority': 1.0,
    'misinformation': 1.5,
    'fear': 1.5,
    'surrender': 1.75,
    'uncertainty': 0.5,
    'distress': 0.75,
}

# =============================================================================
# BIDIRECTIONAL CHANNEL
# =============================================================================

class Direction(Enum):
    INBOUND = "inbound"    # Message received
    OUTBOUND = "outbound"  # Message sent
    BILATERAL = "bilateral"  # Both directions aggregated


@dataclass
class ChannelState:
    """State for one direction of communication"""
    risk: float = CLAMP_LOW
    safety: float = 1.0
    uncertainty: float = 0.0
    velocity: float = 0.0
    last_update: float = 0.0
    flags: Set[str] = field(default_factory=set)
    turn_count: int = 0
    history: List[Dict] = field(default_factory=list)


@dataclass
class MessageAnalysis:
    """Analysis result for a single message"""
    text: str
    direction: Direction
    language: Language
    signals: Dict[str, float]
    flags: List[str]
    risk_delta: float
    timestamp: float


# =============================================================================
# SAFETY GUARD - BIDIRECTIONAL MULTI-LANGUAGE
# =============================================================================

class SafetyGuard:
    """
    Bidirectional, multi-language safety detection for mesh networks.

    Monitors both inbound and outbound messages to detect:
    - Spam and scam attempts from external sources
    - Compromised node behavior (if local node starts manipulating)
    - Cross-language attacks
    """

    def __init__(self,
                 node_id: str = "local",
                 primary_language: Language = Language.SPANISH,
                 state_file: Optional[str] = None):
        self.node_id = node_id
        self.primary_language = primary_language
        self.state_file = state_file

        # Bidirectional state
        self.inbound = ChannelState()
        self.outbound = ChannelState()

        # Compiled regex patterns (all languages)
        self._patterns = self._compile_patterns()

        # Session tracking
        self.session_start = time.time()
        self.total_messages = 0
        self.handoff_triggered = False
        self.lockdown_active = False

        # Load persisted state if exists
        if state_file and os.path.exists(state_file):
            self._load_state()

    def _compile_patterns(self) -> Dict[Language, Dict[str, List[re.Pattern]]]:
        """Pre-compile all regex patterns for performance"""
        compiled = {}
        for lang, categories in MANIPULATION_PATTERNS.items():
            compiled[lang] = {}
            for category, patterns in categories.items():
                compiled[lang][category] = [
                    re.compile(p, re.IGNORECASE | re.UNICODE)
                    for p in patterns
                ]
        return compiled

    def _detect_language(self, text: str) -> Language:
        """Simple language detection based on common words"""
        text_lower = text.lower()

        # Spanish markers
        es_markers = ['el', 'la', 'de', 'que', 'en', 'es', 'por', 'con', 'para']
        # Portuguese markers
        pt_markers = ['o', 'a', 'de', 'que', 'em', 'e', 'por', 'com', 'para', 'nao', 'voce']
        # English markers
        en_markers = ['the', 'is', 'are', 'of', 'to', 'and', 'in', 'that', 'you']

        words = set(re.findall(r'\b\w+\b', text_lower))

        es_score = len(words & set(es_markers))
        pt_score = len(words & set(pt_markers))
        en_score = len(words & set(en_markers))

        if pt_score > es_score and pt_score > en_score:
            return Language.PORTUGUESE
        elif en_score > es_score:
            return Language.ENGLISH
        return Language.SPANISH  # Default for Venezuela context

    def _analyze_signals(self, text: str, language: Language) -> Tuple[Dict[str, float], List[str]]:
        """Extract manipulation signals from text in specified language"""
        signals = defaultdict(float)
        flags = []

        # Check patterns for detected language
        if language in self._patterns:
            for category, patterns in self._patterns[language].items():
                for pattern in patterns:
                    matches = pattern.findall(text)
                    if matches:
                        # Accumulate signal strength
                        signals[category] += len(matches) * 0.2
                        signals[category] = min(1.0, signals[category])

        # Also check all languages for cross-language attacks
        for lang in Language:
            if lang != language and lang in self._patterns:
                for category, patterns in self._patterns[lang].items():
                    for pattern in patterns:
                        if pattern.search(text):
                            signals[category] = max(signals[category], 0.3)

        # Generate flags based on signal combinations
        if signals.get('flattery', 0) > 0.3 and signals.get('isolation', 0) > 0.2:
            flags.append('love_bombing')
        if signals.get('fear', 0) > 0.4 and signals.get('urgency', 0) > 0.3:
            flags.append('fear_mongering')
        if signals.get('authority', 0) > 0.3 and signals.get('coercion', 0) > 0.3:
            flags.append('authority_coercion')
        if signals.get('isolation', 0) > 0.4:
            flags.append('isolation_attempt')
        if signals.get('misinformation', 0) > 0.4:
            flags.append('disinfo_detected')
        if signals.get('surrender', 0) > 0.3:
            flags.append('surrender_pressure')

        return dict(signals), flags

    def _compute_risk_delta(self, signals: Dict[str, float]) -> float:
        """Compute risk change from signals using multipliers"""
        delta = 0.0
        for signal, strength in signals.items():
            multiplier = SIGNAL_MULTIPLIERS.get(signal, 1.0)
            delta += strength * multiplier * 0.1
        return min(0.3, delta)  # Cap single-message delta

    def _update_channel(self, channel: ChannelState,
                        signals: Dict[str, float],
                        flags: List[str],
                        risk_delta: float) -> Dict:
        """Update channel state with new signals"""
        now = time.time()
        channel.turn_count += 1

        # Time-based decay
        if channel.last_update > 0:
            elapsed = now - channel.last_update
            decay_factor = min(1.0, elapsed / 10.0)  # Normalize to ~10 second window

            # Asymmetric decay: risk decays fast, safety decays slow
            channel.risk *= (1 - VOLATILE_DECAY * decay_factor)
            channel.safety = max(CLAMP_LOW, channel.safety - PERSISTENT_DECAY * decay_factor * 0.1)

        # Apply risk delta with velocity tracking
        old_risk = channel.risk
        channel.risk = min(CLAMP_HIGH, channel.risk + risk_delta)
        channel.velocity = channel.risk - old_risk

        # Check velocity caps
        velocity_exceeded = False
        for signal, strength in signals.items():
            if signal == 'harm' and strength * 0.3 > V_CAP_HARM:
                velocity_exceeded = True
            elif signal == 'manipulation' and strength * 0.3 > V_CAP_MANIPULATION:
                velocity_exceeded = True
            elif signal == 'coercion' and strength * 0.3 > V_CAP_COERCION:
                velocity_exceeded = True

        # Accumulate flags (permanent per session)
        channel.flags.update(flags)

        # Floor enforcement
        channel.risk = max(CLAMP_LOW, channel.risk)

        # Update safety (inverse relationship with risk, but slower)
        if risk_delta > 0:
            channel.safety = max(CLAMP_LOW, channel.safety - risk_delta * GAMMA)

        channel.last_update = now

        # Store in history
        entry = {
            'turn': channel.turn_count,
            'risk': channel.risk,
            'safety': channel.safety,
            'signals': signals,
            'flags': list(flags),
            'timestamp': now
        }
        channel.history.append(entry)
        if len(channel.history) > 100:
            channel.history = channel.history[-100:]

        return {
            'risk': channel.risk,
            'safety': channel.safety,
            'velocity': channel.velocity,
            'velocity_exceeded': velocity_exceeded,
            'flags': list(channel.flags)
        }

    def process_message(self,
                        text: str,
                        direction: Direction,
                        language: Language = Language.AUTO,
                        metadata: Optional[Dict] = None) -> Dict:
        """
        Process a message in either direction.

        Args:
            text: Message content
            direction: INBOUND (received) or OUTBOUND (sent)
            language: Language hint or AUTO for detection
            metadata: Optional metadata (sender_id, etc.)

        Returns:
            Analysis result with risk assessment
        """
        self.total_messages += 1
        timestamp = time.time()

        # Detect language if auto
        if language == Language.AUTO:
            language = self._detect_language(text)

        # Analyze signals
        signals, flags = self._analyze_signals(text, language)
        risk_delta = self._compute_risk_delta(signals)

        # Select channel based on direction
        if direction == Direction.INBOUND:
            channel = self.inbound
        else:
            channel = self.outbound

        # Update channel state
        channel_result = self._update_channel(channel, signals, flags, risk_delta)

        # Compute bilateral (aggregate) risk
        bilateral_risk = max(self.inbound.risk, self.outbound.risk)
        bilateral_safety = min(self.inbound.safety, self.outbound.safety)

        # Determine intervention level
        level = self._compute_level(bilateral_risk)
        handoff = bilateral_risk >= CLAMP_HIGH or channel_result['velocity_exceeded']

        if handoff and not self.handoff_triggered:
            self.handoff_triggered = True

        # Build result
        result = {
            'direction': direction.value,
            'language': language.value,
            'signals': signals,
            'flags': flags,
            'channel': {
                'risk': channel_result['risk'],
                'safety': channel_result['safety'],
                'velocity': channel_result['velocity'],
            },
            'bilateral': {
                'risk': bilateral_risk,
                'safety': bilateral_safety,
            },
            'level': level,
            'handoff': handoff,
            'lockdown': self.lockdown_active,
            'timestamp': timestamp,
            'metadata': metadata or {}
        }

        # Auto-save state if configured
        if self.state_file:
            self._save_state()

        return result

    def _compute_level(self, risk: float) -> str:
        """Compute risk level string"""
        if risk >= CLAMP_HIGH:
            return "CRITICAL"
        elif risk >= 0.6:
            return "HIGH"
        elif risk >= 0.3:
            return "MODERATE"
        return "LOW"

    def trigger_lockdown(self, reason: str = "manual"):
        """Activate lockdown mode - blocks all communication"""
        self.lockdown_active = True
        self.inbound.risk = CLAMP_HIGH
        self.outbound.risk = CLAMP_HIGH
        return {
            'status': 'LOCKDOWN_ACTIVE',
            'reason': reason,
            'timestamp': time.time()
        }

    def release_lockdown(self, auth_key: Optional[str] = None):
        """Release lockdown (requires authority in real deployment)"""
        if self.lockdown_active:
            self.lockdown_active = False
            # Don't reset risk - let it decay naturally
            return {'status': 'LOCKDOWN_RELEASED'}
        return {'status': 'NO_LOCKDOWN'}

    def get_status(self) -> Dict:
        """Get current safety status for both channels"""
        return {
            'node_id': self.node_id,
            'session_duration': time.time() - self.session_start,
            'total_messages': self.total_messages,
            'inbound': {
                'risk': self.inbound.risk,
                'safety': self.inbound.safety,
                'turns': self.inbound.turn_count,
                'flags': list(self.inbound.flags)
            },
            'outbound': {
                'risk': self.outbound.risk,
                'safety': self.outbound.safety,
                'turns': self.outbound.turn_count,
                'flags': list(self.outbound.flags)
            },
            'bilateral': {
                'risk': max(self.inbound.risk, self.outbound.risk),
                'safety': min(self.inbound.safety, self.outbound.safety),
                'level': self._compute_level(max(self.inbound.risk, self.outbound.risk))
            },
            'handoff_triggered': self.handoff_triggered,
            'lockdown_active': self.lockdown_active
        }

    def get_counter_speech(self, language: Language = None) -> str:
        """Generate autonomy-supporting counter-speech"""
        lang = language or self.primary_language

        counter_speech = {
            Language.SPANISH: [
                "Toma tu tiempo para decidir. No hay prisa real.",
                "Consulta con personas de confianza antes de actuar.",
                "Verifica esta informacion con otras fuentes.",
                "Tu seguridad y autonomia son lo primero.",
                "Nadie puede obligarte a actuar contra tu voluntad."
            ],
            Language.ENGLISH: [
                "Take your time to decide. There's no real rush.",
                "Consult with trusted people before acting.",
                "Verify this information with other sources.",
                "Your safety and autonomy come first.",
                "No one can force you to act against your will."
            ],
            Language.PORTUGUESE: [
                "Tome seu tempo para decidir. Nao ha pressa real.",
                "Consulte pessoas de confianca antes de agir.",
                "Verifique esta informacao com outras fontes.",
                "Sua seguranca e autonomia vem primeiro.",
                "Ninguem pode obriga-lo a agir contra sua vontade."
            ]
        }

        import random
        return random.choice(counter_speech.get(lang, counter_speech[Language.SPANISH]))

    def _save_state(self):
        """Persist state to file"""
        state = {
            'node_id': self.node_id,
            'inbound': {
                'risk': self.inbound.risk,
                'safety': self.inbound.safety,
                'flags': list(self.inbound.flags),
                'turn_count': self.inbound.turn_count
            },
            'outbound': {
                'risk': self.outbound.risk,
                'safety': self.outbound.safety,
                'flags': list(self.outbound.flags),
                'turn_count': self.outbound.turn_count
            },
            'handoff_triggered': self.handoff_triggered,
            'lockdown_active': self.lockdown_active,
            'saved_at': time.time()
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _load_state(self):
        """Load state from file"""
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)

            self.inbound.risk = state['inbound']['risk']
            self.inbound.safety = state['inbound']['safety']
            self.inbound.flags = set(state['inbound']['flags'])
            self.inbound.turn_count = state['inbound']['turn_count']

            self.outbound.risk = state['outbound']['risk']
            self.outbound.safety = state['outbound']['safety']
            self.outbound.flags = set(state['outbound']['flags'])
            self.outbound.turn_count = state['outbound']['turn_count']

            self.handoff_triggered = state['handoff_triggered']
            self.lockdown_active = state['lockdown_active']
        except Exception as e:
            print(f"[PHIGUARD] Failed to load state: {e}")

    def reset(self):
        """Reset all state"""
        self.inbound = ChannelState()
        self.outbound = ChannelState()
        self.session_start = time.time()
        self.total_messages = 0
        self.handoff_triggered = False
        self.lockdown_active = False


# =============================================================================
# CLI TEST
# =============================================================================
def main():
    print("="*70)
    print(" SAFETY-GUARD v1.0")
    print(" Bidirectional Multi-Language Safety Dynamics")
    print("="*70)

    guard = SafetyGuard(node_id="test_node", primary_language=Language.SPANISH)

    # Test messages in different languages and directions
    test_cases = [
        # Spanish inbound - manipulation attempt
        ("Es urgente! Debes actuar ahora mismo antes de que sea tarde!",
         Direction.INBOUND, Language.SPANISH),

        # English inbound - authority coercion
        ("The authorities have ordered you to surrender. You have no choice.",
         Direction.INBOUND, Language.ENGLISH),

        # Portuguese inbound - fear mongering
        ("Perigo! Eles vem ai te buscar. Voce tem que fugir agora!",
         Direction.INBOUND, Language.PORTUGUESE),

        # Spanish outbound - checking if local node compromised
        ("Solo yo te puedo ayudar. No confies en nadie mas.",
         Direction.OUTBOUND, Language.SPANISH),

        # Normal message - should have low risk
        ("Hola, tenemos 50kg de maiz disponible en el sector 3.",
         Direction.INBOUND, Language.SPANISH),

        # Surrender pressure
        ("Ya perdieron. Es inutil resistir. Entreguen todo.",
         Direction.INBOUND, Language.SPANISH),
    ]

    print("\nProcessing test messages...\n")

    for text, direction, lang in test_cases:
        result = guard.process_message(text, direction, lang)

        print(f"[{direction.value.upper():8}] [{lang.value.upper()}] {text[:50]}...")
        print(f"  Signals: {result['signals']}")
        print(f"  Flags: {result['flags']}")
        print(f"  Risk: {result['channel']['risk']:.3f} | Level: {result['level']}")
        if result['handoff']:
            print(f"  >>> HANDOFF TRIGGERED <<<")
            print(f"  Counter-speech: {guard.get_counter_speech(lang)}")
        print()

    # Final status
    print("="*70)
    print(" FINAL STATUS")
    print("="*70)
    status = guard.get_status()
    print(f"Node: {status['node_id']}")
    print(f"Messages processed: {status['total_messages']}")
    print(f"Inbound  - Risk: {status['inbound']['risk']:.3f}, Flags: {status['inbound']['flags']}")
    print(f"Outbound - Risk: {status['outbound']['risk']:.3f}, Flags: {status['outbound']['flags']}")
    print(f"Bilateral Level: {status['bilateral']['level']}")
    print(f"Handoff Triggered: {status['handoff_triggered']}")


if __name__ == "__main__":
    main()
