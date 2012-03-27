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

# Code for handling compatibility between different GCC versions

import gcc
import gccutils

# The checker need to be able to access global declarations for exception
# objects, such as:
#    PyAPI_DATA(PyObject *) PyExc_MemoryError;
# and of type objects, such as:
#    PyAPI_DATA(PyTypeObject) PyList_Type;
#
# Originally we did this using gccutils.get_global_vardecl_by_name(), which
# walks the translation units' top-level blocks looking for gcc.VarDecl
# Unfortunately as of GCC PR debug/51410 (in 4.7 onwards), those that aren't
# directly referenced by the code being compiled get stripped (to condense
# the debug data), and so we can't see them anymore.
# However, GCC 4.7 gained a PLUGIN_FINISH_DECL event, so we can use that
# instead to gather the decls for later use.
#
# See https://fedorahosted.org/gcc-python-plugin/ticket/21

class CouldNotFindVarDecl(RuntimeError):
    def __init__(self, varname):
        self.varname = varname
    def __str__(self):
        return ('could not find expected global variable %r'
                % self.varname)

if hasattr(gcc, 'PLUGIN_FINISH_DECL'):
    # GCC 4.7 and later
    global_exceptions = {}
    global_typeobjs = {}

    def on_finish_decl(*args):
        # GCC 4.7 and later: callback to the PLUGIN_FINISH_DECL event
        # print(args) # FIXME: why two args?

        global global_exceptions
        global global_typeobjs

        decl = args[0]
        if isinstance(decl, gcc.VarDecl):
            if decl.name:
                if decl.name.startswith('PyExc_'):
                    global_exceptions[decl.name] = decl
                if decl.name.endswith('_Type'):
                    global_typeobjs[decl.name] = decl

    def _get_exception_decl_by_name(exc_name):
        return global_exceptions[exc_name]

    def _get_typeobject_decl_by_name(typeobjname):
        return global_typeobjs[typeobjname]

else:
    # GCC 4.6 doesn't have PLUGIN_FINISH_DECL, but
    # gccutils.get_global_vardecl_by_name() finds the declarations we need

    def _get_exception_decl_by_name(exc_name):
        return gccutils.get_global_vardecl_by_name(exc_name)

    def _get_typeobject_decl_by_name(typeobjname):
        return gccutils.get_global_vardecl_by_name(typeobjname)

def get_exception_decl_by_name(exc_name):
    exc_decl = _get_exception_decl_by_name(exc_name)
    if not exc_decl:
        raise CouldNotFindVarDecl(exc_name)
    return exc_decl

def get_typeobject_decl_by_name(typeobjname):
    typeobjdecl = _get_typeobject_decl_by_name(typeobjname)
    if not typeobjdecl:
        raise CouldNotFindVarDecl(typeobjname)
    return typeobjdecl
