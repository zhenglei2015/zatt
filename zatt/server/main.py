import asyncio
from .protocols import Orchestrator, PeerProtocol, ClientProtocol
from .config import config
from .logger import logger


def run():
    loop = asyncio.get_event_loop()
    orchestrator = Orchestrator(config)
    coro = loop.create_datagram_endpoint(lambda: PeerProtocol(orchestrator),
                                         local_addr=config['cluster']
                                         [config['id']])
    transport, _ = loop.run_until_complete(coro)
    orchestrator.peer_transport = transport

    coro = loop.create_server(lambda: ClientProtocol(orchestrator),
                              *config['cluster'][config['id']])
    server = loop.run_until_complete(coro)

    logger.info('Serving on {}'.format(config['cluster'][config['id']]))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()

if __name__ == '__main__':
    run()
