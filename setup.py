#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='Zatt',
      version='1.0',
      description='Implementation of the Raft algorithm for distributed consensus',
      author='Simone Accascina',
      author_email='simon@accascina.me',
      url='https://github.com/simonacca/zatt',
      license='MIT',
      keywords = 'distributed consensus raft',
      classifiers=[
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Distributed Systems :: Consens Algorithms',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
      ],
    packages = find_packages(exclude=['docs', 'tests']),
    entry_points = {'console_scripts':['zattd=zatt.server.main:run']},
     )
