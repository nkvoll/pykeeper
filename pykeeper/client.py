import logging
import threading
from collections import namedtuple

import zookeeper

from pykeeper import event


logger = logging.getLogger(__name__)


STATE_NAME_MAPPING = {
    zookeeper.ASSOCIATING_STATE: "associating",
    zookeeper.AUTH_FAILED_STATE: "auth-failed",
    zookeeper.CONNECTED_STATE: "connected",
    zookeeper.CONNECTING_STATE: "connecting",
    zookeeper.EXPIRED_SESSION_STATE: "expired",
    # TODO: Find a better name for this?
    999: 'connecting',
    0: 'connecting'
}


TYPE_NAME_MAPPING = {
    zookeeper.NOTWATCHING_EVENT: "not-watching",
    zookeeper.SESSION_EVENT: "session",
    zookeeper.CREATED_EVENT: "created",
    zookeeper.DELETED_EVENT: "deleted",
    zookeeper.CHANGED_EVENT: "changed",
    zookeeper.CHILD_EVENT: "child"
}

ZOO_OPEN_ACL_UNSAFE = {
    "perms": zookeeper.PERM_ALL,
    "scheme": "world",
    "id": "anyone"
}


class ClientEvent(namedtuple("ClientEvent", 'type, connection_state, path')):
    """
    A client event is returned when a watch deferred fires. It denotes
    some event on the zookeeper client that the watch was requested on.
    """

    @property
    def type_name(self):
        return TYPE_NAME_MAPPING[self.type]
    @property
    def state_name(self):
        return STATE_NAME_MAPPING[self.connection_state]

    def __repr__(self):
        return  "<ClientEvent %s at %r state: %s>" % (
            self.type_name, self.path, self.state_name)

class TimeoutException(Exception):
    pass


def join(*args):
    return '/'.join(args)


class ZooKeeper(object):

    def __init__(self, servers, reconnect=True):
        self.servers = servers
        self.reconnect = reconnect
        self.handle = None

        self._caches = dict()

        self.on_state = event.Event()
        self.on_event = event.Event()

    def connect(self):
        self.handle = zookeeper.init(self.servers, self._global_watcher)
        self.on_state(self, self.state_name)

    @property
    def state_name(self):
        if self.handle is None:
            return None
        return STATE_NAME_MAPPING[zookeeper.state(self.handle)]

    @property
    def client_id(self):
        if self.handle is None:
            return None
        return zookeeper.client_id(self.handle)

    def _global_watcher(self, handle, event_type, conn_state, path):
        assert handle == self.handle, 'unexpected handle'

        event = ClientEvent(event_type, conn_state, path)
        logger.debug('{0}: Received event {1}'.format(self, event))

        self.on_event(event)
        self.on_state(self, self.state_name)

        if event.state_name == 'expired' and self.reconnect:
            logger.info('{0}: Session expired, reconnecting.'.format(self))
            self.close()
            self.connect()

    def close(self):
        if self.handle is not None:
            zookeeper.close(self.handle)

    def wait_until_connected(self, timeout=None):
        # optimizing for the common case of us already being connected
        if self.state_name == 'connected':
            return

        evt = threading.Event()

        def waiter(client, state):
            if state == 'connected':
                evt.set()

        try:
            self.on_state += waiter

            # state may have changed between the entry of this method and the on_state listener being added.
            if self.state_name == 'connected':
                return

            evt.wait(timeout=timeout)
            if self.state_name != 'connected':
                raise TimeoutException()

        finally:
            self.on_state -= waiter

    def exists(self, path, watcher=None):
        return zookeeper.exists(self.handle, path, self._wrap_watcher(watcher))

    def cached_exists(self, path):
        cache = self._caches.setdefault('exists', dict())

        retval = cache.get(path, Ellipsis)
        if retval is not Ellipsis:
            return retval

        def invalidator(event):
            cache.pop(path, None)

        retval = zookeeper.exists(self.handle, path, self._wrap_watcher(invalidator))
        cache[path] = retval
        return retval

    def get_children(self, path, watcher=None):
        return zookeeper.get_children(self.handle, path, self._wrap_watcher(watcher))

    def cached_get_children(self, path):
        cache = self._caches.setdefault('get_children', dict())

        retval = cache.get(path, Ellipsis)
        if retval is not Ellipsis:
            return retval

        def invalidator(event):
            cache.pop(path, None)

        retval = zookeeper.get_children(self.handle, path, self._wrap_watcher(invalidator))
        cache[path] = retval
        return retval

    def delete(self, path, version=-1):
        return zookeeper.delete(self.handle, path, version)

    def delete_recursive(self, path, dry_run=False, force=False):
        self._delete_recursive(path, dry_run, force)

    def get(self, path, watcher=None):
        return zookeeper.get(self.handle, path, self._wrap_watcher(watcher))

    def cached_get(self, path):
        cache = self._caches.setdefault('get', dict())

        retval = cache.get(path, Ellipsis)
        if retval is not Ellipsis:
            return retval

        def invalidator(event):
            cache.pop(path, None)

        retval = zookeeper.get(self.handle, path, self._wrap_watcher(invalidator))
        cache[path] = retval
        return retval

    def create(self, path, value, acl=[ZOO_OPEN_ACL_UNSAFE], flags=0):
        return zookeeper.create(self.handle, path, value, acl, flags)

    def create_recursive(self, path, data, acl=[ZOO_OPEN_ACL_UNSAFE]):
        if self.exists(path):
            return
        base, name = path.rsplit('/', 1)
        if base:
            self.create_recursive(base, '', acl)
        if not self.exists(path):
            self.create(path, data, acl)

    def set(self, path, value):
        return zookeeper.set(self.handle, path, value)

    def set2(self, path, value):
        return zookeeper.set2(self.handle, path, value)

    def get_acl(self, path):
        return zookeeper.get_acl(self.handle, path)

    def set_acl(self, path, version, acl):
        return zookeeper.set_acl(self.handle, path, version, acl)

    def is_ephemeral(self, path, cache=False):
        getter = self.get
        if cache:
            getter = self.cached_get
        return bool(getter(path)[1]['ephemeralOwner'])

    def _delete_recursive(self, path, dry_run, force):
        has_ephemeral_child = None

        for name in list(self.get_children(path)):
            has_ephemeral_child = self._delete_recursive(join(path, name), dry_run, force)

        if has_ephemeral_child:
            if not dry_run:
                logger.debug('{0}: Didn\'t delete {1!r} because it has an ephemeral child.'.format(self, path))
            return has_ephemeral_child

        ephemeral = self.is_ephemeral(path) and not force
        if dry_run:
            if ephemeral:
                logger.info('{0}: (dry-run) Not deleting {1!r} because it is an ephemeral.'.format(self, path))
            else:
                logger.info('{0}: (dry-run) Would delete {1!r}.'.format(self, path))
        else:
            if ephemeral:
                logger.debug('{0}: Not deleting {1!r} because it is an ephemeral.'.format(self, path))
            else:
                logger.debug('{0}: Deleting {1!r}.'.format(self, path))
                self.delete(path)
        return ephemeral

    def _wrap_watcher(self, watcher):
        if watcher is None:
            return watcher

        return self._watcher_wrapper(watcher)

    def _watcher_wrapper(self, func):
        def wrapper(handle, event_type, conn_state, path):
            event = ClientEvent(event_type, conn_state, path)
            func(event)

        return wrapper

    def __repr__(self):
        return 'ZooKeeperClient(servers={0}, state={1} at {2})'.format(self.servers, self.state_name, hex(id(self)))