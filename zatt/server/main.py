import asyncio
from .protocol import Orchestrator, RaftProtocol
from .config import config



def run():
    orchestrator = Orchestrator(config())
    loop = asyncio.get_event_loop()

    # Each client connection will create a new protocol instance
    coro = loop.create_server(lambda: RaftProtocol(orchestrator),
                              '127.0.0.1', 8888, reuse_port=True)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))
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
