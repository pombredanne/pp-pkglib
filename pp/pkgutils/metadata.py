import logging
from ConfigParser import ConfigParser
from distutils.version import LooseVersion as Version


def get_log():
       return logging.getLogger('pp.pkgutils.metadata')


def get_parser():
    """ Returns a parser for the setup.cfg in the cwd
    """
    parser = ConfigParser()
    parser.read('setup.cfg')
    return parser

MULTI_LINE_KEYS=['install_requires']
def get_metadata(parser):
    res = dict(parser.items('metadata'))
    for key in MULTI_LINE_KEYS:
        res[key] = [i.strip() for i in res[key].split() if i.strip()]
    return res

def get_version(parser):
    """ Returns the pkg version for the given setup.cfg parser
    """
    return Version(parser.get('metadata','version'))
