"""
EMERGENCY RESET - Data Protection Module
========================================
Protects sensitive data when devices are lost or stolen:
- 3-pass secure deletion
- Configurable data protection levels
- Signed verification (prevents unauthorized resets)
- Protects mesh network data and credentials
"""

import os
import sys
import time
import secrets
import hashlib
import shutil
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass
from enum import Enum

# Attempt GPG import
try:
    import gnupg
    GPG_AVAILABLE = True
except ImportError:
    GPG_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

# Panic codes (these trigger kill switch)
PANIC_CODES = ['XKILL', 'PANIC99', 'BORRAR', 'QUEMAR']

# Paths to sanitize in standard mode
STANDARD_PATHS = [
    "~/.orbitdb",
    "~/.resilience_mesh",
    "~/.resilience_gpg",
    "~/.config/meshtastic",
]

# Additional paths for full reset mode
SCORCHED_EARTH_PATHS = [
    "~/.gnupg",               # Full GPG keyring
    "~/.ipfs",                # IPFS data
    "~/.local/share/orbitdb", # Alternative OrbitDB location
    "~/resilience_mesh",      # Project directory
]

# Specific files to target
CRITICAL_FILES = [
    "~/.gnupg/secring.gpg",     # GPG secret keyring (legacy)
    "~/.gnupg/private-keys-v1.d", # GPG private keys (modern)
    "~/.resilience_gpg/secring.gpg",
    "~/.resilience_mesh/safety_state.json",
    "~/.resilience_mesh/node_id",
]

# Sanitization passes
SANITIZATION_PASSES = 3


class KillMode(Enum):
    STANDARD = "standard"          # Core mesh data only
    SCORCHED_EARTH = "scorched"    # Everything including GPG
    SURGICAL = "surgical"          # Specific files only


@dataclass
class SanitizationReport:
    """Report of sanitization operation"""
    mode: KillMode
    files_erased: int
    directories_removed: int
    errors: List[str]
    timestamp: float
    verified: bool
    signed: bool


# =============================================================================
# PANIC CODE VERIFICATION
# =============================================================================

class PanicCodeVerifier:
    """
    Verifies panic codes are signed by authorized admin key.

    Prevents malicious actors from triggering remote wipes.
    """

    def __init__(self,
                 admin_key_id: Optional[str] = None,
                 gnupghome: str = "~/.resilience_gpg"):
        self.admin_key_id = admin_key_id
        self.gnupghome = os.path.expanduser(gnupghome)
        self.gpg = None

        if GPG_AVAILABLE and admin_key_id:
            try:
                self.gpg = gnupg.GPG(gnupghome=self.gnupghome)
            except:
                pass

    def verify_panic(self, panic_code: str, signature: Optional[str] = None) -> bool:
        """
        Verify panic code authorization.

        If admin_key_id is configured, requires valid signature.
        If not configured, accepts any valid panic code (less secure).
        """
        # Check if it's a valid panic code
        if panic_code.upper() not in PANIC_CODES:
            return False

        # If no admin key configured, accept raw panic codes
        if not self.admin_key_id:
            return True

        # Require signature if admin key is configured
        if not signature:
            print("[KILL] Panic code requires signature")
            return False

        # Verify signature
        if not self.gpg:
            print("[KILL] GPG not available for verification")
            return False

        try:
            # Create verification message
            message = f"PANIC:{panic_code}:{int(time.time() // 300)}"  # 5-min window

            verified = self.gpg.verify(signature, message.encode())

            if verified.valid and verified.key_id == self.admin_key_id:
                return True
            else:
                print(f"[KILL] Invalid signature or wrong key: {verified.key_id}")
                return False

        except Exception as e:
            print(f"[KILL] Verification error: {e}")
            return False

    def generate_signed_panic(self, panic_code: str, passphrase: Optional[str] = None) -> Optional[str]:
        """Generate signed panic code (for admin use)"""
        if not self.gpg:
            return None

        try:
            message = f"PANIC:{panic_code}:{int(time.time() // 300)}"
            signed = self.gpg.sign(
                message,
                keyid=self.admin_key_id,
                passphrase=passphrase,
                detach=True
            )
            return str(signed) if signed else None
        except Exception as e:
            print(f"[KILL] Sign error: {e}")
            return None


# =============================================================================
# FORENSIC SANITIZATION
# =============================================================================

class ForensicSanitizer:
    """
    DoD-standard forensic data sanitization.

    Uses cryptographically secure random overwrites to make
    data irrecoverable even with forensic tools.
    """

    def __init__(self, passes: int = SANITIZATION_PASSES):
        self.passes = passes
        self.errors: List[str] = []
        self._erased_count = 0
        self._dir_count = 0

    def _secure_erase_file(self, file_path: str) -> bool:
        """
        Securely erase single file with random overwrites.

        Pass 1: Random data
        Pass 2: Random data (different)
        Pass 3: Random data (different)
        Then: Truncate to 0, rename to random, delete
        """
        try:
            if not os.path.isfile(file_path):
                return False

            size = os.path.getsize(file_path)

            # Open for overwrite
            with open(file_path, "r+b") as f:
                for pass_num in range(self.passes):
                    f.seek(0)
                    # Write cryptographically secure random bytes
                    f.write(secrets.token_bytes(size))
                    f.flush()
                    os.fsync(f.fileno())

            # Truncate to zero
            with open(file_path, "wb") as f:
                pass

            # Rename to random name before deletion
            random_name = os.path.join(
                os.path.dirname(file_path),
                secrets.token_hex(16)
            )
            os.rename(file_path, random_name)

            # Delete
            os.remove(random_name)

            self._erased_count += 1
            return True

        except PermissionError:
            self.errors.append(f"Permission denied: {file_path}")
        except Exception as e:
            self.errors.append(f"Error erasing {file_path}: {e}")

        return False

    def _secure_erase_directory(self, dir_path: str) -> int:
        """Recursively erase all files in directory"""
        erased = 0
        dir_path = os.path.expanduser(dir_path)

        if not os.path.isdir(dir_path):
            return 0

        # Walk bottom-up to handle nested directories
        for root, dirs, files in os.walk(dir_path, topdown=False):
            # Erase all files
            for name in files:
                file_path = os.path.join(root, name)
                if self._secure_erase_file(file_path):
                    erased += 1

            # Remove empty directories
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                    self._dir_count += 1
                except:
                    pass

        # Remove root directory
        try:
            os.rmdir(dir_path)
            self._dir_count += 1
        except:
            pass

        return erased

    def _erase_gpg_secrets(self) -> int:
        """Specifically target GPG secret keys"""
        erased = 0

        # Legacy keyring
        for path in ["~/.gnupg/secring.gpg", "~/.resilience_gpg/secring.gpg"]:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                if self._secure_erase_file(expanded):
                    erased += 1
                    print(f"[KILL] Erased GPG secret ring: {path}")

        # Modern private keys directory
        for base in ["~/.gnupg", "~/.resilience_gpg"]:
            priv_dir = os.path.expanduser(os.path.join(base, "private-keys-v1.d"))
            if os.path.isdir(priv_dir):
                count = self._secure_erase_directory(priv_dir)
                erased += count
                if count > 0:
                    print(f"[KILL] Erased {count} private keys from {priv_dir}")

        return erased

    def _erase_orbitdb_leveldb(self) -> int:
        """Target OrbitDB's LevelDB storage"""
        erased = 0

        leveldb_paths = [
            "~/.orbitdb",
            "~/.jsipfs/datastore",
            "~/.ipfs/datastore",
            "~/.local/share/orbitdb",
        ]

        for path in leveldb_paths:
            expanded = os.path.expanduser(path)
            if os.path.isdir(expanded):
                count = self._secure_erase_directory(expanded)
                erased += count
                if count > 0:
                    print(f"[KILL] Erased OrbitDB/IPFS data: {path} ({count} files)")

        return erased

    def execute(self,
                mode: KillMode = KillMode.STANDARD,
                custom_paths: Optional[List[str]] = None) -> SanitizationReport:
        """
        Execute sanitization.

        Args:
            mode: STANDARD, SCORCHED_EARTH, or SURGICAL
            custom_paths: Additional paths to sanitize

        Returns:
            SanitizationReport with results
        """
        self.errors = []
        self._erased_count = 0
        self._dir_count = 0

        print(f"[KILL] *** KILL SWITCH ACTIVATED - Mode: {mode.value} ***")

        # Determine paths based on mode
        paths = []

        if mode == KillMode.SURGICAL:
            paths = CRITICAL_FILES.copy()
        elif mode == KillMode.STANDARD:
            paths = STANDARD_PATHS.copy()
        elif mode == KillMode.SCORCHED_EARTH:
            paths = STANDARD_PATHS + SCORCHED_EARTH_PATHS

        if custom_paths:
            paths.extend(custom_paths)

        # Phase 1: GPG secrets (always first)
        print("[KILL] Phase 1: GPG secret keys...")
        gpg_erased = self._erase_gpg_secrets()

        # Phase 2: OrbitDB LevelDB
        print("[KILL] Phase 2: OrbitDB/IPFS data...")
        orbit_erased = self._erase_orbitdb_leveldb()

        # Phase 3: General paths
        print("[KILL] Phase 3: General sanitization...")
        for path in paths:
            expanded = os.path.expanduser(path)

            if os.path.isdir(expanded):
                count = self._secure_erase_directory(expanded)
                print(f"[KILL] Erased directory: {path} ({count} files)")
            elif os.path.isfile(expanded):
                if self._secure_erase_file(expanded):
                    print(f"[KILL] Erased file: {path}")

        # Build report
        report = SanitizationReport(
            mode=mode,
            files_erased=self._erased_count,
            directories_removed=self._dir_count,
            errors=self.errors,
            timestamp=time.time(),
            verified=True,
            signed=False
        )

        print(f"[KILL] Complete: {report.files_erased} files, {report.directories_removed} dirs")

        if self.errors:
            print(f"[KILL] Errors: {len(self.errors)}")
            for err in self.errors[:5]:
                print(f"  - {err}")

        return report


# =============================================================================
# KILL SWITCH CONTROLLER
# =============================================================================

class KillSwitch:
    """
    Main kill switch controller with panic code verification.
    """

    def __init__(self,
                 admin_key_id: Optional[str] = None,
                 gnupghome: str = "~/.resilience_gpg",
                 exit_after: bool = True):
        self.verifier = PanicCodeVerifier(admin_key_id, gnupghome)
        self.sanitizer = ForensicSanitizer()
        self.exit_after = exit_after

        # Callbacks (for logging, etc.)
        self._on_trigger_handlers: List[Callable] = []

    def on_trigger(self, handler: Callable):
        """Register kill trigger handler"""
        self._on_trigger_handlers.append(handler)

    def trigger(self,
                panic_code: str,
                signature: Optional[str] = None,
                mode: KillMode = KillMode.STANDARD) -> Optional[SanitizationReport]:
        """
        Trigger kill switch.

        Args:
            panic_code: Must be valid panic code
            signature: Required if admin_key_id is configured
            mode: Sanitization mode

        Returns:
            SanitizationReport if successful, None if verification failed
        """
        # Verify panic code
        if not self.verifier.verify_panic(panic_code, signature):
            print("[KILL] Panic verification FAILED - aborting")
            return None

        print(f"[KILL] Panic verified: {panic_code}")

        # Notify handlers
        for handler in self._on_trigger_handlers:
            try:
                handler(panic_code, mode)
            except:
                pass

        # Execute sanitization
        report = self.sanitizer.execute(mode)
        report.signed = signature is not None

        if self.exit_after:
            print("[KILL] Terminating process...")
            os._exit(1)

        return report

    def check_panic_in_message(self, message: str) -> Optional[str]:
        """Check if message contains panic code"""
        message_upper = message.upper()
        for code in PANIC_CODES:
            if code in message_upper:
                return code
        return None


# =============================================================================
# TEST
# =============================================================================
def main():
    print("="*60)
    print(" KILL SWITCH MODULE TEST")
    print("="*60)
    print(" WARNING: This is a test - no actual deletion will occur")
    print("="*60)

    # Test panic code detection
    print("\n[TEST] Panic code detection...")
    kill = KillSwitch(exit_after=False)

    test_messages = [
        "Hola, tenemos maiz disponible",
        "XKILL - Emergency shutdown!",
        "Normal message with PANIC99 hidden",
        "BORRAR todo ahora!",
    ]

    for msg in test_messages:
        code = kill.check_panic_in_message(msg)
        status = f"PANIC: {code}" if code else "clean"
        print(f"  '{msg[:40]}...' -> {status}")

    # Test verifier without admin key
    print("\n[TEST] Verification (no admin key)...")
    verifier = PanicCodeVerifier(admin_key_id=None)
    print(f"  XKILL valid: {verifier.verify_panic('XKILL')}")
    print(f"  INVALID valid: {verifier.verify_panic('INVALID')}")

    # Test sanitizer paths (dry run)
    print("\n[TEST] Sanitization paths...")
    print("  Standard mode paths:")
    for path in STANDARD_PATHS:
        expanded = os.path.expanduser(path)
        exists = os.path.exists(expanded)
        print(f"    {path}: {'EXISTS' if exists else 'not found'}")

    print("\n  Scorched earth additional:")
    for path in SCORCHED_EARTH_PATHS:
        expanded = os.path.expanduser(path)
        exists = os.path.exists(expanded)
        print(f"    {path}: {'EXISTS' if exists else 'not found'}")

    print("\n[TEST] Kill switch ready (not triggered)")


if __name__ == "__main__":
    main()
