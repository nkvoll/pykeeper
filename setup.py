import os
import sys
from setuptools import setup, find_packages


# make python setup.py test not spew errors (see http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html)
if 'test' in sys.argv:
    import multiprocessing

# add pykeeper to the package path so we can get the version from the source tree
here = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, here)
import pykeeper

setup(
    name = 'pykeeper',
    version = str(pykeeper.version),

    author = 'Njal Karevoll',
    author_email = 'njal@karevoll.no',

    description = 'Higher-level bindings for ZooKeeper.',
    long_description = open('Readme.md').read(),

    license = 'MIT',

    keywords = 'zookeeper',

    url = 'http://github.com/nkvoll/pykeeper',

    # enable python setup.py nosetests
    setup_requires = ['nose'],
    test_suite = 'nose.collector',
    tests_require = ['mock'],

    packages = find_packages(),

    classifiers = [
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ]
)
