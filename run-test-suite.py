import glob
import os
import sys

from subprocess import Popen, PIPE
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
            self.expdata = open(exppath).read()
        else:
            self.expdata = ''

    def check_for_diff(self, out, err, p, args, label):
        if self.actual != self.expdata:
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
    env['PYTHONPATH'] = os.getcwd()

    args = ['gcc']
    args += ['-c']
    args += ['-o', outfile]
    args += ['-fplugin=%s' % os.path.abspath('python.so'),
             '-fplugin-arg-python-script=%s' % script_py]
    #args += cflags.split()
    #args += ['-Wall',  '-Werror'] # during testing
    #args += ['-shared'] # not sure why this is necessary
    #if extra_cflags:
    #    args += extra_cflags
    args += [c_input]
    #print args

    # Invoke the compiler:
    p = Popen(args, env=env, stdout=PIPE, stderr=PIPE)
    out.actual, err.actual = p.communicate()
    #print 'out: %r' % out.actual
    #print 'err: %r' % err.actual
    c = p.wait()
    if c != 0:
        raise CompilationError(out.actual, err.actual, p, args)
    
    assert os.path.exists(outfile)
    out.check_for_diff(out.actual, err.actual, p, args, 'stdout')
    err.check_for_diff(out.actual, err.actual, p, args, 'stderr')

had_errors = False
testdirs = sorted(glob.glob('tests/*'))
for testdir in testdirs:
    try:
        print ('%s: ' % testdir),
        run_test(testdir)
        print 'OK'
    except RuntimeError, err:
        had_errors = True
        print 'FAIL'
        print err
    
if had_errors:
    sys.exit(1)

