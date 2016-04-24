import asyncio
import os
import json
import logging
from .states import Follower
from .config import config

logger = logging.getLogger(__name__)


class Orchestrator():
    def __init__(self):
        os.makedirs(config.storage, exist_ok=True)
        self.state = Follower(orchestrator=self)

    def change_state(self, new_state):
        self.state.teardown()
        logger.info('State change:' + new_state.__name__)
        self.state = new_state(old_state=self.state)

    def data_received_peer(self, addr, message):
        for peer_id, peer in config.cluster.items():
            if peer == addr:
                self.state.data_received_peer(peer_id, message)
                break

    def data_received_client(self, transport, message):
        self.state.data_received_client(transport, message)

    def send(self, transport, message):
        transport.sendto(str(json.dumps(message)).encode())

    def send_peer(self, peer_id, message):
        if peer_id == self.state.volatile['Id']:
            return
        self.peer_transport.\
            sendto(str(json.dumps(message)).encode(), config.cluster[peer_id])

    def broadcast_peers(self, message):
        for peer_id in config.cluster:
            self.send_peer(peer_id, message)


class PeerProtocol(asyncio.Protocol):
    def __init__(self, orchestrator, first_message=None):
        self.orchestrator = orchestrator
        self.first_message = first_message

    def connection_made(self, transport):
        self.transport = transport
        if self.first_message:
            transport.sendto(json.dumps(self.first_message).encode())

    def datagram_received(self, data, addr):
        message = json.loads(data.decode())
        self.orchestrator.data_received_peer(addr, message)

    def error_received(self, ex):
        print('Error:', ex)


class ClientProtocol(asyncio.Protocol):
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def connection_made(self, transport):
        logger.debug('Established connection with client %s:%s',
                     *transport.get_extra_info('peername'))
        self.transport = transport

    def data_received(self, data):
        message = json.loads(data.decode())
        self.orchestrator.data_received_client(self, message)

    def connection_lost(self, exc):
        logger.debug('Closed connection with client %s:%s',
                     *self.transport.get_extra_info('peername'))

    def send(self, message):
        self.transport.write(json.dumps(message).encode())
        self.transport.close()
