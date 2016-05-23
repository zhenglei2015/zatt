# Client

The client is designed to be embedded in client-side applications and is blocking, that is, the call will not return until the item in question has been successfully committed.

A `distributedDict` client behaves like a regular dictionary, except that a call to the replicated cluster is made for every read/write operation (the frequency of this operation can be easily customized).

Let's try to interact with it:

First we have to create two instances and point them to any of the nodes in the cluster.
```
>>> from zatt.client.distributedDict import DistributedDict
>>> d1 = DistributedDict('127.0.0.1', 1111)
>>> d2 = DistributedDict('127.0.0.1', 1111)
```

Then, we can update one instance
```
>>> d1['spam'] = 'egg'
```

And read it back from the other instance, that could very well be on another machine.

```
>>> d2['spam']
'egg'

```
