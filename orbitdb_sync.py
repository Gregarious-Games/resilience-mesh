"""
ORBITDB SYNC LAYER - P2P Persistence for Soberanía-Mesh
========================================================
Merkle-CRDT synchronization via OrbitDB sidecar.

Ensures grain ledger survives node seizures through distributed replication.
Even if 50% of family laptops are compromised, remaining nodes merge without conflict.
"""

import requests
import json
import time
import hashlib
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# OrbitDB sidecar configuration
ORBITDB_API = "http://127.0.0.1:3000"
ORBITDB_TIMEOUT = 5  # seconds

class SyncStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    SYNCING = "syncing"
    ERROR = "error"


@dataclass
class InventoryRecord:
    """Single inventory record for the distributed ledger"""
    record_id: str
    node_id: str
    commodity_code: str
    quantity: int
    timestamp: float
    signature: Optional[str] = None  # GPG signature
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            '_id': self.record_id,
            'node_id': self.node_id,
            'commodity_code': self.commodity_code,
            'quantity': self.quantity,
            'timestamp': self.timestamp,
            'signature': self.signature,
            'metadata': self.metadata
        }

    @staticmethod
    def from_dict(data: Dict) -> 'InventoryRecord':
        return InventoryRecord(
            record_id=data.get('_id', ''),
            node_id=data['node_id'],
            commodity_code=data['commodity_code'],
            quantity=data['quantity'],
            timestamp=data['timestamp'],
            signature=data.get('signature'),
            metadata=data.get('metadata', {})
        )


class OrbitDBSync:
    """
    Synchronization layer for OrbitDB sidecar.

    The sidecar runs as a separate Node.js process exposing HTTP API.
    This allows process isolation - database failures don't crash the LoRa bridge.
    """

    def __init__(self,
                 api_url: str = ORBITDB_API,
                 db_name: str = "soberania-inventory",
                 node_id: str = "local"):
        self.api_url = api_url
        self.db_name = db_name
        self.node_id = node_id
        self.status = SyncStatus.DISCONNECTED

        # Local cache for offline operation
        self._local_cache: Dict[str, InventoryRecord] = {}
        self._pending_writes: List[InventoryRecord] = []
        self._last_sync = 0

        # Callbacks
        self._on_sync_handlers: List[Callable] = []
        self._on_conflict_handlers: List[Callable] = []

        # Background sync thread
        self._running = False
        self._sync_thread = None

    def _generate_record_id(self, node_id: str, code: str, timestamp: float) -> str:
        """Generate deterministic record ID"""
        data = f"{node_id}:{code}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def check_connection(self) -> bool:
        """Check if OrbitDB sidecar is reachable"""
        try:
            resp = requests.get(
                f"{self.api_url}/health",
                timeout=ORBITDB_TIMEOUT
            )
            if resp.status_code == 200:
                self.status = SyncStatus.CONNECTED
                return True
        except requests.exceptions.RequestException:
            pass

        self.status = SyncStatus.DISCONNECTED
        return False

    def add_inventory(self,
                      commodity_code: str,
                      quantity: int,
                      signature: Optional[str] = None,
                      metadata: Optional[Dict] = None) -> Optional[InventoryRecord]:
        """
        Add inventory record to distributed ledger.

        If OrbitDB is unreachable, queues for later sync.
        """
        timestamp = time.time()
        record_id = self._generate_record_id(self.node_id, commodity_code, timestamp)

        record = InventoryRecord(
            record_id=record_id,
            node_id=self.node_id,
            commodity_code=commodity_code,
            quantity=quantity,
            timestamp=timestamp,
            signature=signature,
            metadata=metadata or {}
        )

        # Add to local cache immediately
        self._local_cache[record_id] = record

        # Try to sync to OrbitDB
        if self._sync_record(record):
            return record

        # Queue for later if offline
        self._pending_writes.append(record)
        print(f"[ORBIT] Queued for sync: {commodity_code}:{quantity}")
        return record

    def _sync_record(self, record: InventoryRecord) -> bool:
        """Sync single record to OrbitDB"""
        if not self.check_connection():
            return False

        try:
            resp = requests.post(
                f"{self.api_url}/db/{self.db_name}/add",
                json=record.to_dict(),
                timeout=ORBITDB_TIMEOUT
            )
            if resp.status_code in (200, 201):
                print(f"[ORBIT] Synced: {record.commodity_code}:{record.quantity}")
                return True
            else:
                print(f"[ORBIT] Sync failed: {resp.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[ORBIT] Sync error: {e}")

        return False

    def get_inventory(self, commodity_code: Optional[str] = None) -> List[InventoryRecord]:
        """
        Get inventory records from distributed ledger.

        Returns local cache if OrbitDB unreachable.
        """
        records = []

        if self.check_connection():
            try:
                params = {}
                if commodity_code:
                    params['commodity_code'] = commodity_code

                resp = requests.get(
                    f"{self.api_url}/db/{self.db_name}/query",
                    params=params,
                    timeout=ORBITDB_TIMEOUT
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get('records', []):
                        record = InventoryRecord.from_dict(item)
                        records.append(record)
                        # Update local cache
                        self._local_cache[record.record_id] = record
                    return records
            except requests.exceptions.RequestException:
                pass

        # Fallback to local cache
        for record in self._local_cache.values():
            if commodity_code is None or record.commodity_code == commodity_code:
                records.append(record)

        return records

    def get_network_summary(self) -> Dict:
        """Get summary of inventory across all nodes"""
        records = self.get_inventory()

        summary = {
            'total_records': len(records),
            'nodes': set(),
            'by_commodity': {},
            'last_sync': self._last_sync
        }

        for record in records:
            summary['nodes'].add(record.node_id)
            code = record.commodity_code
            if code not in summary['by_commodity']:
                summary['by_commodity'][code] = {'total': 0, 'sources': []}
            summary['by_commodity'][code]['total'] += record.quantity
            summary['by_commodity'][code]['sources'].append({
                'node': record.node_id[:8],
                'qty': record.quantity
            })

        summary['nodes'] = list(summary['nodes'])
        return summary

    def sync_pending(self) -> int:
        """Sync all pending writes to OrbitDB"""
        if not self.check_connection():
            return 0

        synced = 0
        still_pending = []

        for record in self._pending_writes:
            if self._sync_record(record):
                synced += 1
            else:
                still_pending.append(record)

        self._pending_writes = still_pending
        self._last_sync = time.time()

        if synced > 0:
            print(f"[ORBIT] Synced {synced} pending records")
            for handler in self._on_sync_handlers:
                try:
                    handler(synced)
                except:
                    pass

        return synced

    def start_background_sync(self, interval: float = 30.0):
        """Start background sync thread"""
        if self._running:
            return

        self._running = True

        def sync_loop():
            while self._running:
                self.sync_pending()
                time.sleep(interval)

        self._sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self._sync_thread.start()
        print(f"[ORBIT] Background sync started (interval: {interval}s)")

    def stop_background_sync(self):
        """Stop background sync"""
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5)

    def on_sync(self, handler: Callable):
        """Register sync completion handler"""
        self._on_sync_handlers.append(handler)

    def get_status(self) -> Dict:
        """Get sync status"""
        return {
            'status': self.status.value,
            'api_url': self.api_url,
            'db_name': self.db_name,
            'local_records': len(self._local_cache),
            'pending_writes': len(self._pending_writes),
            'last_sync': self._last_sync
        }


# =============================================================================
# ORBITDB SIDECAR SPECIFICATION
# =============================================================================
"""
The OrbitDB sidecar should implement these endpoints:

GET  /health                    - Returns 200 if operational
POST /db/{name}/add             - Add record to DocumentStore
GET  /db/{name}/query           - Query records with optional filters
GET  /db/{name}/all             - Get all records
DELETE /db/{name}/{id}          - Delete record by ID

Example sidecar (Node.js):

```javascript
const express = require('express');
const { create } = require('ipfs-core');
const OrbitDB = require('orbit-db');

const app = express();
app.use(express.json());

let orbitdb, db;

async function init() {
    const ipfs = await create();
    orbitdb = await OrbitDB.createInstance(ipfs);
    db = await orbitdb.docstore('soberania-inventory', {
        indexBy: '_id'
    });
    await db.load();
}

app.get('/health', (req, res) => res.json({ status: 'ok' }));

app.post('/db/:name/add', async (req, res) => {
    const hash = await db.put(req.body);
    res.json({ hash, status: 'added' });
});

app.get('/db/:name/query', async (req, res) => {
    const records = db.query(doc => {
        if (req.query.commodity_code) {
            return doc.commodity_code === req.query.commodity_code;
        }
        return true;
    });
    res.json({ records });
});

init().then(() => {
    app.listen(3000, '127.0.0.1', () => {
        console.log('OrbitDB sidecar running on port 3000');
    });
});
```
"""


# =============================================================================
# TEST
# =============================================================================
def main():
    print("="*60)
    print(" ORBITDB SYNC LAYER TEST")
    print("="*60)

    sync = OrbitDBSync(node_id="test_farm_001")

    # Check connection (will fail without sidecar)
    connected = sync.check_connection()
    print(f"\nOrbitDB connection: {connected}")
    print(f"Status: {sync.status.value}")

    # Add inventory (will queue if offline)
    print("\nAdding inventory records...")
    sync.add_inventory("A1", 100, metadata={'location': 'sector_3'})
    sync.add_inventory("B1", 50)
    sync.add_inventory("C2", 200)

    # Get status
    status = sync.get_status()
    print(f"\nSync Status:")
    print(f"  Local records: {status['local_records']}")
    print(f"  Pending writes: {status['pending_writes']}")

    # Get inventory from cache
    print("\nLocal inventory cache:")
    for record in sync.get_inventory():
        print(f"  {record.commodity_code}: {record.quantity}")


if __name__ == "__main__":
    main()
