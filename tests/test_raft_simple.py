# Very simple test 
# Mimics the behavior to start with
import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from raft_simple import (
    AppendEntryRequest,
    LogEntry,
    LogStore,
    Node,
    NodeRole,
    RaftClusterSim,
    VoteRequest,
)


def make_node(node_id: int, all_ids=None):
    if all_ids is None:
        all_ids = [1, 2, 3]
    return Node(id=node_id, name=f"n{node_id}", all_node_ids=all_ids)


def test_logstore_last_index_last_term_empty():
    store = LogStore()
    assert store.last_index() == 0
    assert store.last_term() == 0


def test_logstore_term_at_sentinel():
    store = LogStore()
    assert store.term_at(0) == 0


def test_logstore_append_and_truncate():
    store = LogStore()
    store.append_entry(LogEntry(index=1, term=1, command="SET a 1"))
    store.append_entry(LogEntry(index=2, term=1, command="SET b 2"))
    store.append_entry(LogEntry(index=3, term=2, command="SET c 3"))
    assert store.last_index() == 3
    assert store.last_term() == 2

    store.truncate_from(3)
    assert store.last_index() == 2
    assert store.last_term() == 1


def test_vote_rejects_lower_term():
    node = make_node(1)
    node.state.current_term = 2
    req = VoteRequest(term=1, candidate_id=2, last_log_index=0, last_log_term=0)
    resp = node.on_vote_request(req)
    assert resp.granted is False
    assert node.state.current_term == 2


def test_vote_grants_higher_term_and_steps_down():
    node = make_node(1)
    node.state.role = NodeRole.CANDIDATE
    node.state.current_term = 2
    req = VoteRequest(term=3, candidate_id=2, last_log_index=0, last_log_term=0)
    resp = node.on_vote_request(req)
    assert resp.granted is True
    assert node.state.current_term == 3
    assert node.state.role == NodeRole.FOLLOWER
    assert node.state.voted_for == 2


def test_vote_one_per_term():
    node = make_node(1)
    node.state.current_term = 1
    req1 = VoteRequest(term=1, candidate_id=2, last_log_index=0, last_log_term=0)
    req2 = VoteRequest(term=1, candidate_id=3, last_log_index=0, last_log_term=0)
    resp1 = node.on_vote_request(req1)
    resp2 = node.on_vote_request(req2)
    assert resp1.granted is True
    assert resp2.granted is False


def test_vote_log_freshness():
    node = make_node(1)
    node.state.log_store.append_entry(LogEntry(index=1, term=2, command="SET a 1"))
    stale = VoteRequest(term=2, candidate_id=2, last_log_index=1, last_log_term=1)
    fresh = VoteRequest(term=2, candidate_id=2, last_log_index=1, last_log_term=2)
    assert node.on_vote_request(stale).granted is False
    assert node.on_vote_request(fresh).granted is True


def test_append_entry_rejects_missing_prev_index():
    node = make_node(1)
    req = AppendEntryRequest(
        term=1,
        leader_id=2,
        prev_index=1,
        prev_term=1,
        entry=LogEntry(index=2, term=1, command="SET a 1"),
        leader_commit_index=0,
    )
    resp = node.on_append_entry(req)
    assert resp.success is False


def test_append_entry_rejects_prev_term_mismatch():
    node = make_node(1)
    node.state.log_store.append_entry(LogEntry(index=1, term=1, command="SET a 1"))
    req = AppendEntryRequest(
        term=2,
        leader_id=2,
        prev_index=1,
        prev_term=2,
        entry=LogEntry(index=2, term=2, command="SET b 2"),
        leader_commit_index=0,
    )
    resp = node.on_append_entry(req)
    assert resp.success is False


def test_append_entry_conflict_truncates_and_appends():
    node = make_node(1)
    node.state.log_store.append_entry(LogEntry(index=1, term=1, command="SET a 1"))
    node.state.log_store.append_entry(LogEntry(index=2, term=2, command="SET b 2"))

    req = AppendEntryRequest(
        term=3,
        leader_id=2,
        prev_index=1,
        prev_term=1,
        entry=LogEntry(index=2, term=3, command="SET c 3"),
        leader_commit_index=2,
    )
    resp = node.on_append_entry(req)
    assert resp.success is True
    assert node.state.log_store.last_index() == 2
    assert node.state.log_store.term_at(2) == 3


def test_cluster_election_selects_leader():
    cluster = RaftClusterSim()
    nodes = [make_node(1), make_node(2), make_node(3)]
    for n in nodes:
        cluster.add_node(n)
    cluster.start_election()
    assert cluster.leader is not None
    assert cluster.leader.state.role == NodeRole.LEADER


def test_cluster_propose_commits_majority():
    cluster = RaftClusterSim()
    nodes = [make_node(1), make_node(2), make_node(3)]
    for n in nodes:
        cluster.add_node(n)
    cluster.start_election()

    entry = LogEntry(index=1, term=cluster.leader.state.current_term, command="SET a 10")
    cluster.propose(entry)

    assert cluster.leader.state.commit_index == 1
    for n in nodes:
        assert n.state.log_store.last_index() == 1
