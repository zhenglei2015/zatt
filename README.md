# [Zatt](https://github.com/simonacca/zatt)

Zatt is a distributed storage system built on the [Raft](https://raft.github.io/)
consensus algorithm.

The **server** is a standalone application and is therefore *python3-only*.
The **client** instead is compatible with both major versions of python.

## Installing
Both the server and the client are shipped in the same [package](https://pypi.python.org/pypi/raft/) (Note: this link won't work until the project is public).

Zatt can be installed by several means:

### Pypi
`$ pip3 install zatt`. (Note: this won't work until the project is public).

(use `pip2` if you want to install in python2)

### Pip and Git
`$ pip3 install git+ssh://github.com/simonacca/zatt.git@develop`

### Cloning
```
$ git clone git@github.com:simonacca/zatt.git
$ cd zatt
$ python3 setup.py install
```

At this point `$ zattd --help` should work.

## Examples

This screencast shows what will be explained below:

[![asciicast](https://asciinema.org/a/7o8bpyfxh0r1uaxvpfi7u8tjl.png)](https://asciinema.org/a/7o8bpyfxh0r1uaxvpfi7u8tjl)


### Spinning up a cluster of servers

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

### Client

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

### Remarks

Please note that in order to erase the log of a node, the corresponding `zatt.{id}.persist` folder has to be removed.

Also note that JSON, currently used for serialization, only supports keys of type `str` and values of type `int, float, str, bool, list, dict `.

## Tests
In order to run the tests:

* clone the repo if you haven't done so already: `git clone git@github.com:simonacca/zatt.git`
* navigate to the test folder: `cd zatt/tests`
* execute: `python3 run.py`

## Contributing

TODO

## License

TODO
