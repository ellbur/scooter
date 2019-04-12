#!/usr/bin/python

from setuptools import setup

setup(
    name       = 'scooter',
    version    = '2.2',
    packages   = ['scooter'],
    py_modules = ['scooter.gcc', 'scooter.llvm'],
    # http://stackoverflow.com/questions/12372336/how-do-i-make-pip-respect-requirements
    install_requires = [
        'quickfiles',
        'quickstructures',
        'ellbur-easyrun',
    ],
    # http://pythonhosted.org/setuptools/setuptools.html#dependencies-that-aren-t-in-pypi
    dependency_links = [
        'https://github.com/ellbur/quickfiles/archive/master.zip#quickfiles-0.123',
        'https://github.com/ellbur/quickstructures/archive/master.zip#quickstructures-0.123',
        'https://github.com/ellbur/easyrun/archive/master.zip#easyrun-0.123',
    ]
)

