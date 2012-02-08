class Event(object):
    """Very lightweight event handling.

    Example:

        >>> event = Event()
        >>> some_list = list()
        >>> def foo(arg):
        ...     some_list.append(arg)
        >>> event += foo
        >>> event('42')
        >>> event(123)
        >>> print some_list
        ['42', 123]
    """
    def __init__(self):
        self._callbacks = []

    def handle(self, callback):
        self._callbacks.append(callback)
        return self
    __iadd__ = handle

    def unhandle(self, callback):
        if not callback in self._callbacks:
            raise ValueError("%s was not handling this event." % callback)
        self._callbacks.remove(callback)
        return self
    __isub__ = unhandle

    def __contains__(self, callback):
        return callback in self._callbacks

    def __call__(self, *args, **kwargs):
        # Make a copy in case the callback wants to remove itself from
        # the list, since we can't iterate over a modified list.
        callbacks = self._callbacks[:]
        for callback in callbacks:
            callback(*args, **kwargs)

    def __len__(self):
        return len(self._callbacks)