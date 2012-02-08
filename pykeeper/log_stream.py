import os
import logging
import threading
import zookeeper
import sys


logger = logging.getLogger('zookeeper')

_installed = False
_relay_thread = None
_logging_pipe = None


def _relay_log():
    global _installed, _logging_pipe
    r, w = _logging_pipe
    f = os.fdopen(r)

    levels = dict(
        ZOO_INFO = logging.INFO,
        ZOO_WARN = logging.WARNING,
        ZOO_ERROR = logging.ERROR,
        ZOO_DEBUG = logging.DEBUG,
    )

    while _installed:
        try:
            line = f.readline().strip()
            if '@' in line:
                level, message = line.split('@', 1)
                level = levels.get(level.split(':')[-1])

                # this line is definitely misclassified in the C client....
                if 'Exceeded deadline by' in line and level == logging.WARNING:
                    level = logging.DEBUG

                # reclassify failed server connection attemps as INFO instead of ERROR:
                if 'server refused to accept the client' in line and level == logging.ERROR:
                    level = logging.INFO

            else:
                level = None
                message = '...' # TODO: can we genereate a better logging message

            if level is None:
                logger.log(logging.INFO, line)
            else:
                logger.log(level, message)
        except Exception as v:
            logger.exception('Exception occurred while relaying zookeeper log: {0}'.format(v))


def is_installed():
    return _installed

def install():
    global _installed, _relay_thread, _logging_pipe

    if is_installed():
        return

    _logging_pipe = os.pipe()

    zookeeper.set_log_stream(os.fdopen(_logging_pipe[1], 'w'))

    _relay_thread = threading.Thread(target=_relay_log)
    _relay_thread.setDaemon(True) # die along with the interpreter
    _relay_thread.start()

    _installed = True

def uninstall():
    if not is_installed():
        return

    global _installed, _relay_thread

    _installed = False
    zookeeper.set_log_stream(sys.stderr)
    # TODO: make sure the thread is actually stopped

    _relay_thread.join()