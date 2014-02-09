#!/usr/bin/python

from distutils.core import setup

setup(
    name       = 'scooter',
    version    = '0.123',
    packages   = ['scooter'],
    py_modules = ['scooter.gcc', 'scooter.llvm']
)

