# -*- coding: utf-8 -*-
"""
A top level helper so setup.py commands can be run on a number of
Python packages in a repository in the correct order.
"""
import sys
from pkglib import config, manage, cmdline


def setup():
    """ Mirror pkglib's setup() method for each sub-package in this repository.
    """
    top_level_parser = config.get_pkg_cfg_parser()
    cfg = config._parse_metadata(top_level_parser, 'multipkg', ['pkg_dirs'])
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
            print "In directory {0}: Running '{1}'".format(dirname, ' '.join(cmd))
            cmdline.run(cmd, capture_stdout=False)
