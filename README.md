## Minimal consensus protocol 

### Goal 

Implement a minimal, Raft-inspired consensus protocol that demonstrates core distributed-systems invariants:

- Leader election
- Replicated, append-only log
- State machine replication with commit semantics

### What this demonstrates 

- Given **N nodes**, a **single leader** is elected for a term and is responsible for proposing log entries
- Log entries are **replicated to followers** and become **committed only after quorum approval**
- **Append ≠ Commit**: entries are appended first and applied to the state machine only after commitment
- Once committed, **all healthy nodes converge to the same state**

## Tests 

Failure modes covered by tests include:
- message reordering or loss
- stale leaders and higher-term reconciliation
- conflicting logs and truncation
- node outage and delayed rejoin

Run the tests through 

* `pip install -r requirements.txt` 
* `cd tests && pytest -q` 

## Implementation details 

### Scope

* The implementation is intentionally very simple
* In-memory log and node state (no persistence / fsync)
* Nodes are simulated as objects in a single process (no threads, no real sockets)
* A deterministic simulation harness controls message delivery (drop/delay/reorder)
* Unit tests validate the key safety properties and expected behavior in failure modes


### Simulation 

* In this implementation I have created a `ReftSimulation` class that has encapsulated all the routing and simulation in that class. 
* There are few functionalities (and its intentional and not implemented by actual full e2e protocol)
  * Election and majority votes - `start_election` -- Equivalent to a leader starting the election after coming up 
  * Propose - `propose` -- Equivalent to synchronizing the entries and eventually committing the state across all nodes 
  * `sync_offline_node` -- simulates delayed node recovery and deterministic log reconciliation

### Node 

* Node is the heart of the actual implementation and all the necessary behaviors of the node are encapsulated here, 
  * `on_vote_request` - This handler will be called from simulator, to make the node behave as if the vote request came through 
  * `on_append_entry_request` - While real RAFT can batch and apply multiple entries I intentionally simplified to be appending one by one, as the actual invariant is not changed irrespective of appending one or more. 
  * `apply_committed` - This is to commit the state machine, I kept it close to how a real sensor could be sent in reality (in a toy version `SET sensor1 31`)

* Each node state is modeled as the heart of the node and contains all the details about the latest/prev term, index etc. 

### Log store 

* Log store is the equivalent of storing the log somewhere, this is simply take each entry and apending them and have some basic helpers to fetch/retrieve data. 


## Offline / delayed-rejoin experiment

As an extension, the simulator includes an **offline node mode**, inspired by Eight Sleep’s backup / offline operation:
https://www.eightsleep.com/blog/backup-mode

Nodes marked offline temporarily stop receiving messages while the leader continues operation. When nodes rejoin, they deterministically catch up by replaying missing log entries and applying committed state.

This experiment demonstrates how buffered updates and delayed reconciliation preserve safety and convergence.

## Notes/Future work 

This is not a complete Raft implementation. Features intentionally omitted include:
- heartbeats and time-based elections
- persistent storage
- dynamic membership changes






