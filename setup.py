#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()


def load_requirements(filename: str):
    with open(filename) as req_file:
        requirements = [
            req for req in req_file.read().split('\n')
            if '-e .' not in req
        ]
    return requirements


dev_dependencies = load_requirements('requirements-dev.txt')

setup(
    author="Marco Scheidhuber",
    author_email='marco.scheidhuber@sbb.spk-berlin.de',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Processing custom tasks in the ecosystem of the [OCR-D](https://github.com/OCR-D) project.",
    entry_points={
        'console_scripts': [
            'ocrd_butler=ocrd_butler.cli:main',
        ],
    },
    install_requires=load_requirements('requirements.txt'),
    license="MIT",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='ocrd_butler',
    name='ocrd_butler',
    packages=find_packages(include=['ocrd_butler']),
    test_suite='tests',
    tests_require=dev_dependencies,
    extras_require={
        'dev': dev_dependencies,
    },
    url='https://github.com/StaatsbibliothekBerlin/ocrd_butler',
    version='0.1.0',
    zip_safe=False,
)
