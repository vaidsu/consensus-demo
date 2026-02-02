"""
Simplest RAFT ever to start learning 
Every part of the implementation is in one file - Before any expansion 
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import logging
from collections import defaultdict

LOG = logging.getLogger('SimpleRaft')


@dataclass
class LogEntry:

    index: int 
    term: int 
    command: str 

class LogStore:
    """
    Acts as a simple log store for the entries per node 
    TODO: Add the actual type output 
    """

    def __init__(self):
        self.logs: List[LogEntry] = []

    def last_index(self):
        return self.logs[-1].index if self.logs else 0

    def last_term(self):
        return self.logs[-1].term if self.logs else 0

    def term_at(self, index: int) -> Optional[int]:
        if index == 0: return 0 # Sentinel 
        if 1 <= index <= self.last_index():
            return self.logs[index-1].term
        return None
    
    def has_index(self, index: int) -> bool:
        if index == 0: return True
        return 1 <= index <= self.last_index()

    def append_entry(self, entry: LogEntry) -> None:
        # It is an append only entry, it doesn't care about the exact requirement. 
        assert entry.index == self.last_index() + 1, "Log entries must be contiguous"
        self.logs.append(entry)
    
    def truncate_from(self, index: int):
        self.logs = self.logs[:index - 1]

    def get(self, index: int) -> LogEntry:
        if index == 0: return None
        return self.logs[index - 1]


class NodeRole(Enum):

    LEADER = 1
    FOLLOWER = 2
    CANDIDATE = 3


@dataclass
class NodeState:
    ## Persistent state on all servers

    current_term: int # TBA 
    role: NodeRole # What is the role for the node 
    log_store: LogStore # Append only log entries (in memory)
    commit_index: int  # Highest log index committed 
    last_applied: int # Highest log index applied to state machine 
    voted_for: Optional[int] # Which node did I vote for 


## API data models 

@dataclass
class VoteRequest:

    term: int 
    candidate_id: int 
    last_log_index: int 
    last_log_term: int 

@dataclass
class VoteResponse:

    term: int 
    granted: bool

@dataclass
class AppendEntryRequest: 

    term: int 
    leader_id: int 
    prev_index: int 
    prev_term: int 
     # This is intentionally to simplify one entry at a time, where in reality there can be batching, streaming etc. 
    entry: LogEntry
    leader_commit_index: int

@dataclass
class AppendEntryResponse:

    term: int 
    success: bool 
    match_index: int



class StateMachine: 

    def __init__(self):
        self.data: dict[str, int] = defaultdict(int) # {"sensor1": 32} # Like temperature 

    def set_data(self, command):
        # SET sensor1 31
        # Dumb processing 
        splits = [a.strip() for a in command.split(' ') if a]
        sensor_name = splits[1]
        value = int(splits[2])
        self.data[sensor_name] = value


class Node:
    ## Abstraction of the node 

    def __init__(self, id: int, name: str, all_node_ids: List[int]):
        self.id = id 
        self.name = name 
        self.state = NodeState(
            current_term=0,
            role=NodeRole.FOLLOWER,
            log_store=LogStore(),
            commit_index=0,
            last_applied=0,
            voted_for=None
        )
        self.state_machine = StateMachine()
        self.all_node_ids = all_node_ids

    def reconcile_term(self, term: int) -> bool:

        if term < self.state.current_term:
            return False 
        if term > self.state.current_term:
            self.state.current_term = term
            self.state.role = NodeRole.FOLLOWER
            self.state.voted_for = None
        elif self.state.role == NodeRole.CANDIDATE and term == self.state.current_term:
            # This needs to step down 
            self.state.role = NodeRole.FOLLOWER
        return True
        
    def is_log_up_to_date(self, requested_last_term: int, requested_last_index: int) -> bool:
        
        last_log_term = self.state.log_store.last_term()
        last_log_index = self.state.log_store.last_index()
        return requested_last_term > last_log_term or (
            requested_last_term == last_log_term and 
            requested_last_index >= last_log_index)


    def on_vote_request(self, request: VoteRequest) -> VoteResponse:
        """
        Steps: 

        1. Check the request's term with my term 
        2. If request.term > my term, become FOLLOWER, update term and clear voted_for 
        3. Update vote 
        """

        # Deny list first 
        # Term check
        if not self.reconcile_term(request.term):
            return VoteResponse(term=request.term, granted=False)
        
        # Stale log check 
        if not self.is_log_up_to_date(requested_last_term=request.last_log_term, requested_last_index=request.last_log_index):
            return VoteResponse(term=self.state.current_term, granted=False)
        # Grant one vote rule 
        if self.state.voted_for is not None and self.state.voted_for != request.candidate_id:
            return VoteResponse(term=self.state.current_term, granted=False)
        
        # Allow list
        self.state.voted_for = request.candidate_id
        return VoteResponse(term=self.state.current_term, granted=True)
    


    def apply_committed(self):
        # Apply in a loop 
        while self.state.last_applied < self.state.commit_index:
            self.state.last_applied += 1
            entry_to_apply = self.state.log_store.get(self.state.last_applied)
            # Apply to state machine 
            self.state_machine.set_data(entry_to_apply.command)
            LOG.info(f"Node {self.id} applied entry {entry_to_apply} to state machine. Current state: {self.state_machine.data}")
            

    # TODO: Commit to be added 
    def on_append_entry(self, request: AppendEntryRequest) -> AppendEntryResponse:
        """
        Scenarios:

        1. Happy path :

        # (index, term, cmd)
        Leader [(1, 1, X), (2, 1, Y), (3, 1, Z)]
        Follower [(1, 1, X), (2, 1, Y)]
        When leader sends follower (3, 1, Z) -> Last_index 2, last_term 1
        Follower accepts 

        2. Conflict with data already available in follower 
        Leader [(1, 1, X), (2, 1, Y), (3, 1, Z)]
        Follower [(1, 1, X), (2, 1, Y), (3, 2, L)]
        When leader sends follower (3, 1, Z) -> Last_index 2, last_term 1
        Follower accepts the last_index and last_term, but finds that there is a conflict on index 3 with a new term, 
        If conflict:
          truncate_at(index=3) 
          append(index=3)

        3. Conflict in follower but rejects 
        Leader [(1, 1, X), (2, 1, Y), (3, 1, Z)]
        Follower [(1, 1, X)]
        Leader sends follower (3, 1, Z) -> (2, 1)
        Follower doesn't have 2, 1 and reject
        Leader now has to send one index below.
        """
        # We will keep the log store's interface simple as its only job is to append and manage the "list" of entries
        # The heavy lifting can be done by RAFT handling in the node that way we don't leak specific role based handling to the store and keep it in the node 
            
        # Deny list first 
        # Term reconcilliation 
        if not self.reconcile_term(request.term):
            LOG.error(f"Recon term failed {request.term} {request.entry} {self.state}")
            return AppendEntryResponse(term=request.term, success=False, match_index=None)
        
        # Check the last_index and last_term first 
        cur_node_log_term = self.state.log_store.term_at(request.prev_index)
        if request.prev_index > self.state.log_store.last_index():
            # Entries missing 
            LOG.error(f"Current node misses entries failed {request.term} {request.entry}  {self.state}")
            return AppendEntryResponse(term=request.term, success=False, match_index=None)
        # index match, so we check if terms match 
        elif request.prev_index > 0 and cur_node_log_term != request.prev_term:
            # Stale term coming in 
            LOG.error(f"Incorrect term {request.term} {self.state} {request.entry}")
            return AppendEntryResponse(term=request.term, success=False, match_index=None)
        
        # Ready to append, need to merge conflict checks 
        if self.state.log_store.has_index(request.entry.index):
            # Idempotency check 
            if self.state.log_store.term_at(request.entry.index) == request.entry.term:
                # Apply state 
                self.state.commit_index = min(request.leader_commit_index, self.state.log_store.last_index())
                self.apply_committed()
                LOG.info(f"Idempotent request {request.term} {self.state} {request.entry}")
                return AppendEntryResponse(term=self.state.current_term, success=True, match_index=self.state.log_store.last_index())
            else:
                # This means a true conflict, need to truncate to pave way 
                LOG.error(f"Conflict - Index already exists for node {self.id} index {request.entry.index} store {self.state.log_store.logs}")
                # Since the new leader has been elected, it accepts the new entries and truncates old 
                # Truncate first 
                self.state.log_store.truncate_from(request.entry.index)
                # Now append 
                self.state.log_store.append_entry(request.entry)
                # Apply state 
                self.state.commit_index = min(request.leader_commit_index, self.state.log_store.last_index())
                self.apply_committed()
                return AppendEntryResponse(term=request.term, success=True, match_index=self.state.log_store.last_index())
            
        # If we come here, there is nothing conflicting to stop appending of entry 
        self.state.log_store.append_entry(request.entry)
        self.state.commit_index = min(request.leader_commit_index, self.state.log_store.last_index())
        self.apply_committed()
        LOG.info(f"Happy path request {request.term} {self.state} {request.entry}")
        return AppendEntryResponse(term=request.term, success=True, match_index=self.state.log_store.last_index())

        

    def start_election(self):
        # Vote for self and request to become leader
        self.state.role = NodeRole.CANDIDATE
        self.state.current_term += 1
        self.state.voted_for = self.id 
        return self.id

    def become_leader(self):
        self.state.role = NodeRole.LEADER
        # Reset voted for, for next term.
        self.state.voted_for = self.id


"""
The simulator is very simple to pretty much orchestrate things to emulate the basics of RAFT. 
Most of the behaviors are encapsulated into the Node and this is simply to help orchestrate
All the nodes implements a handler for handling append_entry and vote_request, this way its like the node
gets the request and processes and it makes testing easier
"""
class RaftClusterSim:

    def __init__(self) -> None:
        self.nodes: List[Node] = []
        self.leader: Node = None
        # For simulator purposes only 
        self.cur_leader_index = -1

    @property
    def majority(self):
        return (len(self.nodes) // 2) + 1

    def add_node(self, node: Node):
        self.nodes.append(node)

    def start_election(self):
        # Pick the next node and start election
        self.cur_leader_index += 1
        # To ensure we do round robin simulation
        self.cur_leader_index = min(self.cur_leader_index, len(self.nodes) - 1)
        candidate_node = self.nodes[self.cur_leader_index]
        # Start election in the node 
        candidate_id = candidate_node.start_election()
        # Now send the vote request to other 
        total_votes = 0
        for n in self.nodes:
            vote_response = self.send_vote_request(
                to_node=n,
                request=VoteRequest(
                    term=candidate_node.state.current_term,
                    candidate_id=candidate_id,
                    last_log_index=candidate_node.state.log_store.last_index(),
                    last_log_term=candidate_node.state.log_store.last_term()
                )
            )
            total_votes += 1 if vote_response.granted else 0
        
        if total_votes >= self.majority:
            # Make the candidate the leader 
            candidate_node.become_leader()
            # Set cluster leader 
            self.leader = self.nodes[self.cur_leader_index]

        

    def send_vote_request(self, to_node: Node, request: VoteRequest) -> VoteResponse:
        # Simulation
        # Find the node by id 
        return to_node.on_vote_request(request=request)

    def send_append_entry(self, to_node: Node, request: AppendEntryRequest) -> AppendEntryResponse:
        return to_node.on_append_entry(request)
    
    def propose(self, entry: LogEntry):
        # Append to leader first 
        # This avoids moving by 1 after append
        prev_index = self.leader.state.log_store.last_index()
        prev_term = self.leader.state.log_store.term_at(prev_index)
        self.leader.state.log_store.append_entry(entry)
        # Propose to other nodes 
        total_ack = 1 # Leader counts 1 since in the loop leader is skipped
        for n in self.nodes:
            if n.id != self.leader.id:
                ack = n.on_append_entry(
                    request=AppendEntryRequest(
                        term=self.leader.state.current_term,
                        leader_id=self.leader.id,
                        prev_index=prev_index,
                        prev_term=prev_term,
                        entry=entry,
                        leader_commit_index=self.leader.state.commit_index
                    )
                )
                total_ack += 1 if ack.success else 0
        
        if total_ack >= self.majority:
            LOG.info(f"Leader {self.leader.id} committed index {entry.index}")
            self.leader.state.commit_index = entry.index

            # Broadcast the commit 
            for n in self.nodes:
                if n.id != self.leader.id:
                    n.on_append_entry(
                        AppendEntryRequest(
                            term=self.leader.state.current_term,
                            leader_id=self.leader.id,
                            prev_index=prev_index,
                            prev_term=prev_term,
                            entry=entry,  # resend ok - Idempotent
                            leader_commit_index=self.leader.state.commit_index
                        )
                    )

        # Leader apply
        self.leader.apply_committed() 
