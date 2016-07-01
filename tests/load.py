from timeit import default_timer as timer
from utils import Pool as SPool
from zatt.client.distributedDict import DistributedDict
from multiprocessing import Pool

from time import sleep

n_servers = 2 ** 1
n_clients = 2 ** 2
payloads = 2000


def client(x):
    d = DistributedDict('127.0.0.1', 9110)
    d[str(x)] = 'a' * 51 #str(x)

clients_pool = Pool(n_clients)

print('Bringing up {} nodes'.format(n_servers))
start = timer()
pool = SPool(n_servers)
pool.start(pool.ids)
end = timer()
print('Time elapsed {}'.format(end - start))

input('Ready?')
print('using {} clients'.format(n_clients))
print('Adding {} key:value pairs'.format(payloads))

start = timer()
clients_pool.map(client, range(payloads))
end = timer()
print('Time elapsed client  {}'.format(end - start))


sleep(1)
pool.stop(pool.ids)
pool.rm(pool.ids)
