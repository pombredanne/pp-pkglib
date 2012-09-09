"""
"""
from setuptools import setup, find_packages
from ConfigParser import ConfigParser
import os
def get_metadata():
    parser = ConfigParser()
    parser.read(os.path.join(os.path.dirname(__file__),'setup.cfg'))
    return dict(parser.items('metadata'))
md = get_metadata()

TestSuite = ''

needed = [
]

EagerResources = [
]

ProjectScripts = [
]

PackageData = {
    # Include every file type in the egg file:
    '': ['*.*'],
}

# Make exe versions of the scripts:
EntryPoints = {
  'console_scripts': ['tagup=pp.pkgutils.scripts.tagup:main'],
}

setup(
#    url=ProjecUrl,
    zip_safe=False,
    name=md['name'],
    version=md['version'],
    author=md['author'],
    author_email=md['author_email'],
    description=md['summary'],
    long_description=md['summary'],
    license=md['licence'],
    test_suite=TestSuite,
    scripts=ProjectScripts,
    install_requires=needed,
    packages=find_packages(),
    package_data=PackageData,
    eager_resources = EagerResources,
    entry_points = EntryPoints,
    namespace_packages = ['pp'],

)
