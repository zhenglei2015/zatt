import asyncio
import socket
import json
from .states import Follower
from .logger import logger


class Orchestrator():
    def __init__(self, config):
        self.cluster = config['cluster']
        self.state = Follower(orchestrator=self, config=config)

    def change_state(self, new_state):
        self.state.teardown()
        self.state = new_state(old_state=self.state)

    def data_received(self, addr, message):
        for peer_id, peer in self.cluster.items():
            if peer == addr:
                self.state.data_received_peer(peer_id, message)
                return
        self.state.data_received_client(transport, message)

    def send(self, transport, message):
        transport.sendto(str(json.dumps(message)).encode())

    def send_peer(self, peer_id, message):
        self.transport.sendto(str(json.dumps(message)).encode(),
                              self.cluster[peer_id])

    def broadcast_peers(self, message):
        for peer_id in self.cluster:
            if peer_id != self.state.volatile['Id']:
                self.send_peer(peer_id, message)


class PeerProtocol(asyncio.Protocol):
    def __init__(self, orchestrator, first_message=None):
        self.orchestrator = orchestrator
        self.first_message = first_message  # in case an immediate message is needed

    def connection_made(self, transport):
        self.transport = transport
        if self.first_message:
            transport.sendto(json.dumps(self.first_message).encode())

    def datagram_received(self, data, addr):
        message = json.loads(data.decode())
        self.orchestrator.data_received(addr, message)

    def error_received(self, ex):
        print('Error:', ex)
