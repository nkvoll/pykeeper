# pykeeper: Higher-level bindings for ZooKeeper


The aim of this project is providing a higher level API over the official low level Python ZooKeeper bindings (zkpython).


## Features

    * Automatic reconnection
    * Recursive delete
    * Recursive create
    * Cached versions of: [get (cached_get), get_children (cached_get_children), exists (cached_exists)]
    * Easy handling and masking of temporary disconnects/reconnects.


## Installing

Either install the latest relase from PYPI:

    $ pip install pykeeper

... or get the latest development version from GitHub:

    $ pip install https://github.com/nkvoll/pykeeper/zipball/develop#egg=pykeeper

Additionally, pykeeper requires a working installation of the official low level Python ZooKeeper bindings. These can either be built from source (recommended, explanation below), or
you could install the statically compiled version [zc-zookeeper-static](http://pypi.python.org/pypi/zc-zookeeper-static)) from PYPI, which may or may not work on your architecture/OS, and may
or may not be the latest available ZooKeeper version.


### Installing ZooKeeper on OS X (homebrew)

If you don't have homebrew, follow the Linux installation below, skipping "ldconfig", otherwise, use homebrew to install zookeeper with the ``--python`` flag:

    $ brew install --python zookeeper


### Installing ZooKeeper on Linux

Download and unpack the latest release of ZooKeeper from http://zookeeper.apache.org/releases.html:

    $ tar -zxvf zookeeper-3.4.2.tar.gz

Build the C bindings:

    $ cd zookeeper-3.4.2/src/c
    $ ./configure --prefix=/usr/local
    $ make
    $ sudo make install
    $ ldconfig

Build and install the python bindings:

    $ cd ../contrib/zkpython
    $ ant install


## Running the test-suite

The test suite assumes you have a ZooKeeper server running on localhost:22181:

    $ cd example
    $ export ZOOCFGDIR=$(pwd) zkServer start-foreground

zkServer / zkServer.sh is found in the ZooKeeper installation directory.

The tests can then be run via the setup.py script:

    $ python setup.py nosetests -with-doctest --verbosity=2


## Example usage

    $ python
    >>> import pykeeper

    # (optional) redirect zookeeper logging to the python "logging" package, using the "zookeeper" logger.
    #   doing this prevents zookeeper from writing a lot of garbage to sys.stderr, and makes enables handling
    #   the logging output via the default python logging facilities. this behaviour is optional and can be
    #   switched off at any time later by calling pykeeper.uninstall_log_stream()
    >>> pykeeper.install_log_stream()

    # Create a ZooKeeper client and connect:
    >>> client = pykeeper.ZooKeeper('localhost:22181')
    >>> client.connect()

    >>> client.get_children('/')
    ['zookeeper']

    # creating a node:
    >>> client.create_recursive('/bar/baz', '{"ok": true}')
    >>> client.get_children('/')
    ['bar', 'zookeeper']
    >>> bool(client.exists('/bar/baz'))
    True
    >>> client.get_children('/bar')
    ['baz']
    >>> client.get('/bar/baz')
    ('{"ok": true}', {'pzxid': 3620L, 'ctime': 1328717487776L, 'aversion': 0, 'mzxid': 3620L, 'numChildren': 0, 'ephemeralOwner': 0L, 'version': 0, 'dataLength': 12, 'mtime': 1328717487776L, 'cversion': 0, 'czxid': 3620L})

    # delete the node:
    >>> client.delete_recursive('/bar')
    >>> bool(client.exists('/bar'))
    False
    >>> client.get_children('/')
    ['foo', 'zookeeper']

    # since the node does not exist, trying to get its data raises an exception:
    >>> client.get('/bar')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "pykeeper/client.py", line 176, in get
        return zookeeper.get(self.handle, path, self._wrap_watcher(watcher))
    zookeeper.NoNodeException: no node


### Handling transient connection errors/losses


If we lose connection to the ZooKeeper server, calls on the client will raise an exception:

    >>> client.get('/')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "pykeeper/client.py", line 176, in get
        return zookeeper.get(self.handle, path, self._wrap_watcher(watcher))
    zookeeper.ConnectionLossException: connection loss

We can wait until the connection is re-established by calling ``client.wait_until_connected()`` with an optional timeout. The default timeout is ``None``, which means the call will block until the connection is re-established:

    >>> client.state_name
    'connecting'
    >>> client.wait_until_connected()
    >>> client.state_name
    'connected'

If the connection is not re-established before the timeout occurs, a TimeoutException is raised:

    >>> client.state_name
    'connecting'
    >>> client.wait_until_connected(timeout=10)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "pykeeper/client.py", line 130, in wait_until_connected
        raise TimeoutException()
    pykeeper.client.TimeoutException
    >>> client.state_name
    'connecting'


## Troubleshooting

### Q: Why do I get a ``TypeError`` when I call any functions on the client?

A: Most likely, you attempted to do something along the following lines:

    >>> import pykeeper
    >>> client = pykeeper.ZooKeeper('localhost:22181')
    >>> client.get_children('/')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "pykeeper/client.py", line 153, in get_children
        return zookeeper.get_children(self.handle, path, self._wrap_watcher(watcher))
    TypeError: an integer is required

The problem is that you forgot to call ``client.connect()`` before using the client:

    >>> import pykeeper
    >>> client = pykeeper.ZooKeeper('localhost:22181')
    >>> client.connect()
    >>> client.get_children('/')
    ['zookeeper']

As usual, consider calling ``client.wait_until_connected(timeout=...)`` before using the client to ensure that the client has had time to connect to the ZooKeeper ensemble.

### Q: I'm creating a multiple clients, and I seem to be leaking memory.
A: Always close clients you are not going to use any more by calling ``client.close()``. Another solution is to re-use the clients instead of creating a new one every time you need one.


## Notes

Currently, only the synchronous parts of the API is implemented.


## License

MIT licensed, see LICENSE for details.