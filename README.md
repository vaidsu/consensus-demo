## Minimal consensus protocol 

### Goal 

* Implement RAFT like consensus protocol that demonstrates its core capabilities:
    * Election 
    * Replicated log 
    * Minimal state machine replication
* How do I plan to demonstrate the core capabilities:
    * Give N nodes - A leader is reliably elected and that leader is responsible for consensus 
    * Once the leader is elected the leader commits the log and the logs are synchronized across quorum of nodes 
    * Leader proposes the log entry which gets committed when approved and stored in majority of the quorum
    * Once the log is committed, the state machine is updated to preserve the committed state 
* How do I plan to demonstrate the failure invariants:
    * What happens if the messages/actions go out of order 
    * What happens if the leader goes down 
    * What happens if we have stale leader/conflicting logs/partitions
* How do I plan to add guarantees to the system
    * Safety: No two commands are committed at the same log index 
    * Convergence: Once committed, all healthy nodes will apply the logs in order
    * Leader uniqueness: Only one leader elected and participating at any time

## Implementation details 

### Scope

* The implementation is intentionally very simple
* In-memory log and node state (no persistence / fsync)
* Nodes are simulated as objects in a single process (no threads, no real sockets)
* A deterministic simulation harness controls message delivery (drop/delay/reorder)
* Unit tests validate the key safety properties and expected behavior in failure modes


## Simulation 

### Election 

* 


