# Copyright (c) 2010-2011, Found IT A/S and Piped Project Contributors.
# See LICENSE for details.
import unittest

from pykeeper import event


class TestEvent(unittest.TestCase):

    def test_a_callback_can_remove_itself(self):
        e = event.Event()
        l = list()

        def append_just_once():
            l.append(1)
            e.unhandle(append_just_once)

        def keep_appending():
            l.append(2)

        e += append_just_once
        e += keep_appending

        # the event should now contain these callbacks
        self.assertIn(append_just_once, e)
        self.assertIn(keep_appending, e)

        self.assertEquals(len(e), 2)

        e()
        self.assertEquals(l, [1, 2])

        # At this point, the first callback should have removed itself.
        e()
        # So we should not get an additional 1.
        self.assertEquals(l, [1, 2, 2])

    def test_removing_an_nonexistent_callback_raises(self):
        e = event.Event()
        self.assertRaises(ValueError, e.unhandle,  lambda: None)


__doctests__ = [event]