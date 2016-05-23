# Zatt

Zatt is a **distributed storage system** built on the [Raft](https://raft.github.io) consensus algorithm.

It allows clients to share a **key-value** data structure (a python `dict`), that is automatically replicated to a raft cluster.

Zatt aims to be feature-complete with respect to the [raft paper](http://ramcloud.stanford.edu/raft.pdf); the following features have been implemented so far:

* Leader election
* Log replication
* Log compaction
* Membership changes

## Contents
* [Architecture](architecture.md)
* [Running a Server](server.md)
* [Embedding a Client](client.md)
* [Reference](reference.md)


## Tutorial
### Installation
Both the server and the client are shipped in the same
[package](https://pypi.python.org/pypi/raft/), which can be installed by several means:

#### Pypi
`$ pip3 install zatt`

#### Pip & Github
`$ pip3 install git+ssh://github.com/simonacca/zatt.git`

#### Cloning
```
$ git clone git@github.com:simonacca/zatt.git
$ cd zatt
$ git checkout develop
$ python3 setup.py install
```

Regardless of the installation method, you can check your install with  `$ zattd --help`.


### Spinning up a cluster

A server can be configured with command-line options or with a config file,
in this example, we are going to use both.

First, create an empty folder and enter it:
`$ mkdir zatt_cluster && cd zatt_cluster`.

Now create a config file `zatt.conf` with the following content:
```
{"cluster": {
    "0": ["127.0.0.1", 5254],
    "1": ["127.0.0.1", 5255],
    "2": ["127.0.0.1", 5256]
 }
}
```

You can now run the first node:

`$ zattd -c zatt.conf --id 0 -s zatt.0.persist --debug`

This tells zattd to run the node with `id:0`, taking the info about address and port from the config file.

Now you can spin up a second node: open another terminal, navigate to `zatt_cluster` and issue:

`$ zattd -c zatt.conf --id 2 -s zatt.2.persist --debug`

Repeat for a third node, this time with `id:2`

### Interacting with the cluster

To interact with the cluster, we need a client. Open a python interpreter (`$ python`) and run the following commands:

```
In [1]: from zatt.client import DistributedDict
In [2]: d = DistributedDict('127.0.0.1', 5254)
In [3]: d['key1'] = 0
```

Let's retrieve `key1` from a second client:

Open the python interpreter on another terminal and run:

```
In [1]: from zatt.client import DistributedDict
In [2]: d = DistributedDict('127.0.0.1', 5254)
In [3]: d['key1']
Out[3]: 0
In [4]: d
Out[4]: {'key1': 0}
```

### Notes

Please note that in order to erase the log of a node, the corresponding `zatt.{id}.persist` folder has to be removed.

Also note that JSON, currently used for serialization, only supports keys of type `str` and values of type `int, float, str, bool, list, dict `.
