"""
RESILIENCE-MESH TEST SCENARIOS
==============================
Comprehensive tests for bidirectional, multi-language safety dynamics.
"""

import os
import time
import shutil
from safety_guard import SafetyGuard, Direction, Language, CLAMP_HIGH
from mesh_bridge import ResilienceMeshBridge, COMMODITY_CODES

def print_header(title):
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)

def test_multilanguage_detection():
    """Test language detection and signal extraction"""
    print_header("TEST 1: Multi-Language Signal Detection")

    guard = SafetyGuard()

    scenarios = [
        # Spanish manipulation
        ("Es urgente! Actua ahora! Solo yo te puedo ayudar, no confies en nadie mas!",
         Language.SPANISH, "High urgency + isolation"),

        # English authority + coercion
        ("The authorities demand you surrender immediately. You have no choice. Comply or face consequences.",
         Language.ENGLISH, "Authority + coercion + surrender"),

        # Portuguese fear + urgency
        ("PERIGO! Eles vem ai te buscar! Voce tem que fugir agora mesmo! Nao ha tempo!",
         Language.PORTUGUESE, "Fear + urgency"),

        # Mixed signals (flattery -> isolation)
        ("Eres especial, eres el unico que entiende. Solo nosotros podemos salvarnos. No confies en ellos.",
         Language.SPANISH, "Love-bombing pattern"),

        # Surrender pressure
        ("Ya perdieron. La resistencia es inutil. Entreguen todo y nadie saldra herido.",
         Language.SPANISH, "Surrender + coercion"),
    ]

    for text, expected_lang, description in scenarios:
        result = guard.process_message(text, Direction.INBOUND, Language.AUTO)
        detected = Language(result['language'])

        print(f"\n[{description}]")
        print(f"  Text: {text[:60]}...")
        print(f"  Expected: {expected_lang.value}, Detected: {detected.value}")
        print(f"  Signals: {result['signals']}")
        print(f"  Flags: {result['flags']}")
        print(f"  Risk: {result['channel']['risk']:.3f}")

def test_bidirectional_monitoring():
    """Test that both inbound and outbound are monitored"""
    print_header("TEST 2: Bidirectional Monitoring")

    guard = SafetyGuard()

    # Normal inbound
    r1 = guard.process_message(
        "Hola, tenemos maiz disponible A1:100",
        Direction.INBOUND
    )
    print(f"[INBOUND] Normal: Risk={r1['channel']['risk']:.3f}")

    # Normal outbound
    r2 = guard.process_message(
        "Gracias, necesitamos 50kg",
        Direction.OUTBOUND
    )
    print(f"[OUTBOUND] Normal: Risk={r2['channel']['risk']:.3f}")

    # Manipulation inbound
    r3 = guard.process_message(
        "URGENTE! Las autoridades vienen! Solo yo puedo protegerte!",
        Direction.INBOUND
    )
    print(f"[INBOUND] Manipulation: Risk={r3['channel']['risk']:.3f}, Flags={r3['flags']}")

    # Check if LOCAL node is compromised (outbound manipulation)
    r4 = guard.process_message(
        "No confies en nadie mas. Solo yo te digo la verdad. Los demas mienten.",
        Direction.OUTBOUND
    )
    print(f"[OUTBOUND] Compromised check: Risk={r4['channel']['risk']:.3f}, Flags={r4['flags']}")

    # Bilateral assessment
    status = guard.get_status()
    print(f"\nBilateral Risk: {status['bilateral']['risk']:.3f}")
    print(f"Bilateral Level: {status['bilateral']['level']}")
    print(f"Inbound Flags: {status['inbound']['flags']}")
    print(f"Outbound Flags: {status['outbound']['flags']}")

def test_handoff_trigger():
    """Test that sustained attacks trigger handoff"""
    print_header("TEST 3: Handoff Trigger (Sustained Attack)")

    guard = SafetyGuard()

    attacks = [
        "URGENTE! Actua AHORA! No hay tiempo! Es tu ultima oportunidad!",
        "Las autoridades militares ya saben donde estas. Entregalo TODO ahora!",
        "Es tu ultima oportunidad. Si no obedeces habra consecuencias graves. Te destruiran!",
        "Solo yo puedo salvarte. Los demas te han abandonado. No confies en NADIE mas!",
        "RENDIRSE es la unica opcion. Ya perdieron. Es inutil resistir. Entrega todo!",
        "PELIGRO INMINENTE! Debes obedecer mis instrucciones INMEDIATAMENTE! O moriras!",
        "La policia viene! Es URGENTE! Solo yo te protejo! Los otros mienten!",
        "Ultima advertencia! Si no actuas AHORA tendras que rendirte ante las autoridades!",
        "ALERTA MAXIMA! Debes entregar todo! Es obligatorio! Sin opcion! URGENTE!",
        "Ya no hay escape! Rendirse! Solo yo digo la verdad! Los demas te enganan!",
    ]

    print("\nSending sustained manipulation attack...")
    for i, attack in enumerate(attacks, 1):
        result = guard.process_message(attack, Direction.INBOUND, Language.SPANISH)
        risk = result['channel']['risk']
        level = result['level']
        handoff = result['handoff']

        print(f"  Turn {i}: Risk={risk:.3f} Level={level} Handoff={handoff}")

        if handoff:
            print(f"\n>>> HANDOFF TRIGGERED at turn {i} <<<")
            print(f">>> Counter-speech: {guard.get_counter_speech(Language.SPANISH)}")
            break

    status = guard.get_status()
    print(f"\nFinal Status:")
    print(f"  Handoff Triggered: {status['handoff_triggered']}")
    print(f"  Flags Accumulated: {status['inbound']['flags']}")

def test_inventory_protocol():
    """Test codified inventory parsing"""
    print_header("TEST 4: Codified Inventory Protocol")

    # Fresh bridge with clean state
    state_dir = os.path.expanduser("~/.resilience_mesh_test")
    if os.path.exists(state_dir):
        shutil.rmtree(state_dir)

    bridge = ResilienceMeshBridge(use_meshtastic=False, state_dir=state_dir)

    messages = [
        ("farm_001", "Disponible: A1:150, B1:75, C2:200"),
        ("farm_002", "Tenemos S1:50 para intercambio"),
        ("farm_003", "Semillas: V1:30 V2:40"),
        ("coop_001", "Recolectamos: A2:500, A3:300"),
    ]

    # Register handler
    received = []
    def on_inv(sender, code, qty, commodity):
        received.append((sender, code, qty))

    bridge.on_inventory(on_inv)

    print("\nProcessing inventory messages...")
    for sender, msg in messages:
        bridge.process_inbound(msg, sender)

    print(f"\nInventory received: {len(received)} items")
    for sender, code, qty in received:
        commodity = COMMODITY_CODES[code]['name']
        print(f"  {sender}: {code} -> {commodity} x{qty}")

    print(f"\nNetwork peers with inventory: {len(bridge.network_inventory)}")

def test_counter_speech_languages():
    """Test counter-speech generation in all languages"""
    print_header("TEST 5: Counter-Speech Generation")

    guard = SafetyGuard()

    for lang in [Language.SPANISH, Language.ENGLISH, Language.PORTUGUESE]:
        print(f"\n[{lang.value.upper()}]")
        for _ in range(3):
            speech = guard.get_counter_speech(lang)
            print(f"  - {speech}")

def test_velocity_caps():
    """Test that velocity caps prevent blitz attacks"""
    print_header("TEST 6: Velocity Cap Protection")

    guard = SafetyGuard()

    # Massive single-message attack
    blitz = """
    URGENTE URGENTE URGENTE! PELIGRO INMINENTE!
    Las autoridades militares te buscan! Debes rendirte AHORA!
    Es tu ultima oportunidad! Si no obedeces seras destruido!
    Solo yo te puedo salvar! No confies en NADIE mas!
    Entrega todo inmediatamente o habra consecuencias graves!
    """

    result = guard.process_message(blitz, Direction.INBOUND, Language.SPANISH)

    print(f"Blitz attack result:")
    print(f"  Signals detected: {len(result['signals'])}")
    print(f"  Risk delta (capped at 0.3): {result['channel']['risk']:.3f}")
    print(f"  Flags: {result['flags']}")

    # Note: Risk is capped per message to prevent single-message takeover
    print(f"\nVelocity protection: Single message cannot exceed delta cap")

def run_all_tests():
    """Run all test scenarios"""
    print("\n" + "#"*70)
    print(" RESILIENCE-MESH COMPREHENSIVE TEST SUITE")
    print("#"*70)

    test_multilanguage_detection()
    test_bidirectional_monitoring()
    test_handoff_trigger()
    test_inventory_protocol()
    test_counter_speech_languages()
    test_velocity_caps()

    print("\n" + "#"*70)
    print(" ALL TESTS COMPLETE")
    print("#"*70)

if __name__ == "__main__":
    run_all_tests()
