import asyncio
from .protocol import Orchestrator, PeerProtocol
from .config import fetch_config
from .logger import logger, tick




def run():
    config = fetch_config()
    loop = asyncio.get_event_loop()
    orchestrator = Orchestrator(config)
    coro = loop.create_datagram_endpoint(lambda: PeerProtocol(orchestrator),
                              local_addr=config['cluster'][config['id']])
    transport, _ = loop.run_until_complete(coro)
    orchestrator.transport = transport

    logger.info('Serving on {}'.format(config['cluster'][config['id']]))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    loop.close()

if __name__ == '__main__':
    run()
