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
    code in RPM form
    """
    def run_mock(commands, captureOut=False, captureErr=False):
        cmds = ['mock', '-r', mockcfg] + commands
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
    resultdir = '%s-%s-%s' % (n, v, r)
    if os.path.exists(resultdir):
        shutil.rmtree(resultdir)
    os.mkdir(resultdir)
        
    if 0:
        run_mock(['--init'])
    run_mock(['--installdeps', srpmpath])
    run_mock(['install', PLUGIN_PATH]) # this doesn't work when cleaned: can't open state.log
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

PLUGIN_PATH='gcc-python2-plugin-0.9-1.fc16.x86_64.rpm'
MOCK_CONFIG='fedora-16-x86_64'

# For now, just an experimental hardcoded list of srpms:
local_rebuild_of_srpm_in_mock('MySQL-python-1.2.3-3.fc16.src.rpm')
local_rebuild_of_srpm_in_mock('python-crypto-2.3-5.fc16.src.rpm')
local_rebuild_of_srpm_in_mock('rpm-4.9.1.2-1.fc16.src.rpm')

