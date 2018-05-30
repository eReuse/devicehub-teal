from setuptools import find_packages, setup

setup(
    name="eReuse_Devicehub",
    version='0.0.1',
    packages=find_packages(),
    url='https://github.com/ereuse/devicehub-teal',
    license='Affero',
    author='eReuse.org team',
    author_email='x.bustamante@ereuse.org',
    description='A system to manage devices focused in reusing them.',
    install_requires=[
        'teal',
        'marshmallow_enum',
        'ereuse-utils [Naming]',
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
    classifiers={
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    },
)
