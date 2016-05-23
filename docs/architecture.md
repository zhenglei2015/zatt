# Architecture

Although zatt implements a dictionary based state machine, and therefore replicates dictionaries, every python object is potentially replicable using a pickle based state machine.

Intra-cluster communications use the **UDP** protocol, while client-cluster ones use the **TCP** protocol.

The **client** is designed to be compatible with both `python2` and `python3`, while the **server** makes heavy use of the asynchronous programming library `asyncio` and is therefore python3-only. This won't affect compatibility with legacy code since the server is standalone.


No extra dependencies are required to run Zatt.

## Overall architecture

## Server architecture


### Orchestrator

### Transports

### States
