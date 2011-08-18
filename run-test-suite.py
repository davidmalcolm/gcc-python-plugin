#   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011 Red Hat, Inc.
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

# Test cases are in the form of subdirectories of the "tests" directory; any
# subdirectory containing a "script.py" is regarded as a test case.
#
# A test consists of:
#   input.c: C source code to be compiled
#   script.py: a Python script to be run by GCC during said compilation
#   stdout.txt: (optional) the expected stdout from GCC (empty if not present)
#   stderr.txt: (optional) as per stdout.txt
#   getopts.py: (optional) if present, stdout from this script is
#               added to GCC's invocation options
#
# This runner either invokes all tests, or just a subset, if supplied the
# names of the subdirectories as arguments.  All test cases within the given
# directories will be run.

import glob
import os
import re
import sys
from distutils.sysconfig import get_python_inc
from subprocess import Popen, PIPE

import six

from cpybuilder import CommandError

class CompilationError(CommandError):
    def __init__(self, out, err, p, args):
        CommandError.__init__(self, out, err, p)
        self.args = args
        
    def _describe_activity(self):
        return 'compiling: %s' % ' '.join(self.args)

class TestStream:
    def __init__(self, exppath):
        self.exppath = exppath
        if os.path.exists(exppath):
            with open(exppath) as f:
                expdata = f.read()
            # The expected data is for Python 2
            # Apply python3 fixups as necessary:
            if six.PY3:
                expdata = expdata.replace('<type ', '<class ')
                expdata = expdata.replace('__builtin__', 'builtins')
                # replace long literals with int literals:
                expdata = re.sub('([0-9]+)L', '\g<1>', expdata)
                expdata = re.sub('(0x[0-9a-f]+)L', '\g<1>', expdata)
                expdata = expdata.replace('struct PyStringObject',
                                          'struct PyBytesObject')
            # The expected data is for 64-bit builds of Python
            # Fix it up for 32-bit builds as necessary:
            if six.MAXSIZE == 0x7fffffff:
                expdata = expdata.replace('"Py_ssize_t *" (pointing to 64 bits)',
                                          '"Py_ssize_t *" (pointing to 32 bits)')
            self.expdata = expdata
        else:
            self.expdata = ''

    def _cleanup(self, text):
        result = ''

        # Debug builds of Python add reference-count logging lines of
        # this form:
        #   "[84507 refs]"
        # Strip such lines out:
        text = re.sub(r'(\[[0-9]+ refs\]\n)', '', text)
        for line in text.splitlines():
            if line.startswith("Preprocessed source stored into"):
                # Handle stuff like this that changes every time:
                # "Preprocessed source stored into /tmp/ccRm9Xgx.out file, please attach this to your bugreport."
                continue
            # Remove exact pointer addresses from repr():
            line = re.sub(' object at (0x[0-9a-f]*)>',
                          ' object at 0xdeadbeef>',
                          line)
            result += line + '\n'
        return result

    def check_for_diff(self, out, err, p, args, label, writeback):
        actual = self._cleanup(self.actual)
        expdata = self._cleanup(self.expdata)
        if writeback:
            # Special-case mode: don't compare, instead refresh the "gold"
            # output by writing back to disk:
            if self.expdata == '':
                with open(self.exppath, 'w') as f:
                    f.write(actual)
            return
        if actual != expdata:
            raise UnexpectedOutput(out, err, p, args, self, label)

    def diff(self, label):
        from difflib import unified_diff
        result = ''
        for line in unified_diff(self.expdata.splitlines(),
                                 self.actual.splitlines(),
                                 fromfile='Expected %s' % label,
                                 tofile='Actual %s' % label,
                                 lineterm=""):
            result += '%s\n' % line
        return result

class UnexpectedOutput(CompilationError):
    def __init__(self, out, err, p, args, stream, label):
        CompilationError.__init__(self, out, err, p, args)
        self.stream = stream
        self.label = label
    
    def _extra_info(self):
        return self.stream.diff(self.label)


def run_test(testdir):
    # Compile each 'input.c', using 'script.py'
    # Assume success and empty stdout; compare against expected stderr, or empty if file not present
    c_input = os.path.join(testdir, 'input.c')
    outfile = os.path.join(testdir, 'output.o')
    script_py = os.path.join(testdir, 'script.py')
    out = TestStream(os.path.join(testdir, 'stdout.txt'))
    err = TestStream(os.path.join(testdir, 'stderr.txt'))

    env = dict(os.environ)
    env['LC_ALL'] = 'C'

    # Generate the command-line for invoking gcc:
    args = ['gcc']
    args += ['-c'] # (don't run the linker)
    args += ['-o', outfile]
    args += ['-fplugin=%s' % os.path.abspath('python.so'),
             '-fplugin-arg-python-script=%s' % script_py]

    # Special-case: add the python include dir (for this runtime) if the C code
    # uses Python.h:
    with open(c_input, 'r') as f:
        code = f.read()
    if '#include <Python.h>' in code:
        args += ['-I' + get_python_inc()]

    # If there's a getopts.py, run it to get additional test-specific
    # command-line options:
    getopts_py = os.path.join(testdir, 'getopts.py')
    if os.path.exists(getopts_py):
        p = Popen([sys.executable, getopts_py], stdout=PIPE, stderr=PIPE)
        opts_out, opts_err = p.communicate()
        if six.PY3:
            opts_out = opts_out.decode()
            opts_err = opts_err.decode()
        c = p.wait()
        if c != 0:
            raise CommandError()
        args += opts_out.split()

    # and the source file goes at the end:
    args += [c_input]

    # Invoke the compiler:
    p = Popen(args, env=env, stdout=PIPE, stderr=PIPE)
    out.actual, err.actual = p.communicate()
    if six.PY3:
        out.actual = out.actual.decode()
        err.actual = err.actual.decode()
    #print 'out: %r' % out.actual
    #print 'err: %r' % err.actual
    c = p.wait()

    # Check exit code:
    if err.expdata == '':
        # Expect a successful exit:
        if c != 0:
            raise CompilationError(out.actual, err.actual, p, args)
        assert os.path.exists(outfile)
    else:
        # Expect a failed exit:
        if c == 0:
            sys.stderr.write(out.diff('stdout'))
            sys.stderr.write(err.diff('stderr'))
            raise CompilationError(out.actual, err.actual, p, args)
    
    out.check_for_diff(out.actual, err.actual, p, args, 'stdout', 0)
    err.check_for_diff(out.actual, err.actual, p, args, 'stderr', 0)


from optparse import OptionParser
parser = OptionParser()
parser.add_option("-x", "--exclude",
                  action="append",
                  type="string",
                  dest="excluded_dirs",
                  help="exclude tests in DIR and below", metavar="DIR")
(options, args) = parser.parse_args()

# print (options, args)

def find_tests_below(path):
    result = []
    for dirpath, dirnames, filenames in os.walk(path):
        if 'script.py' in filenames:
            result.append(dirpath)
    return result


if len(args) > 0:
    # Just run the given tests (or test subdirectories)
    testdirs = []
    for path in args:
        testdirs += find_tests_below(path)
else:
    # Run all the tests
    testdirs = find_tests_below('tests')

def exclude_test(test):
    if test in testdirs:
        testdirs.remove(test)

# Handle exclusions:
if options.excluded_dirs:
    for path in options.excluded_dirs:
        for test in find_tests_below(path):
            exclude_test(test)

# Certain tests don't work on 32-bit
if six.MAXSIZE == 0x7fffffff:
    # These two tests verify that we can detect int vs Py_ssize_t mismatches,
    # but on 32-bit these are the same type, so don't find anything:
    exclude_test('tests/cpychecker/PyArg_ParseTuple/with_PY_SSIZE_T_CLEAN')
    exclude_test('tests/cpychecker/PyArg_ParseTuple/without_PY_SSIZE_T_CLEAN')

    # One part of the expected output for this test assumes int vs Py_ssize_t
    # mismatch:
    exclude_test('tests/cpychecker/PyArg_ParseTuple/incorrect_converters')

num_passes = 0
failed_tests = []
for testdir in testdirs:
    try:
        sys.stdout.write('%s: ' % testdir)
        run_test(testdir)
        print('OK')
        num_passes += 1
    except RuntimeError:
        err = sys.exc_info()[1]
        print('FAIL')
        print(err)
        failed_tests.append(testdir)

def num(count, singular, plural):
    return '%i %s' % (count, singular if count == 1 else plural)

print('%s; %s' % (num(num_passes, "success", "successes"),
                  num(len(failed_tests), "failure", "failures")))
if len(failed_tests) > 0:
    print('Failed tests:')
    for test in failed_tests:
        print('  %s' % test)
    sys.exit(1)

