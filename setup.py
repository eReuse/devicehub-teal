import re
from collections import OrderedDict

from setuptools import find_packages, setup

with open('README.md', encoding='utf8') as f:
    long_description = f.read()

with open('ereuse_devicehub/__init__.py', 'rt', encoding='utf8') as f:
    version = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)

test_requires = [
    'pytest',
    'pytest-datadir',
    'requests_mock'
]

setup(
    name='ereuse-devicehub',
    version=version,
    url='https://github.com/ereuse/devicehub-teal',
    project_urls=OrderedDict((
        ('Documentation', 'http://devicheub.ereuse.org'),
        ('Code', 'http://github.com/ereuse/devicehub-teal'),
        ('Issue tracker', 'https://tree.taiga.io/project/ereuseorg-devicehub/issues?q=rules')
    )),
    license='Affero',
    author='eReuse.org team',
    author_email='x.bustamante@ereuse.org',
    description='A system to manage devices focusing reuse.',
    packages=find_packages(),
    include_package_data=True,
    platforms='any',
    python_requires='>=3.5.3',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=[
        'click',
        'click-spinner',
        'ereuse-rate==0.0.2',
        'ereuse-utils[Naming]>=0.4b1',
        'hashids',
        'marshmallow_enum',
        'psycopg2-binary',
        'python-stdnum',
        'PyYAML',
        'teal>=0.2.0a12',
        'requests',
        'requests-toolbelt',
        'sqlalchemy-utils[password, color, phone]',
    ],
    extras_require={
        'docs': [
            'sphinx',
            'sphinxcontrib-httpdomain >= 1.5.0',
            'sphinxcontrib-plantuml >= 0.12',
            'sphinxcontrib-websupport >= 1.0.1'
        ],
        'test': test_requires
    },
    tests_requires=test_requires,
    setup_requires=[
        'pytest-runner'
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
