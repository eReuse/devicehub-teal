from collections import OrderedDict

from setuptools import find_packages, setup

with open('README.md', encoding='utf8') as f:
    long_description = f.read()

test_requires = [
    'pytest',
    'requests_mock'
]

setup(
    name='ereuse-devicehub',
    version='0.2.0b3',
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
    python_requires='>=3.5.3',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=[
        'teal>=0.2.0a32',  # teal always first
        'click',
        'click-spinner',
        'ereuse-utils[Naming]>=0.4b13',
        'hashids',
        'marshmallow_enum',
        'psycopg2-binary',
        'python-stdnum',
        'PyYAML',
        'requests',
        'requests-toolbelt',
        'sqlalchemy-citext',
        'sqlalchemy-utils[password, color, phone]',
        'Flask-WeasyPrint'
    ],
    extras_require={
        'docs': [
            'sphinx',
            'sphinxcontrib-httpdomain >= 1.5.0',
            'sphinxcontrib-plantuml >= 0.12',
            'sphinxcontrib-websupport >= 1.0.1'
        ],
        'docs-auto': [
            'sphinx-autobuild'
        ],
        'test': test_requires
    },
    tests_require=test_requires,
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
