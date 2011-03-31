"""
Wrapper around one of gcc's "tree"

This seems to be this typedef:
  coretypes.h:60:typedef union tree_node *tree;
  coretypes.h:63:typedef const union tree_node *const_tree;
"""
import sys

cdef extern from "config.h":
    pass

cdef extern from "system.h":
    pass

cdef extern from "coretypes.h":
    cdef union tree_node:
        pass
    ctypedef tree_node *tree

cdef extern from "gcc-python-wrappers.h":
   pass

cdef class Tree:
    cdef tree t

    def __init__(self):
        self.t = NULL

    cdef __set_ptr(self, tree t):
        self.t = t
        # FIXME: interaction with gcc's GC ?

    cdef __get_ptr(self, tree t):
        self.t = t
        
    #def __repr__(self):
    #    return 'optpass.OptPass(%r)' % self.ptr.name


cdef extern gcc_python_make_wrapper_tree(tree t):
    obj = Tree()
    obj.__set_ptr(t)
    return obj
