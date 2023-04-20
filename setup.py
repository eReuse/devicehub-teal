from pathlib import Path

from setuptools import find_packages, setup

from ereuse_devicehub import __version__

test_requires = ['pytest', 'requests_mock']

setup(
    name='ereuse-devicehub',
    version=__version__,
    url='https://github.com/ereuse/devicehub-teal',
    project_urls={
        'Documentation': 'http://devicehub.ereuse.org',
        'Code': 'http://github.com/ereuse/devicehub-teal',
        'Issue tracker': 'https://tree.taiga.io/project/ereuseorg-devicehub/issues?q=rules',
    },
    license='Affero',
    author='eReuse.org team',
    author_email='x.bustamante@ereuse.org',
    description='A system to manage devices focusing reuse.',
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.7.3',
    long_description=Path('README.md').read_text('utf8'),
    install_requires=[
        #        'teal>=0.2.0a38',  # teal always first
        'click',
        'click-spinner',
        #        'ereuse-utils[naming,test,session,cli]>=0.4b49',
        'hashids',
        'marshmallow_enum',
        'psycopg2-binary',
        'python-stdnum',
        'PyYAML',
        'requests[security]',
        'requests-toolbelt',
        'sqlalchemy-citext',
        'sqlalchemy-utils[password, color, phone]',
        'Flask-WeasyPrint',
        'sortedcontainers',
    ],
    extras_require={
        'docs': [
            'sphinx',
            'sphinxcontrib-httpdomain >= 1.5.0',
            'sphinxcontrib-plantuml >= 0.12',
            'sphinxcontrib-websupport >= 1.0.1',
        ],
        'docs-auto': ['sphinx-autobuild'],
        'test': test_requires,
    },
    tests_require=test_requires,
    entry_points={'console_scripts': ['dh = ereuse_devicehub.cli:cli']},
    setup_requires=['pytest-runner'],
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
    ],
)
