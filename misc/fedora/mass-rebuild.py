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

import glob
import os
import re
import shutil
from subprocess import check_output, Popen, PIPE
import sys

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

    n, v, r = nvr_from_srpm_path(srpmpath)
    resultdir = 'LOGS/%s-%s-%s' % (n, v, r)
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

# Rebuild all src.rpm files found in "SRPMS":
for srpmpath in glob.glob('SRPMS/*.src.rpm'):
    local_rebuild_of_srpm_in_mock(srpmpath, MOCK_CONFIG)

