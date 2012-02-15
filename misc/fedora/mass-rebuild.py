#   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012 Red Hat, Inc.
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

import datetime
import glob
import os
import re
import shutil
from subprocess import check_output, Popen, PIPE
import sys
import webbrowser

from bugreporting import NewBug, BugReportDb
from makeindex import gather_html_reports

def nvr_from_srpm_path(path):
    filename = os.path.basename(path)
    m = re.match('(.+)-(.+)-(.+).src.rpm', filename)
    name, version, release = m.groups()
    return name, version, release

def get_local_python_srpms():
    """
    Extract a list of srpm names that require python 2 to build
    """
    cmd = ['rpm',
           '-q',
           '--qf=%{sourcerpm}\\n',
           '--whatrequires',
           'libpython2.7.so.1.0()(64bit)']
    out = check_output(cmd)
    result = set()
    for line in out.splitlines():
        m = re.match('(.+)-(.+)-(.+)', line)
        name, version, release = m.groups()
        result.add(name)
    return sorted(result)

#print(get_local_python_srpms())
#sys.exit(0)

"""
for srpmname in get_local_python_srpms():
    cmd = ['mock',
           '-r', 'fedora-16-x86_64',
           '--scm-enable',
           '--scm-option', 'method=git',
           '--scm-option', 'git_get="git clone SCM_BRN git://pkgs.fedoraproject.org/SCM_PKG.git SCM_PKG"',
           '--scm-option', 'package=%s' % srpmname,
           '-v']
    p = Popen(cmd)
    p.communicate()
"""

def get_result_dir(srpmpath):
    n, v, r = nvr_from_srpm_path(srpmpath)
    resultdir = 'LOGS/%s-%s-%s' % (n, v, r)
    return resultdir

def local_rebuild_of_srpm_in_mock(srpmpath, mockcfg):
    """
    Rebuild the given SRPM locally within mock, injecting the cpychecker
    code in RPM form; gathering the results to a subdir within "LOGS"
    """
    def run_mock(commands, captureOut=False, captureErr=False):
        cmds = ['mock', '-r', mockcfg, '--disable-plugin=ccache'] + commands
        print('--------------------------------------------------------------')
        print(' '.join(cmds))
        print('--------------------------------------------------------------')
        args = {}
        if captureOut:
            args['stdout'] = PIPE
        if captureErr:
            args['stderr'] = PIPE
        p = Popen(cmds, **args)
        out, err = p.communicate()
        return out, err

    resultdir = get_result_dir(srpmpath)
    if os.path.exists(resultdir):
        shutil.rmtree(resultdir)
    os.mkdir(resultdir)
        
    # Experimenting with the script is much faster if we remove the --init here:
    if 1:
        run_mock(['--init'])
    run_mock(['--installdeps', srpmpath])

    # Install the pre-built plugin:
    run_mock(['install', PLUGIN_PATH]) # this doesn't work when cleaned: can't open state.log

    # Copy up latest version of the libcpychecker code from this working copy
    # overriding the copy from the pre-built plugin:
    if 1:
        for module in glob.glob('../../libcpychecker/*.py'):
            HACKED_PATH='/usr/lib/gcc/x86_64-redhat-linux/4.6.2/plugin/python2/libcpychecker'
            # FIXME: ^^ this will need changing
            run_mock(['--copyin', module, HACKED_PATH])

    # Locate existing __global_cflags so that we can prepend our flags to it:
    out, err = run_mock(['--chroot',  'rpm --eval "%{__global_cflags}"'],
                        captureOut=True)
    global_cflags = out.strip()
    # print('global_cflags: %r' % global_cflags)

    # Create script within chroot:
    SCRIPT_PATH='/test.py'
    run_mock(['--copyin', 'test.py', SCRIPT_PATH])

    # Rebuild src.rpm, using the script:
    run_mock(['--rebuild', srpmpath,

              '--no-clean',

              # setting revised cflags so as to use the script:
              # FIXME: calling this repeatedly with --init disabled leads to
              # an accumulation of multiple copies of our flags at the front of __global_cflags
              ('--define=__global_cflags -fplugin=python2 -fplugin-arg-python2-script=%s %s'
               % (SCRIPT_PATH, global_cflags))
              ])

    # Extract build logs:
    shutil.copy('/var/lib/mock/%s/result/build.log' % mockcfg,
                resultdir)

    # Scrape out *refcount-errors.html:
    BUILD_PREFIX='/builddir/build/BUILD'
    out, err = run_mock(['chroot',
                         'find %s -name *-refcount-errors.html' % BUILD_PREFIX],
                        captureOut=True)
    for line in out.splitlines():
        if line.endswith('-refcount-errors.html'):
            # Convert from e.g.
            #    '/builddir/build/BUILD/gst-python-0.10.19/gst/.libs/gstmodule.c.init_gst-refcount-errors.html'
            # to:
            #    'gst-python-0.10.19/gst/.libs/gstmodule.c.init_gst-refcount-errors.html"
            dstPath = line[len(BUILD_PREFIX)+1:]

            # Place it within resultdir:
            dstPath = os.path.join(resultdir, dstPath)

            # Lazily construct directory hierarchy:
            dirPath = os.path.dirname(dstPath)
            if not os.path.exists(dirPath):
                os.makedirs(dirPath)
            # Copy the file from the chroot to our result location:
            run_mock(['--copyout', line, dstPath])

PLUGIN_PATH='gcc-python2-plugin-0.9-1.fc16.x86_64.rpm'
MOCK_CONFIG='fedora-16-x86_64'

def prepare_bug_report(srpmpath):
    srpmname, version, release = nvr_from_srpm_path(srpmpath)

    resultdir = get_result_dir(srpmpath)
    # Open local copy of results for manual inspection:
    webbrowser.open(os.path.join(resultdir, 'index.html'))

    today = datetime.date.today()
    datestr = today.isoformat() # e.g. "2012-02-15"

    # Emit shell commands to be run.
    # These aren't yet done automatically, since we really ought to have the
    # manual review from above.
    mkdircmd = 'ssh dmalcolm@fedorapeople.org mkdir public_html/gcc-python-plugin/%(datestr)s' % locals()
    print(mkdircmd)
    scpcmd = 'scp -r %(resultdir)s dmalcolm@fedorapeople.org:public_html/gcc-python-plugin/%(datestr)s' % locals()
    print(scpcmd)

    reporturl = 'http://fedorapeople.org/~dmalcolm/gcc-python-plugin/%(datestr)s/%(srpmname)s-%(version)s-%(release)s/' % locals()

    # FIXME:
    gitversion='073d390de53ef52136bd90e5ac06f1ef833d047d'

    comment = """
Description of problem:
I've been writing an experimental static analysis tool to detect bugs commonly occurring within C Python extension modules:
  https://fedorahosted.org/gcc-python-plugin/
  http://gcc-python-plugin.readthedocs.org/en/latest/cpychecker.html
  http://fedoraproject.org/wiki/Features/StaticAnalysisOfPythonRefcounts

I ran the latest version of the tool (in git master; post 0.9) on
%(srpmname)s-%(version)s-%(release)s.src.rpm, and it reports various errors.

You can see a list of errors here, triaged into categories (from most significant to least significant):
%(reporturl)s

FIXME: add notes on the bugs here

There may of course be other bugs in my checker tool.

Hope this is helpful; let me know if you need help reading the logs that the tool generates - I know that it could use some improvement.

Version-Release number of selected component (if applicable):
%(srpmname)s-%(version)s-%(release)s
gcc-python-plugin post-0.9 git %(gitversion)s running the checker in an *f16* chroot
""" % locals()

    bug = NewBug(product='Fedora',
                 version='rawhide',
                 component=srpmname,
                 summary=('Bugs found in %s-%s-%s using gcc-with-cpychecker'
                          ' static analyzer' % (srpmname, version, release)),
                 comment=comment,
                 blocked=['cpychecker'],
                 bug_file_loc=reporturl)
    bugurl = bug.make_url()
    webbrowser.open(bugurl)

# Rebuild all src.rpm files found in "SRPMS" as necessary:
if 1:
    for srpmpath in sorted(glob.glob('SRPMS/*.src.rpm')):

        srpmname, version, release = nvr_from_srpm_path(srpmpath)

        bugdb = BugReportDb()
        # print(bugdb.bugs)
        statuses = bugdb.find(srpmname)
        if statuses:
            for status in statuses:
                print(status.get_status())
            continue

        resultdir = get_result_dir(srpmpath)
        if not os.path.exists(resultdir):
            local_rebuild_of_srpm_in_mock(srpmpath, MOCK_CONFIG)
        gather_html_reports(resultdir, 'Errors seen in %s' % resultdir)
        prepare_bug_report(srpmpath)
        break

# TODO:
# - automate grabbing the src.rpms; see e.g.:
#     http://download.fedora.devel.redhat.com/pub/fedora/linux/releases/16/Everything/source/SRPMS/
#     http://download.fedora.devel.redhat.com/pub/fedora/linux/development/17/source/SRPMS/
