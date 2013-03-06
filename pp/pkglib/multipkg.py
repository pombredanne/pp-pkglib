# -*- coding: utf-8 -*-
"""
A top level helper so setup.py commands can be run on a number of
Python packages in a repository in the correct order.
"""
import sys
import subprocess
from pkglib import config, manage


def setup():
    """ Mirror pkglib's setup() method for each sub-package in this repository.
    """
    top_level_parser = config.get_pkg_cfg_parser()
    cfg = config._parse_metadata(top_level_parser, 'multipkg', ['pkg_dirs'])
    rc = [0]
    for dirname in cfg['pkg_dirs']:
        with manage.chdir(dirname):
            # Update sub-package setup.cfg with top-level version
            sub_parser = config.get_pkg_cfg_parser()
            sub_cfg = config.parse_pkg_metadata(sub_parser)
            if sub_cfg['version'] != cfg['version']:
                print ("Updating setup.cfg version for {0}: {1} -> {2}"
                       .format(dirname, sub_cfg['version'], cfg['version']))
                sub_parser.set('metadata', 'version', cfg['version'])
                with open('setup.cfg', 'w') as sub_cfg_file:
                    sub_parser.write(sub_cfg_file)

            cmd = [sys.executable, "setup.py"] + sys.argv[1:]
            print ("In directory {0}: Running '{1}'"
                   .format(dirname, ' '.join(cmd)))
            p = subprocess.Popen(cmd)
            p.communicate()
            if p.returncode != 0:
                # Here we exit straight away, unless this was a run as
                # 'python setup.py test'. Reason for this is that we want to
                # run all the packages' tests through and gather the results.
                # For any other setup.py command, a failure here is likely
                # some sort of build or config issue and it's best not to
                # plow on.
                print "Command failed with exit code {0}".format(p.returncode)
                if 'test' in cmd:
                    rc[0] = p.returncode
                else:
                    sys.exit(p.returncode)
    sys.exit(rc[0])
