import threading
import unittest
import time
import mock

import zookeeper

from pykeeper import client, log_stream


class ClientTest(unittest.TestCase):

    def setUp(self):
        self.client = client.ZooKeeper('localhost:22181')
        log_stream.install()


    def tearDown(self):
        self.client.close()
        log_stream.uninstall()


class ConnectionTest(ClientTest):

    def test_connecting_and_waiting(self):
        self.assertEqual(self.client.state_name, None)
        self.client.connect()
        self.assertEqual(self.client.state_name, 'connecting')

        self.client.wait_until_connected(timeout=10)
        self.assertEqual(self.client.state_name, 'connected')

    def test_connecting_wait_timeout(self):
        self.client.servers = 'localhost:22180'
        self.assertEqual(self.client.state_name, None)
        self.client.connect()

        self.assertRaises(client.TimeoutException, self.client.wait_until_connected, timeout=0.1)
        self.assertEqual(self.client.state_name, 'connecting')

    def test_reconnecting(self):
        self.client.connect()
        self.client.wait_until_connected(timeout=10)

        # store the session id:
        first_client_id = self.client.client_id

        # expire the session
        self.client._global_watcher(self.client.handle, zookeeper.SESSION_EVENT, zookeeper.EXPIRED_SESSION_STATE, '')
        self.client.wait_until_connected(timeout=10)

        # the session id should have changed
        self.assertNotEquals(first_client_id, self.client.client_id)


class GetChildrenTest(ClientTest):

    def setUp(self):
        super(GetChildrenTest, self).setUp()

        self.client.connect()
        self.client.wait_until_connected(timeout=10)

        if self.client.exists('/pykeeper'):
            self.client.delete_recursive('/pykeeper')

        self.client.create('/pykeeper', '')
        self.client.create('/pykeeper/children', '')

    def tearDown(self):
        self.client.delete_recursive('/pykeeper')
        super(GetChildrenTest, self).tearDown()

    def test_get_children_and_watch(self):
        children = self.client.get_children('/pykeeper/children')
        self.assertEquals(children, [])

        event = threading.Event()
        watch_results = list()
        def watcher(client_event):
            watch_results.append(client_event)
            event.set()

        self.client.get_children('/pykeeper/children', watcher=watcher)

        self.assertEqual(event.is_set(), False)
        self.client.create('/pykeeper/children/foo', '')

        # the watch should fire
        event.wait(timeout=1)
        self.assertEqual(len(watch_results), 1)

        # the client event should contain information about the changed node's children
        client_event = watch_results[0]
        self.assertEquals(client_event.state_name, 'connected')
        self.assertEquals(client_event.type_name, 'child')
        self.assertEquals(client_event.path, '/pykeeper/children')

    def test_cached_get_children(self):
        children = self.client.cached_get_children('/pykeeper/children')
        self.assertEquals(children, [])

        children = self.client.cached_get_children('/pykeeper/children')
        self.assertEquals(children, [])

        self.client.create('/pykeeper/children/foo', '')
        time.sleep(0.01)

        children = self.client.cached_get_children('/pykeeper/children')
        self.assertEquals(children, ['foo'])

        # replace the zookeeper 'get_children' method to make sure the cache is used.
        with mock.patch.object(client.zookeeper, 'get_children') as mocked_get_children:
            mocked_get_children.side_effect = lambda *a, **kw: ['mocked']

            children = self.client.cached_get_children('/pykeeper/children')
            self.assertEquals(children, ['foo'])

            self.assertEqual(mocked_get_children.call_count, 0)

            # changing the children should invalidate the cache
            self.client.delete('/pykeeper/children/foo')
            time.sleep(0.01)

            # make sure our mock actually may be used
            children = self.client.cached_get_children('/pykeeper/children')
            self.assertEquals(children, ['mocked'])
            self.assertEquals(mocked_get_children.call_count, 1)


class GetTest(ClientTest):

    def setUp(self):
        super(GetTest, self).setUp()

        self.client.connect()
        self.client.wait_until_connected(timeout=10)

        if self.client.exists('/pykeeper'):
            self.client.delete_recursive('/pykeeper')

        self.client.create('/pykeeper', '')

    def tearDown(self):
        self.client.delete_recursive('/pykeeper')
        super(GetTest, self).tearDown()

    def test_get(self):
        self.assertRaises(zookeeper.NoNodeException, self.client.get, '/pykeeper/get')

        self.client.create('/pykeeper/get', 'foo')

        data, stat = self.client.get('/pykeeper/get')
        self.assertEquals(data, 'foo')

        event = threading.Event()
        watch_results = list()
        def watcher(client_event):
            watch_results.append(client_event)
            event.set()

        self.client.get('/pykeeper/get', watcher=watcher)

        self.assertEqual(event.is_set(), False)
        self.client.delete('/pykeeper/get')

        # the watch should fire
        event.wait(timeout=1)
        self.assertEqual(len(watch_results), 1)

        # the client event should contain information about the deleted node
        client_event = watch_results[0]
        self.assertEquals(client_event.state_name, 'connected')
        self.assertEquals(client_event.type_name, 'deleted')
        self.assertEquals(client_event.path, '/pykeeper/get')

    def test_cached_get(self):
        self.client.create('/pykeeper/get', 'foo')

        data, stat = self.client.cached_get('/pykeeper/get')
        self.assertEquals(data, 'foo')

        data, stat = self.client.cached_get('/pykeeper/get')
        self.assertEquals(data, 'foo')

        self.client.set('/pykeeper/get', 'bar')
        time.sleep(0.01)

        data, stat = self.client.cached_get('/pykeeper/get')
        self.assertEquals(data, 'bar')

        # replace the zookeeper 'get' method to make sure the cache is used.
        with mock.patch.object(client.zookeeper, 'get') as mocked_get:
            mocked_get.side_effect = lambda *a, **kw: ('mocked', mock.Mock())

            data, stat = self.client.cached_get('/pykeeper/get')
            self.assertEquals(data, 'bar')

            self.assertEqual(mocked_get.call_count, 0)

            # changing the children should invalidate the cache
            self.client.delete('/pykeeper/get')
            time.sleep(0.01)

            # make sure our mock actually may be used
            data, stat = self.client.cached_get('/pykeeper/get')
            self.assertEquals(data, 'mocked')
            self.assertEquals(mocked_get.call_count, 1)


class ExistsTest(ClientTest):

    def setUp(self):
        super(ExistsTest, self).setUp()

        self.client.connect()
        self.client.wait_until_connected(timeout=10)

        if self.client.exists('/pykeeper'):
            self.client.delete_recursive('/pykeeper')

        self.client.create('/pykeeper', '')

    def tearDown(self):
        self.client.delete_recursive('/pykeeper')
        super(ExistsTest, self).tearDown()

    def test_get(self):
        self.assertFalse(self.client.exists('/pykeeper/exists'))

        self.client.create('/pykeeper/exists', 'foo')

        self.assertTrue(self.client.exists('/pykeeper/exists'))

        event = threading.Event()
        watch_results = list()
        def watcher(client_event):
            watch_results.append(client_event)
            event.set()

        self.client.exists('/pykeeper/exists', watcher=watcher)

        self.assertEqual(event.is_set(), False)
        self.client.delete('/pykeeper/exists')

        # the watch should fire
        event.wait(timeout=1)
        self.assertEqual(len(watch_results), 1)

        # the client event should contain information about the node deletion
        client_event = watch_results[0]
        self.assertEquals(client_event.state_name, 'connected')
        self.assertEquals(client_event.type_name, 'deleted')
        self.assertEquals(client_event.path, '/pykeeper/exists')

    def test_cached_exists(self):
        self.client.create('/pykeeper/exists', 'foo')

        stat = self.client.cached_exists('/pykeeper/exists')
        self.assertTrue(stat)

        second_stat = self.client.cached_exists('/pykeeper/exists')
        self.assertEquals(stat, second_stat)

        # replace the zookeeper 'exists' method to make sure the cache is used.
        with mock.patch.object(client.zookeeper, 'exists') as mocked_exists:
            mocked_stat = mock.Mock()
            mocked_exists.side_effect = lambda *a, **kw: mocked_stat

            stat = self.client.cached_exists('/pykeeper/exists')
            self.assertTrue(stat)
            self.assertNotEquals(stat, mocked_stat)

            self.assertEqual(mocked_exists.call_count, 0)

            # deleting the node should invalidate the cache
            self.client.delete('/pykeeper/exists')
            time.sleep(0.01)

            # make sure our mock actually may be used
            stat = self.client.cached_exists('/pykeeper/exists')
            self.assertEquals(stat, mocked_stat)
            self.assertEquals(mocked_exists.call_count, 1)