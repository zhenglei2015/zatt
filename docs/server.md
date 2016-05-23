# Server

...

The same port is used across two different protocols for communicating both with other nodes and with clients.

## Running
The Zatt server is installed as the `$ zattd` command.
It can be configured either via CLI options, or via a config file.
The two config methods can be mixed, keeping in mind that CLI options override the config file.

### CLI options

```
usage: zattd [-h] [-c PATH_CONF] [-s STORAGE] [-a ADDRESS] [-p PORT]
             [--remote-address REMOTE_ADDRESS] [--remote-port REMOTE_PORT]
             [--debug]

Zatt. An implementation of the Raft algorithm for distributed consensus

optional arguments:
  -h, --help            show this help message and exit
  -c PATH_CONF, --config PATH_CONF
                        Config file path. Default: zatt.persist/conf
  -s STORAGE, --storage STORAGE
                        Path for the persistent state directory. Default:
                        zatt.persist
  -a ADDRESS, --address ADDRESS
                        This node address. Default: 127.0.0.1
  -p PORT, --port PORT  This node port. Default: 5254
  --remote-address REMOTE_ADDRESS
                        Remote node address
  --remote-port REMOTE_PORT
                        Remote node port
  --debug               Enable debug mode

```

### Config file

The config file is formatted in JSON and is idempotent to the CLI options.

```json
{ "address": ["127.0.0.1", 9110],
  "cluster": [
	["127.0.0.1", 9111],
	["127.0.0.1", 9112],
	["127.0.0.1", 9113]
],
 "storage": "/path/to/storage",
 "debug": true,
}

```
Provided that the example above is saved in the file `zatt.json`,
it can then be run with `$ zattd --config zatt.json`
