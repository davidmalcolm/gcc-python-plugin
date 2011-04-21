import unittest
import tempfile

from subprocess import Popen, PIPE

from cpybuilder import CompilationUnit, SimpleModule, PyRuntime


# FIXME: this will need tweaking:
pyruntimes = [PyRuntime('/usr/bin/python2.7', '/usr/bin/python2.7-config'),
              PyRuntime('/usr/bin/python2.7-debug', '/usr/bin/python2.7-debug-config'),
              PyRuntime('/usr/bin/python3.2mu', '/usr/bin/python3.2mu-config'),
              PyRuntime('/usr/bin/python3.2dmu', '/usr/bin/python3.2dmu-config')]

class SimpleTest(unittest.TestCase):
    def test_compilation(self):
        # Verify that the module builds and runs against multiple Python runtimes
        #for runtime in pyruntimes:
        #    print(repr(runtime.get_build_flags()))

        sm = SimpleModule()
        sm.add_module_init('example', modmethods='NULL', moddoc='This is a doc string')
        print sm.cu.as_str()

        with tempfile.NamedTemporaryFile(prefix='example', suffix='.c') as f:
            f.write(sm.cu.as_str())

        runtime = pyruntimes[1]
        cflags = runtime.get_build_flags()

        args = ['gcc']
        args += ['-x', 'c'] # specify that it's C
        args += ['-o', 'example_d.so'] # FIXME: the _d is a Fedora-ism
        args += cflags.split()
        args += ['-shared'] # not sure why this is necessary
        args += ['-'] # read from stdin
        print args
        
        p = Popen(args, stdin = PIPE)
        p.communicate(sm.cu.as_str())
        c = p.wait()
        assert c == 0

        # Now verify that it built:
        p = Popen([runtime.executable,
                   '-c',
                   'import example; print(example.__file__); print(dir(example))'],
                  stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        print repr(out), repr(err)
        
        



if __name__ == '__main__':
    unittest.main()
