"""
Wrapper around one of gcc's "struct opt_pass *"
There seems to be a C-style class hierarchy of these within gcc/tree-pass.h
"""
import sys

cdef extern from "config.h":
    pass

cdef extern from "system.h":
    pass

cdef extern from "coretypes.h":
    pass

cdef extern from "tree-pass.h":
     cdef struct opt_pass:
         char *name

cdef extern from "gcc-python-wrappers.h":
   pass

"""
A single tree-ssa optimization pass

Wrapper around one of GCC's (struct opt_pass*)
"""
cdef class OptPass:
    cdef opt_pass *ptr

    def __init__(self):
        self.ptr = NULL

    cdef __set_ptr(self, opt_pass *ptr):
        self.ptr = ptr
        # FIXME: interaction with gcc's GC ?

    cdef __get_ptr(self, opt_pass *ptr):
        self.ptr = ptr
        
    def __repr__(self):
        return 'optpass.OptPass(%r)' % self.ptr.name


cdef extern gcc_python_make_wrapper_opt_pass(opt_pass *ptr):
    #sys.stdout.write('foo\n')
    #print "foo"
    obj = OptPass()
    obj.__set_ptr(ptr)
    return obj
