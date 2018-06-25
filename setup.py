from setuptools import find_packages, setup

with open('README.md') as f:
    long_description = f.read()

setup(
    name='ereuse-devicehub',
    version='0.2.0a8',
    packages=find_packages(),
    url='https://github.com/ereuse/devicehub-teal',
    license='Affero',
    author='eReuse.org team',
    author_email='x.bustamante@ereuse.org',
    include_package_data=True,
    description='A system to manage devices focusing reuse.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=[
        'teal>=0.2.0a5',
        'marshmallow_enum',
        'ereuse-utils[Naming]>=0.3.0b2',
        'psycopg2-binary',
        'requests',
        'requests-toolbelt',
        'hashids',
        'tqdm',
        'click-spinner',
        'sqlalchemy-utils[password, color, babel]',
        'PyYAML'
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
    ]
)
