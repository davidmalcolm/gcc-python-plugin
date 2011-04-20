"""
Wrapper around one of gcc's "tree"

This seems to be this typedef:
  coretypes.h:60:typedef union tree_node *tree;
  coretypes.h:63:typedef const union tree_node *const_tree;

The actual union seems to be constructed via magic in .def files at compile-time
(see tree.def)
gcc/treestruct.def has:
   DEFTREESTRUCT(enumeration value, printable name).

   Each enumeration value should correspond with a single member of
   union tree_node.

In one of my builds,  "all-tree.def" contained:

#include "tree.def"
END_OF_BASE_TREE_CODES
#include "c-family/c-common.def"
#include "ada/gcc-interface/ada-tree.def"
#include "cp/cp-tree.def"
#include "java/java-tree.def"
#include "objc/objc-tree.def"

and indeed, /usr/lib/gcc/x86_64-redhat-linux/4.6.0/plugin/include/all-tree.def has that
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

cdef extern from "tree.h":
    pass

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
        
    def __repr__(self):
        return 'tree.Tree(%r)' % 'foo'


cdef extern gcc_python_make_wrapper_tree(tree t):
    obj = Tree()
    obj.__set_ptr(t)
    return obj
