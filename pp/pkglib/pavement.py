"""
TODO: merge this with multipkg.py

See http://paver.github.com/paver for more details on it.

Oisin Mulvihill
2012-01-22

"""
import os
import sys
import os.path
import collections

from paver import easy
from paver import tasks
from paver import virtual
from paver.path import path
from paver.options import Bunch


CWD = os.path.abspath(os.curdir)


BASKET = os.environ.get("BASKET", "")
if BASKET:
    sys.stdout.write("Using Environment BASKET '%s'." % BASKET)


Dep = collections.namedtuple('Dep', ['name', 'repo', 'uri'])


# Paver global options we'll add to:
easy.options(

    # Defaults for environment:
    env=Bunch(
        name="conductor",
        script_root=path(os.path.abspath(os.environ.get("SCRIPTROOT", CWD))),
        dev_live_dir=path(os.environ.get("SCRIPTROOT", CWD)) / 'install',
    ),

    # Add extra packages i.e. virtualenv into the paver system for use in installing:
    minilib=Bunch(
        extra_files=['virtual', ]
    ),

    # Where bootstrap and install get information from
    development_env=Bunch(
        install_root=path(os.environ.get("INSTALL_ROOT", CWD)),
        env_dir="env", # relative to install root.
        env_root="", # will be configured in bootstrap() at runtime.
        src="", # will be set
        bootstrap="bootstrap.py", # will be configured in bootstrap() at runtime.
    ),

    DEV_PKGS_IN_DEP_ORDER=[
        Dep('pp-templates', 'hg', 'ssh://hg@bitbucket.org/python_pro/pp-templates'),
        Dep('pp-bookingsys-backend', 'hg', 'ssh://hg@bitbucket.org/python_pro/pp-bookingsys-backend'),
        Dep('pp-bookingsys-frontend', 'hg', 'ssh://hg@bitbucket.org/python_pro/pp-bookingsys-frontend'),
        Dep('pp-bookingsys-restclient', 'hg', 'ssh://hg@bitbucket.org/python_pro/pp-bookingsys-restclient'),
    ],
)


def git_clone(uri, target):
    """Call git clone on given uri and check it out as target.
    """
    easy.sh("git clone -b develop %s %s" % (uri, target))


def hg_clone(uri, target):
    """Call git clone on given uri and check it out as target.
    """
    easy.sh("hg clone %s %s" % (uri, target))




def write_for_run(file_name, script):
    """Handy wrapper around executable shell script creation.
    """
    fd = file(file_name, "w");
    fd.write(script)
    fd.close()
    easy.sh("chmod a+x %s" % file_name, ignore_error=True)



# --  -----------------------------------------
#
#
@easy.task
def env(options):
    """Set up the environment that the other tasks can rely on.
    """
    e = options.env
    # Set to true for a delivery going into ~/.virtualenvs
    e.is_wrappered = False
    e.env_name = ''
    e.build_root = e.script_root / 'build'
    e.build_dir = e.build_root


@easy.task
@easy.needs('env', 'generate_setup', 'minilib')
def build(options):
    """Build the RPM/DEB/XYZ package which will use paver to deliver the app.
    """
    e = options.env

    #e.build_dir.chdir()

    # Copy the paver build system minimum so it can be bootstrapped
    # and installed on the server via the RPM
    #
    #shutil.copy(e.script_root / 'pavement.py', e.build_dir)
    #shutil.copy(e.script_root / 'setup.py', e.build_dir)
    #shutil.copy(e.script_root / 'paver-minilib.zip', e.build_dir)

    # rpm / deb / other package set up here
    #


# --  Virtual Environment Configuration --------------------------------
#
#
@easy.task
def bootstrap(options):
    """create virtualenv in ./env

    This will use the system python

    """
    env = options.development_env

    # Create the virtual environment without installing paver using standard easy_install.
    # We do this so it doesn't try to get it via the network. It will be installed along
    # with other dependencies we deliver.
    #
    virtual._create_bootstrap(
        env.bootstrap,
        packages_to_install=[],
        paver_command_line=None,
        install_paver=False,
        dest_dir=env.env_root,
        no_site_packages=True,
        unzip_setuptools=True,
    )

    # Actually create the virtual from the bootstrap we just created:
    easy.sh('%s %s --no-site-packages --clear' % (sys.executable, env.bootstrap))
    env.env_root.chdir()



# --  Develop Environment Set up --------------------------------
#
#
@easy.task
@easy.needs('env')
@easy.cmdopts([
    ('install_root=', 't', "Indicates where the root install directory is located."),
    ('src=', 's', "Indicates where checked out code will go."),
])
def development_env(options):
    """Set up the environment the development environment expects.
    """
    env = options.env
    de = options.development_env

    # Figure out and set up the runtime information:
    #
    if not options.development_env.src:
        sys.stderr.write("No src location specified! Please use -s to specify.\n")
        sys.exit(1)
    else:
        de.src = path(options.development_env.src)

    de.src = path(de.src)
    de.env_name = de.install_root
    de.install_root = path(de.install_root)

    # Work out where to install. This step is used by the develop
    # task as well as the install task. If the path is absolute it
    # is used without modification. Otherwise I will look for
    # virtualenvwrapers "~/.virtualenvs" and use this over the /tmp
    # based install.
    #
    if not de.install_root.isabs():
        easy.info("Non-absolute path given. Figuring out where to go.")

        # Virtualenvwraper integrate?

        # Respect the $WORKON_HOME environment variable if it is set.
        virtualenvs = os.environ.get("WORKON_HOME")
        if virtualenvs is None:
            home = os.environ.get("HOME", '/tmp')
            virtualenvs = path(home) / ".virtualenvs"
        else:
            # Convert the path to the paver path object.
            virtualenvs = path(virtualenvs)
        if virtualenvs.isdir():
            env.is_wrappered = True
            de.install_root = virtualenvs / de.install_root
            easy.info("Installing into '%s'." % de.install_root)

        else:
            # Fail over to /tmp/<given>
            de.install_root = path('/tmp') / de.install_root

    de.install_root = path(os.path.abspath((de.install_root)))
    de.bootstrap = de.install_root / 'bootstrap.py'

    # Only append env if we are not integrating into virtualenv wrappers:
    if not env.is_wrappered:
        de.env_root = de.install_root / path(de.env_dir)
    else:
        de.env_root = de.install_root

    de.install_dir = de.install_root

    # We are running out of a source code checkout.
    de.deps = env.script_root / '..' / 'deps'
    de.install_dir.makedirs()
    easy.info("development_env: development machine install. Using '%s' for install." % de.install_dir)



# -- On dev machine, set up common environment -----------------------------------------
#
#
@easy.task
@easy.needs('development_env', 'bootstrap')
def develop(options):
    """Set up an environment to do development under.
    """
    de = options.development_env
    env = options.env

    easy.info("-- Generating development environment --")

    # RPM installed dir or source code checkout dir:
    de.install_dir.chdir()
    src_dir = path(de.src)

    # The python environment should now be install and running. Finish
    # the install using the local env's easy_install:
    python = de.env_root / 'bin' / 'python'

    # Now install the difficult packages:
    tmp = path("/tmp")
    tmp.chdir()

    # Set up the various  modules and libraries in development
    # mode so changes can be made in place, rather then building
    # and reinstalling each time
    easy.info("-- Setting  packages in development mode --")

    # Get the source code:
    #
    if not src_dir.isdir():
        # Make the src checkout dir
        print("Source checkout dir '%s' not present. Making." % src_dir)
        os.makedirs(src_dir)

    for dev_pkg in options.DEV_PKGS_IN_DEP_ORDER:
        src_dir.chdir()
        t = src_dir / dev_pkg.name

        # Get code if the checkout isn't present already:
        if not t.isdir() and dev_pkg.repo == 'git':
            git_clone(dev_pkg.uri, dev_pkg.name)
        elif not t.isdir() and dev_pkg.repo == 'hg':
            hg_clone(dev_pkg.uri, dev_pkg.name)

        # Change into the checkout dir and do the setup.py develop
        # if there is a setup.py present.
        #
        t.chdir()

        # Set up the
        setup_py = t / 'setup.py'
        if setup_py.isfile():
            easy.info("Setting up '{0}': ".format(dev_pkg))
            stdout = easy.sh("{python} setup.py develop {BASKET} ".format(
                    python=python,
                    BASKET=BASKET
                ),
                capture=True,
            )
            easy.info(stdout)

    # Add the hook to change into the source directory when workon is called.
    if env.is_wrappered:
        postactivate = de.env_root / 'bin' / 'postactivate'
        write_for_run(postactivate, ("""
#!/bin/bash
echo "Changing into source code checkout directory '%(src_dir)s'."
cd %(src_dir)s

        """ % locals()).strip())


    activate = de.env_root / 'bin' / 'activate'

    msg = """
=======================================
Development Environment Set Up Complete
=======================================

To activate the environment call:

    source %(activate)s

To stop using the development environment call:

    deactivate

    """ % locals()

    if not options.is_wrappered:
        easy.info(msg)

    else:
        name = de.env_name.strip()
        msg = """

=======================================
Development Environment Set Up Complete
=======================================

To activate the environment you can now use:

    workon %(name)s

To stop using the development environment call:

    deactivate

        """ % locals()
        easy.info(msg)
