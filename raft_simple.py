"""
Simplest RAFT ever to start learning 
Every part of the implementation is in one file - Before any expansion 
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import logging

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
        pass 

    def last_term(self):
        pass 

    def term_at(self):
        pass 

    def append_entries(self):
        pass 
    
    def truncate_from(self):
        pass 



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
class AppendEntriesRequest: 

    term: int 
    leader_id: int 
    prev_index: int 
    prev_term: int 
    entries: List[LogEntry]
    leader_commit: int

@dataclass
class AppendEntriesResponse:

    term: int 
    success: bool 
    match_index: int


class StateMachine: 

    def __init__(self):
        pass


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
            voted_for=None,
            last_heartbeat_tick=0
        )
        self.all_node_ids = all_node_ids

    def on_vote_request(self, request: VoteRequest) -> VoteResponse:
        pass

    def on_append_entries(self, request: AppendEntriesRequest) -> AppendEntriesResponse:
        pass


class SimpleRaft:

    def __init__(self) -> None:
        self.nodes: List[Node] = []
        self.leader: Node = None

    def send_vote_request(self, from_id: int, to_id: int, request: VoteRequest) -> VoteResponse:
        pass 

    def send_append_entries(self, from_id: int, to_id: int, request: AppendEntriesRequest) -> AppendEntriesResponse:
        pass 

    def update_state(self):
        pass 

    def get_state(self):
        pass 

