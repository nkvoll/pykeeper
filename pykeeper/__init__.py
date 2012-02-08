from .client import *
from .log_stream import install as install_log_stream, uninstall as uninstall_log_stream


# See http://www.python.org/dev/peps/pep-0386/ for version numbering, especially NormalizedVersion
from distutils import version
version = version.LooseVersion('0.1.0')