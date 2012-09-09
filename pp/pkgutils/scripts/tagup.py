import sys
import os
import logging
import ConfigParser
import argparse     
import shutil
import pprint

import pkg_resources

from pp.pkgutils.osutil import chdir, run
from pp.pkgutils.vcs import get_tags, get_revno, get_previous_revno
from pp.pkgutils.metadata import get_parser, get_version, Version, get_metadata

PKG_REPO=os.environ['PKG_REPO']
HG_ROOT=os.environ['HG_ROOT']

SOURCE_PACKAGE_PREFIXES = ['pp.']


def get_log():
    return logging.getLogger('pp.pkgutils.scripts.tagup')


class UserError(Exception):
    """ Errors to be raised cleanly to the user """
    pass


class PackageError(UserError):
    pass


def next_version(version):
    """
      Returns the next version after this one
    """
    v = version.version[:]
    v[2] +=1 
    return Version('.'.join([str(i) for i in v]))


def get_dist_name(pkg_dir):
    with chdir(pkg_dir):
        return get_metadata(get_parser())['name']

# --------- Distutils ------------ # 

def get_dist(dist_name):
    res = [i for i in pkg_resources.working_set if i.project_name == dist_name]
    if not res:
        raise PackageError("Distribution %s not installed" % dist_name)
    return res[0]


def is_third_party(dist):
    """
    True if this dist is 'third-party'. 
    """
    for prefix in SOURCE_PACKAGE_PREFIXES:
        if dist.project_name.startswith(prefix):
            return False
    return True


def is_src(dist):
    """
    True if this dist is a source package we could be tagging up within this environment.
    Dependant on specifying a common package prefix
    """
    for prefix in SOURCE_PACKAGE_PREFIXES:
        if dist.project_name.startswith(prefix) and not dist.location.endswith('.egg'):
            return True
    return False


def resolve_dependencies(dists):
    reqs = [i.as_requirement() for i in dists]
    return dict([(i.key, i) for i in pkg_resources.WorkingSet().resolve(reqs)])


def get_vcs_url(dist):
    """
    Return the VCS url for this dist.
    """
    # TODO: support multi-pkg repos
    return '%s/%s' % (HG_ROOT, dist.project_name.replace('.','-'))


# -------- Tagup Stages ----------- # 


def verify(dist):
    get_log().info("Verifying %s" % dist)
    with chdir(dist.location):
        diff = run(['hg','st'], capture = True)
        if diff:
            raise PackageError("Package %s has uncommitted changes at %s" % (dist.project_name, dist.location))


def update(dist):
    get_log().info("Updating %s" % dist)
    with chdir(dist.location):
        run(['hg','pull', '-u'])
        heads = run(['hg','heads', '--template','{node}-'],capture=True).split('-')[:-1]
        if len(heads) > 1:
            raise PackageError("Package %s has unmerged heads at %s" % (dist.project_name, dist.location))


def is_top_level(pkg):
    with chdir(pkg):
        parser = get_parser()
        try:
            if parser.get('tagup','top_level') == 'true':
                return True
        except (ConfigParser.NoSectionError, ConfigParser.NoOpotionError):
            pass
    return False
             

def build_dist(dist):
    get_log().info("Building %s" % dist)
    with chdir(dist.location):    
        run(['python','setup.py','egg_info','--tag-build=', 'sdist'])


def should_tag(dist):
    get_log().info("Checking if we should tag %s" % dist)
    with chdir(dist.location):
        # Using cfg version in case the env is out-of-date
        version = get_version(get_parser())
        releases = get_tags()
        get_log().debug("This version: %s" % (version))
        get_log().debug("Releases : %s" % (releases))
        if version.vstring in releases.keys():
            raise PackageError("Version %s has already been tagged" % version)

        # Check if the second last revision number is in our releases
        # Second last because creating the tag itself is one commit, and
        # rolling over the version is another.

        second_last_revno = get_previous_revno(get_previous_revno(get_revno()))
        get_log().debug("Second-last revno: %s" % second_last_revno)
        if second_last_revno in releases.values():
            get_log().info("No changes since last release")
            return False
        return version


def pin_requirements(dist, all_dists):
    """
    Override versions of things we're tagging to be explicit pins. 
    This will 'flatten' the dependency graph for anything that is third-party so that nothing 
    shifts under our feet when we install this later.
    """
    get_log().info("Pinning requirements for %s" % dist)

    with chdir(dist.location):
        parser = get_parser()
        cfg = get_metadata(parser)
        new_reqs = set()
        for req in pkg_resources.parse_requirements(cfg['install_requires']):
            if not req.key in all_dists:
                raise PackageError("Dependency %s is not installed, cannot pin to version." % req.project_name)
            req_dist = all_dists[req.key]
            if is_third_party(req_dist):
                # Flatten third-party requirement graphs.
                [new_reqs.add(i.as_requirement()) for i in resolve_dependencies([req_dist]).values()]
            else:
                new_reqs.add(all_dists[req.key].as_requirement())
        
        parser.set('metadata','install_requires',  '\n'.join(str(i) for i in new_reqs))

        # Save setup file away so we can go back to the un-pinned version
        shutil.copyfile('setup.cfg', 'setup.cfg.unpinned')

        # Write out pinned requirements 
        with open('setup.cfg', 'wb') as fp:
            parser.write(fp)
        return new_reqs


def print_plan(plan, all_deps):
    get_log().info(40 * '-')
    get_log().info("    Tagup Plan")
    get_log().info(40 * '-')
    for key in plan:
        get_log().info("    %s %s" % (key, all_deps[key].version))
        for req in sorted(plan[key]):
            get_log().info("    |-- %s" % (req))
        get_log().info(40 * '-')


def tag(dist):
    get_log().info("Tagging %s" % dist)
    with chdir(dist.location):    
        diff = run(['hg','st'], capture = True)
        if 'setup.cfg' in diff:
            get_log().info("Committing new setup.cfg") 
            run(['hg','commit','-m','Pinning requirements for version %s' % dist.version])
        run(['hg','tag', str(dist.version)])


def rollover(dist, version):
    get_log().info("Rolling over %s" % dist)
    with chdir(dist.location):    
        if os.path.isfile('setup.cfg.unpinned'):
            get_log().info("Rolling back to unpinned setup.cfg")
            shutil.move('setup.cfg.unpinned', 'setup.cfg')
        new_version = next_version(version)
        cfg = get_parser()
        cfg.set('metadata','version',new_version.vstring)
        with open('setup.cfg', 'wb') as fp:
            cfg.write(fp)
        get_log().info("New version is: %s" % new_version.vstring)


def commit(dist):
    get_log().info("Committing %s" % dist)
    with chdir(dist.location):    
        run(['hg','commit','-m','Tagged at version %s' % dist.version])


def upload(dist):
    get_log().info("Uploading %s" % dist)
    with chdir(dist.location):    
        cfg = get_parser()
        run(['scp', 'dist/%s-%s.tar.gz' % (cfg.get('metadata','name'), dist.version), PKG_REPO])

# -------- Main Run -------- #


def get_args(argv=None):
    if not argv:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description='Tag and release Python distributions.')

    parser.add_argument('distributions', metavar='DISTRIBUTIONS', type=str, nargs='+',
                       help='Python distributions to tagup ')

    return parser.parse_args(argv)


def main(argv = None):
    logging.basicConfig(level=logging.INFO)
    args = get_args(argv)
    try:
        tagup(args)
    except UserError, e:
        get_log().critical(e.args[0])
        sys.exit(1)


def tagup(args):
    tagging_dists = [get_dist(i) for i in args.distributions] 
    get_log().info("Top-level Targets:")
    [get_log().info("  %r" % i) for i in tagging_dists]

    # Gather full list of dependencies for tagging targets
    all_deps = resolve_dependencies(tagging_dists)

    #get_log().info("All dependencies:")
    #[get_log().info("  %r" % i) for i in all_deps.values()]
    
    tagging_dists = [i for i in all_deps.values() if is_src(i)]

    # Verify
    [verify(i) for i in tagging_dists]

    # Update
    # XXX 
    #[update(i) for i in tagging_dists]

    # Gather tagging targets.
    tagging_targets = {}
    for dist in tagging_dists:
        version = should_tag(dist)
        if version:
            tagging_targets[dist.key] = version
            # Set new version on our global list of packages
            all_deps[dist.key]._version = version

    if not tagging_targets:
        get_log().info("Nothing to tag")
        sys.exit(0)

    # Pin package dependencies and gather tagging plan
    plan = dict([(i.key, pin_requirements(i, all_deps)) for dist in tagging_targets.items()])

    # Print plan
    print_plan(plan, all_deps)

    # Build
    [build_dist(i) for i in tagging_dists]

    # Create Tags
    [tag(all_deps[key]) for key in tagging_targets]

    # Rollover versions
    [rollover(all_deps[key], version) for key, version in tagging_targets.items()]

    # Upload
    [upload(all_deps[key]) for key in tagging_targets]

    # Commit
    [commit(all_deps[key]) for key in tagging_targets]

if __name__ == '__main__':
    main()
