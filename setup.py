from setuptools import find_packages, setup

setup(
    name="ereuse-devicehub",
    version='0.2.0a2',
    packages=find_packages(),
    url='https://github.com/ereuse/devicehub-teal',
    license='Affero',
    author='eReuse.org team',
    author_email='x.bustamante@ereuse.org',
    description='A system to manage devices focusing reuse.',
    install_requires=[
        'teal',
        'marshmallow_enum',
        'ereuse-utils [Naming] >= 0.3.0b1',
        'psycopg2-binary',
        'sqlalchemy-utils',
        'requests',
        'requests-toolbelt',
        'hashids'
    ],
    tests_requires=[
        'pytest',
        'pytest-datadir',
        'requests_mock'
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: GNU Affero General Public License v3'
    ],
)
