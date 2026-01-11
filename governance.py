"""
GOVERNANCE LITE - Democratic Decision Making
============================================
Simple voting and proposal system for cooperative governance.

Features:
- Proposals for trades, decisions, resource allocation
- Signed votes using node identity
- Quorum-based approval
- Time-limited voting periods
- Audit trail on OrbitDB ledger

Keeps cooperatives democratic without complexity.
"""

import time
import hashlib
import json
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


# =============================================================================
# CONFIGURATION
# =============================================================================

# Voting parameters
DEFAULT_QUORUM = 0.5        # 50% of members must vote
DEFAULT_THRESHOLD = 0.6     # 60% approval to pass
DEFAULT_DURATION = 86400    # 24 hours voting period
MIN_VOTERS = 3              # Minimum voters for valid decision


class ProposalType(Enum):
    TRADE = "trade"              # Exchange goods between nodes
    RESOURCE = "resource"        # Allocate shared resources
    MEMBERSHIP = "membership"    # Add/remove members
    POLICY = "policy"           # Change network policies
    EMERGENCY = "emergency"      # Emergency decisions (shorter period)
    GENERAL = "general"         # General proposals


class ProposalStatus(Enum):
    DRAFT = "draft"             # Being prepared
    ACTIVE = "active"           # Open for voting
    PASSED = "passed"           # Approved
    REJECTED = "rejected"       # Not approved
    EXPIRED = "expired"         # Voting period ended without quorum
    CANCELLED = "cancelled"     # Cancelled by proposer


class VoteChoice(Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    """A single vote on a proposal"""
    voter_id: str
    choice: VoteChoice
    timestamp: float
    signature: str = ""         # For verification
    comment: str = ""


@dataclass
class Proposal:
    """A governance proposal"""
    proposal_id: str
    proposal_type: ProposalType
    title: str
    description: str
    proposer_id: str
    created_at: float
    expires_at: float
    status: ProposalStatus = ProposalStatus.DRAFT

    # For trade proposals
    offer: Dict = field(default_factory=dict)      # {'A1': 50}
    request: Dict = field(default_factory=dict)    # {'B1': 30}

    # Voting
    votes: Dict[str, Vote] = field(default_factory=dict)
    quorum: float = DEFAULT_QUORUM
    threshold: float = DEFAULT_THRESHOLD

    # Results
    result_yes: int = 0
    result_no: int = 0
    result_abstain: int = 0

    def to_dict(self) -> Dict:
        return {
            'proposal_id': self.proposal_id,
            'type': self.proposal_type.value,
            'title': self.title,
            'description': self.description,
            'proposer': self.proposer_id,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'status': self.status.value,
            'offer': self.offer,
            'request': self.request,
            'votes': {
                'yes': self.result_yes,
                'no': self.result_no,
                'abstain': self.result_abstain,
                'total': len(self.votes)
            },
            'quorum': self.quorum,
            'threshold': self.threshold
        }


# =============================================================================
# GOVERNANCE ENGINE
# =============================================================================

class GovernanceEngine:
    """
    Manage proposals and voting for the cooperative.

    Designed for mesh networks:
    - Works offline (syncs via OrbitDB when connected)
    - Signed votes prevent tampering
    - Simple enough for non-technical users
    """

    def __init__(self,
                 node_id: str,
                 member_list: List[str] = None,
                 orbitdb = None):

        self.node_id = node_id
        self.members = set(member_list or [node_id])
        self.orbitdb = orbitdb

        # Proposals
        self.proposals: Dict[str, Proposal] = {}

        # Event handlers
        self.on_proposal_handlers: List[Callable] = []
        self.on_vote_handlers: List[Callable] = []
        self.on_result_handlers: List[Callable] = []

    def _generate_id(self) -> str:
        """Generate unique proposal ID"""
        return hashlib.sha256(
            f"{self.node_id}{time.time()}".encode()
        ).hexdigest()[:12]

    def _sign_vote(self, voter_id: str, proposal_id: str, choice: VoteChoice) -> str:
        """Create simple vote signature (placeholder for GPG)"""
        data = f"{voter_id}:{proposal_id}:{choice.value}:{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def add_member(self, member_id: str):
        """Add member to voting roster"""
        self.members.add(member_id)

    def remove_member(self, member_id: str):
        """Remove member from voting roster"""
        self.members.discard(member_id)

    def create_proposal(self,
                        proposal_type: ProposalType,
                        title: str,
                        description: str,
                        duration: int = DEFAULT_DURATION,
                        offer: Dict = None,
                        request: Dict = None,
                        quorum: float = DEFAULT_QUORUM,
                        threshold: float = DEFAULT_THRESHOLD) -> Proposal:
        """Create a new proposal"""
        now = time.time()

        # Emergency proposals have shorter duration
        if proposal_type == ProposalType.EMERGENCY:
            duration = min(duration, 3600)  # Max 1 hour

        proposal = Proposal(
            proposal_id=self._generate_id(),
            proposal_type=proposal_type,
            title=title,
            description=description,
            proposer_id=self.node_id,
            created_at=now,
            expires_at=now + duration,
            status=ProposalStatus.DRAFT,
            offer=offer or {},
            request=request or {},
            quorum=quorum,
            threshold=threshold
        )

        self.proposals[proposal.proposal_id] = proposal

        # Notify handlers
        for handler in self.on_proposal_handlers:
            try:
                handler(proposal, 'created')
            except:
                pass

        return proposal

    def create_trade_proposal(self,
                              offer: Dict,
                              request: Dict,
                              description: str = "") -> Proposal:
        """Convenience method for trade proposals"""
        offer_str = ", ".join(f"{k}:{v}" for k, v in offer.items())
        request_str = ", ".join(f"{k}:{v}" for k, v in request.items())

        return self.create_proposal(
            proposal_type=ProposalType.TRADE,
            title=f"Trade: {offer_str} for {request_str}",
            description=description or f"Propose trading {offer_str} for {request_str}",
            offer=offer,
            request=request,
            duration=DEFAULT_DURATION
        )

    def submit_proposal(self, proposal_id: str) -> bool:
        """Submit draft proposal for voting"""
        if proposal_id not in self.proposals:
            return False

        proposal = self.proposals[proposal_id]
        if proposal.status != ProposalStatus.DRAFT:
            return False

        proposal.status = ProposalStatus.ACTIVE

        # Sync to OrbitDB
        if self.orbitdb:
            self.orbitdb.add_proposal(proposal.to_dict())

        # Notify
        for handler in self.on_proposal_handlers:
            try:
                handler(proposal, 'submitted')
            except:
                pass

        return True

    def vote(self,
             proposal_id: str,
             choice: VoteChoice,
             voter_id: str = None,
             comment: str = "") -> Optional[Vote]:
        """Cast a vote on a proposal"""
        if proposal_id not in self.proposals:
            return None

        proposal = self.proposals[proposal_id]
        voter_id = voter_id or self.node_id

        # Validate
        if proposal.status != ProposalStatus.ACTIVE:
            print(f"[GOV] Proposal not active: {proposal.status.value}")
            return None

        if time.time() > proposal.expires_at:
            self._finalize_proposal(proposal_id)
            return None

        if voter_id not in self.members:
            print(f"[GOV] Non-member cannot vote: {voter_id}")
            return None

        # Create vote
        vote = Vote(
            voter_id=voter_id,
            choice=choice,
            timestamp=time.time(),
            signature=self._sign_vote(voter_id, proposal_id, choice),
            comment=comment
        )

        # Record vote (overwrites previous)
        proposal.votes[voter_id] = vote

        # Update counts
        self._update_vote_counts(proposal)

        # Sync to OrbitDB
        if self.orbitdb:
            self.orbitdb.add_vote(proposal_id, {
                'voter': voter_id,
                'choice': choice.value,
                'signature': vote.signature,
                'timestamp': vote.timestamp
            })

        # Notify
        for handler in self.on_vote_handlers:
            try:
                handler(proposal, vote)
            except:
                pass

        # Check if we can finalize early
        self._check_early_result(proposal)

        return vote

    def _update_vote_counts(self, proposal: Proposal):
        """Recalculate vote counts"""
        proposal.result_yes = sum(
            1 for v in proposal.votes.values() if v.choice == VoteChoice.YES
        )
        proposal.result_no = sum(
            1 for v in proposal.votes.values() if v.choice == VoteChoice.NO
        )
        proposal.result_abstain = sum(
            1 for v in proposal.votes.values() if v.choice == VoteChoice.ABSTAIN
        )

    def _check_early_result(self, proposal: Proposal):
        """Check if result is determined before expiry"""
        total_members = len(self.members)
        total_votes = len(proposal.votes)
        votes_needed = int(total_members * proposal.quorum)

        # Not enough votes yet
        if total_votes < votes_needed:
            return

        # Check if outcome is certain
        remaining = total_members - total_votes
        threshold_votes = int((proposal.result_yes + proposal.result_no) * proposal.threshold)

        # If YES already passed threshold and NO can't catch up
        if proposal.result_yes >= threshold_votes:
            if proposal.result_no + remaining < proposal.result_yes:
                self._finalize_proposal(proposal.proposal_id)

        # If NO already blocks and YES can't catch up
        elif proposal.result_no > (total_votes - threshold_votes):
            if proposal.result_yes + remaining < threshold_votes:
                self._finalize_proposal(proposal.proposal_id)

    def _finalize_proposal(self, proposal_id: str):
        """Finalize voting and determine result"""
        if proposal_id not in self.proposals:
            return

        proposal = self.proposals[proposal_id]
        if proposal.status != ProposalStatus.ACTIVE:
            return

        total_members = len(self.members)
        total_votes = len(proposal.votes)

        # Check quorum
        if total_votes < max(MIN_VOTERS, int(total_members * proposal.quorum)):
            proposal.status = ProposalStatus.EXPIRED
        else:
            # Calculate result (excluding abstains)
            deciding_votes = proposal.result_yes + proposal.result_no
            if deciding_votes == 0:
                proposal.status = ProposalStatus.EXPIRED
            elif proposal.result_yes / deciding_votes >= proposal.threshold:
                proposal.status = ProposalStatus.PASSED
            else:
                proposal.status = ProposalStatus.REJECTED

        # Sync to OrbitDB
        if self.orbitdb:
            self.orbitdb.update_proposal(proposal_id, {
                'status': proposal.status.value,
                'result_yes': proposal.result_yes,
                'result_no': proposal.result_no,
                'result_abstain': proposal.result_abstain
            })

        # Notify
        for handler in self.on_result_handlers:
            try:
                handler(proposal)
            except:
                pass

    def check_expired(self):
        """Check and finalize expired proposals"""
        now = time.time()
        for proposal in self.proposals.values():
            if proposal.status == ProposalStatus.ACTIVE and now > proposal.expires_at:
                self._finalize_proposal(proposal.proposal_id)

    def cancel_proposal(self, proposal_id: str) -> bool:
        """Cancel a proposal (only proposer can cancel draft/active)"""
        if proposal_id not in self.proposals:
            return False

        proposal = self.proposals[proposal_id]
        if proposal.proposer_id != self.node_id:
            return False
        if proposal.status not in [ProposalStatus.DRAFT, ProposalStatus.ACTIVE]:
            return False

        proposal.status = ProposalStatus.CANCELLED
        return True

    def get_active_proposals(self) -> List[Proposal]:
        """Get all active proposals"""
        self.check_expired()
        return [p for p in self.proposals.values() if p.status == ProposalStatus.ACTIVE]

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """Get proposal by ID"""
        return self.proposals.get(proposal_id)

    def get_my_pending_votes(self) -> List[Proposal]:
        """Get proposals I haven't voted on yet"""
        return [
            p for p in self.get_active_proposals()
            if self.node_id not in p.votes
        ]

    def format_proposal(self, proposal: Proposal, lang: str = "es") -> str:
        """Format proposal for display"""
        lines = []

        status_icons = {
            ProposalStatus.ACTIVE: "[ACTIVO]",
            ProposalStatus.PASSED: "[APROBADO]",
            ProposalStatus.REJECTED: "[RECHAZADO]",
            ProposalStatus.EXPIRED: "[EXPIRADO]",
        }

        lines.append(f"{status_icons.get(proposal.status, '[?]')} {proposal.title}")
        lines.append(f"  ID: {proposal.proposal_id}")
        lines.append(f"  Tipo: {proposal.proposal_type.value}")
        lines.append(f"  Propuesto por: {proposal.proposer_id[:8]}")

        if proposal.offer:
            lines.append(f"  Ofrece: {proposal.offer}")
        if proposal.request:
            lines.append(f"  Solicita: {proposal.request}")

        lines.append(f"  Votos: SI:{proposal.result_yes} NO:{proposal.result_no} ABS:{proposal.result_abstain}")

        if proposal.status == ProposalStatus.ACTIVE:
            remaining = int(proposal.expires_at - time.time())
            hours = remaining // 3600
            mins = (remaining % 3600) // 60
            lines.append(f"  Tiempo restante: {hours}h {mins}m")

        return "\n".join(lines)

    def to_broadcast(self, proposal: Proposal) -> str:
        """Format proposal for mesh broadcast"""
        if proposal.proposal_type == ProposalType.TRADE:
            offer = ",".join(f"{k}:{v}" for k, v in proposal.offer.items())
            request = ",".join(f"{k}:{v}" for k, v in proposal.request.items())
            return f"[PROP:{proposal.proposal_id[:6]}] TRADE {offer} FOR {request}"
        else:
            return f"[PROP:{proposal.proposal_id[:6]}] {proposal.title[:30]}"


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    print("="*70)
    print(" GOVERNANCE LITE TEST")
    print("="*70)

    # Create governance engine
    members = ["farm_001", "farm_002", "farm_003", "coop_001", "coop_002"]
    gov = GovernanceEngine(node_id="farm_001", member_list=members)

    # Test 1: Create trade proposal
    print("\n[Test 1] Create trade proposal")
    proposal = gov.create_trade_proposal(
        offer={'A1': 50, 'B1': 20},
        request={'C2': 30},
        description="Trading corn and beans for rice"
    )
    print(f"  Created: {proposal.proposal_id}")
    print(f"  Status: {proposal.status.value}")

    # Submit for voting
    gov.submit_proposal(proposal.proposal_id)
    print(f"  Submitted: {proposal.status.value}")

    # Test 2: Vote on proposal
    print("\n[Test 2] Voting")
    gov.vote(proposal.proposal_id, VoteChoice.YES, voter_id="farm_001")
    gov.vote(proposal.proposal_id, VoteChoice.YES, voter_id="farm_002")
    gov.vote(proposal.proposal_id, VoteChoice.NO, voter_id="farm_003")
    gov.vote(proposal.proposal_id, VoteChoice.YES, voter_id="coop_001")
    gov.vote(proposal.proposal_id, VoteChoice.ABSTAIN, voter_id="coop_002")

    print(f"  Votes: YES={proposal.result_yes} NO={proposal.result_no} ABS={proposal.result_abstain}")
    print(f"  Status: {proposal.status.value}")

    # Test 3: Display formatted
    print("\n[Test 3] Formatted display")
    print(gov.format_proposal(proposal))

    # Test 4: Broadcast format
    print("\n[Test 4] Broadcast format")
    print(f"  {gov.to_broadcast(proposal)}")

    # Test 5: Emergency proposal
    print("\n[Test 5] Emergency proposal")
    emergency = gov.create_proposal(
        ProposalType.EMERGENCY,
        "Flood Alert Response",
        "Move grain storage to higher ground immediately",
        duration=3600  # 1 hour
    )
    gov.submit_proposal(emergency.proposal_id)
    print(f"  Emergency proposal: {emergency.proposal_id}")
    print(f"  Expires in: {int(emergency.expires_at - time.time())}s")

    # Test 6: Check pending votes
    print("\n[Test 6] Pending votes for farm_003")
    gov2 = GovernanceEngine(node_id="farm_003", member_list=members)
    gov2.proposals = gov.proposals  # Share proposals
    pending = gov2.get_my_pending_votes()
    print(f"  Pending: {len(pending)} proposals")
    for p in pending:
        print(f"    - {p.title[:40]}")

    print("\n" + "="*70)
    print(" GOVERNANCE TESTS COMPLETE")
    print("="*70)
