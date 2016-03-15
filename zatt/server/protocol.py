import asyncio
import socket
import logging
import json
from .states import Follower

logging.basicConfig(level=logging.INFO)

class Orchestrator():
    def __init__(self, config):
        self.cluster = config['cluster']
        self.state = Follower(orchestrator=self, config=config)

    def change_state(self, new_state):
        self.state.teardown()
        self.state = new_state(old_state=self.state)

    def connection_made(self, transport):
        peer_info = transport.get_extra_info('peername')
        for node in self.cluster.values():
            if peer_info == node['info']:
                if 'transport' in node and not node['transport'].is_closing():
                    transport.close()
                else:
                    node['transport'] = transport
                break
        logging.info('New connection:' + peer_info[0] + str(peer_info[1]))

    def data_received(self, transport, message):
        for peer_id, peer in self.cluster.items():
            if peer['transport'] is transport:
                self.state.data_received_peer(peer_id, message)
                return
        self.state.data_received_client(transport, message)

    def send(self, transport, message):
        transport.write(str(json.dumps(message) + '\n').encode())

    def send_peer(self, peer_id, message):
        if 'transport' in self.cluster[peer_id] and\
           not self.cluster[peer_id]['transport'].is_closing():
            transport = self.cluster[peer_id]['transport']
            self.send(transport, message)
        else:
            loop = asyncio.get_event_loop()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)
            sock.bind(('127.0.0.1', 8888))
            sock.connect(self.cluster[peer_id]['info'])
            sock.setblocking(False)
            coro = loop.create_connection(lambda: RaftProtocol(self, message),
                                          sock=sock)
            loop.create_task(coro)

    def broadcast_peers(self, message):
        for peer_id in self.cluster:
            if peer_id != self.state.volatile['Id']:
                self.send_peer(peer_id, message)


class RaftProtocol(asyncio.Protocol):
    def __init__(self, orchestrator, first_message=None):
        self.orchestrator = orchestrator
        self.first_message = first_message  # in case an immediate message is needed

    def connection_made(self, transport):
        self.orchestrator.connection_made(transport)
        self.transport = transport
        if self.first_message:
            transport.write(json.dumps(self.first_message).encode())

    def data_received(self, data):
        message = json.loads(data.decode())
        self.orchestrator.data_received(self.transport, message)
