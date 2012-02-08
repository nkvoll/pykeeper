from setuptools import setup, find_packages


# make python setup.py test not spew errors (see http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html)
import sys
if 'test' in sys.argv:
    import multiprocessing


setup(
    name = "pykeeper",
    version = "0.1.1",

    author = 'Njal Karevoll',
    author_email = 'njal@karevoll.no',

    description = 'Higher-level bindings for ZooKeeper.',
    long_description = open('Readme.md').read(),

    license = 'MIT',

    keywords = 'zookeeper',

    include_package_data = True,

    url = 'http://github.com/nkvoll/pykeeper',

    # enable python setup.py nosetests
    setup_requires = ['nose'],
    test_suite = 'nose.collector',
    tests_require = ['mock'],

    packages = find_packages(),
)
