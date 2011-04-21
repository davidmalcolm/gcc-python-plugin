from maketreetypes import iter_tree_types
from cpybuilder import CompilationUnit, SimpleModule

sm = SimpleModule()
sm.cu.add_include('config.h')
sm.cu.add_include('system.h')
sm.cu.add_include('coretypes.h')
sm.cu.add_include('tree.h')
sm.cu.add_decl("""
struct PyGccTree {
     PyObject_HEAD
     tree t;
};
""")

# FIXME: truncating the list for now, for sanity's sake:
for t in list(iter_tree_types())[:5]:
    #tp = PyTypeObject(name = 'PyType%s' % t.camel_cased_string(),
    #                  tp_name = 'tree.%s' % t.camel_cased_string(),
    #                  struct_name = 'struct PyGccTree')
    sm.add_type_object(name = 'tree_%sType' % t.camel_cased_string(),
                       localname = t.camel_cased_string(),
                       tp_name = 'tree.%s' % t.camel_cased_string(),
                       struct_name = 'struct PyGccTree')

sm.add_module_init('tree', modmethods='NULL', moddoc='This is a doc string')
print sm.cu.as_str()

from subprocess import Popen, PIPE, check_call


GCCPLUGINS_DIR = Popen(['gcc', '--print-file-name=plugin'], stdout=PIPE).communicate()[0].strip()


pyconfigs = ('python2.7-config',
             'python2.7-debug-config',
             'python3.2mu-config',
             'python3.2dmu-config')
             
for pyconfig in pyconfigs:
    cflags = Popen([pyconfig, '--cflags', '--ldflags'], stdout=PIPE).communicate()[0]
    args = ['gcc']
    args += ['-x', 'c'] # specify that it's C
    args += ['-o', 'test.so']
    args += cflags.split()
    args += ['-shared']
    args += ['-I%s/include' % GCCPLUGINS_DIR]
    args += ['-'] # read from stdin
    print args

    p = Popen(args, stdin = PIPE)
    p.communicate(sm.cu.as_str())
    c = p.wait()
    assert c == 0
        
    # FIXME: actually run python and import the modules!
    

#tree_types = list(iter_tree_types())

#print "#include <Python.h>"
#print "PyTypeObject *types_by_code[%i];" % len(tree_types)
#for t in iter_tree_types():
#    print ('    "%s", /* %s %s %s %s */'
#           % (t.camel_cased_string(), t.STRING, t.SYM, t.TYPE, t.NARGS))



