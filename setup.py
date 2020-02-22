#!/usr/bin/python

from setuptools import setup

setup(
    name       = 'scooter',
    version    = '2.7',
    packages   = ['scooter'],
    py_modules = ['scooter.gcc', 'scooter.llvm', 'scooter.build_script', 'scooter.remote_vs'],
    install_requires = [
        'quickfiles',
        'quickstructures',
        'ellbur-easyrun',
        'treewatcher'
    ]
)

