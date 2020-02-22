#!/usr/bin/python

from setuptools import setup

setup(
    name       = 'scooter',
    version    = '2.3',
    packages   = ['scooter'],
    py_modules = ['scooter.gcc', 'scooter.llvm'],
    # http://stackoverflow.com/questions/12372336/how-do-i-make-pip-respect-requirements
    install_requires = [
        'quickfiles',
        'quickstructures',
        'ellbur-easyrun',
    ]
)

