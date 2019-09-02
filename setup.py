#!/usr/bin/env python

import os
import glob
from setuptools import setup

VERSION = "0.9.4"


def find_data_files(source, target, patterns):
    """
    Locates the specified data-files and returns the matches
    in a data_files compatible format.

    source is the root of the source data tree.
        Use '' or '.' for current directory.
    target is the root of the target data tree.
        Use '' or '.' for the distribution directory.
    patterns is a sequence of glob-patterns for the
        files you want to copy.
    """
    if glob.has_magic(source) or glob.has_magic(target):
        raise ValueError("Magic not allowed in src, target")
    ret = {}
    for pattern in patterns:
        pattern = os.path.join(source, pattern)
        for filename in glob.glob(pattern):
            if os.path.isfile(filename):
                targetpath = os.path.join(
                    target, os.path.relpath(filename, source)
                )
                path = os.path.dirname(targetpath)
                ret.setdefault(path, []).append(filename)
    return sorted(ret.items())


with open('README.rst') as f:
    LONG_DESCR = f.read()


setup(
    name='mandoline-py',
    version=VERSION,
    description='An STL to GCode slicer for 3D printing, using the clipper libraries.',
    long_description=LONG_DESCR,
    author='Revar Desmera',
    author_email='revarbat@gmail.com',
    url='https://github.com/revarbat/mandoline-py',
    download_url='https://github.com/revarbat/mandoline-py/archive/master.zip',
    packages=['mandoline-py'],
    license='MIT License',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    keywords='stl gcode slicer 3dprinting',
    entry_points={
        'console_scripts': ['mandoline-py=mandoline-py:main'],
    },
    install_requires=[
        'setuptools',
        'six>=1.10.0',
        'pyquaternion>=0.9.5',
        'pyclipper>=1.1.0',
        'PyOpenGL-accelerate>=3.1.0',
    ],
)
