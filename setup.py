from setuptools import setup, find_packages


setup(
    name='abctools',
    version='0.1-dev',
    description='Collection of general tools and utilities for working in and with Alembic Files',
    url='http://github.com/westernx/abctools',

    packages=find_packages(exclude=['build*', 'tests*']),
    include_package_data=True,

    author='Mark Reid',
    author_email='mindmark@gmail.com',
    license='BSD-3',

    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
