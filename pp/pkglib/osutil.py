import os
import subprocess
import logging
from contextlib import contextmanager


def get_log():
    return logging.getLogger('pp.pkglib.osutil')


@contextmanager
def chdir(dir):
    """ Context Manager that changes to the given dir 
        and back again on exit. Much like bash's pushd and popd.

        Parameters
        ----------
        :param dir: `str`
           Directory to change to.
    """
    here = os.getcwd()
    os.chdir(dir)
    yield
    os.chdir(here)


def run(cmd, capture=False, **kwargs):
    """ Convenience wrapper around subprocess.Popen

        Parameters
        ----------
        :param capture: `bool`
            Captures and returns stdout if True
    """
    get_log().debug('run: %r' % cmd)  
    stdout = None
    if capture:
        stdout=subprocess.PIPE
    ps = subprocess.Popen(cmd,stdout=stdout, **kwargs)
    out, err = ps.communicate()
    if not ps.returncode == 0:
       get_log().error("Non-zero exit code for: %r" % cmd)
       get_log().error("Stdout: %r" % out)
       get_log().error("Stderr: %r" % err)
       raise subprocess.CalledProcessError(ps.returncode, cmd, out)
    return out
