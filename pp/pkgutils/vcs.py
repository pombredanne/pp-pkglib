import re
import logging

from pp.pkgutils.osutil import run

RE_VERSION = re.compile('\d+\.\d+\.\d+')

def get_log():
    return logging.getLogger('pp.pkgutils.vcs')

def get_tags():
    """ Returns a list of tags for the cwd
    """
    items =  [ i.strip() for i in  \
               run(['hg','tags'], capture=True).split('\n') \
               if i.strip() ]
    res = {}
    for i in items:
        tag, rev = i.split()
        if tag == 'tip' or not RE_VERSION.match(tag): continue
        res[tag] = rev.split(':')[1]
    return res
    

def get_revno():
    """ Returns the revision number of the cwd
    """
    return run(['hg','id','-i'],capture=True).strip()


def get_previous_revno(revno):
    """ Retuns the revision number before this one, used
        for detecting similar tags.
    """
    return run(['hg','parents', '-r', revno, '--template',
                '{node}'],capture=True)[:12].strip()
