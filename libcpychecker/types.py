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

"""
Helper functions for looking up various CPython implementation types.
"""
import gcc
from gccutils import get_global_typedef, check_isinstance

def is_py3k():
    """
    Is the Python.h we're compiling against python 3?
    """
    if get_global_typedef('PyStringObject'):
        return False
    else:
        return True

def is_debug_build():
    """
    Is the Python.h we're compiling against configured --with-pydebug ?
    """
    obj = get_global_typedef('PyObject')
    return obj.type.fields[0].name == '_ob_next'

def get_Py_ssize_t():
    return get_global_typedef('Py_ssize_t')

def get_Py_buffer():
    return get_global_typedef('Py_buffer')

def Py_UNICODE():
    return get_global_typedef('Py_UNICODE')

def get_PY_LONG_LONG():
    # pyport.h can supply PY_LONG_LONG as a #define, as a typedef, or not at all
    # FIXME
    # If we have "long long", pyport.h uses that.
    # Assume so for now:
    return gcc.Type.long_long()

def get_PyObject():
    return get_global_typedef('PyObject')

def get_PyObjectPtr():
    return get_global_typedef('PyObject').pointer

def get_PyTypeObject():
    return get_global_typedef('PyTypeObject')

def get_PyStringObject():
    return get_global_typedef('PyStringObject')

def get_PyUnicodeObject():
    return get_global_typedef('PyUnicodeObject')

def get_Py_complex():
    return get_global_typedef('Py_complex')

# Python 3:
def get_PyBytesObject():
    return get_global_typedef('PyBytesObject')

# Map from name of PyTypeObject global to the typedef for the corresponding
# object structure:
type_dict = {
    'PyBuffer_Type' : 'PyBufferObject',
    'PyComplex_Type' : 'PyComplexObject',
    'PyCode_Type' : 'PyCodeObject',
    'PyDict_Type' : 'PyDictObject',
    'PyFile_Type' : 'PyFileObject',
    'PyFloat_Type' : 'PyFloatObject',
    'PyFrame_Type' : 'PyFrameObject',
    'PyFunction_Type' : 'PyFunctionObject',
    'PyInt_Type' : 'PyIntObject',
    'PyList_Type' : 'PyListObject',
    'PyLong_Type' : 'PyLongObject',
    'PyModule_Type' : 'PyModuleObject',
    'PyCapsule_Type' : 'PyCapsuleObject',
    'PyRange_Type' : 'PyRangeObject',
    'PySet_Type' : 'PySetObject',
    'PyFrozenSet_Type' : 'PyFrozenSetObject',
    'PyString_Type' : 'PyStringObject',
    'PyTuple_Type' : 'PyTupleObject',
    'PyType_Type' : 'PyTypeObject',
    'PyUnicode_Type' : 'PyUnicodeObject',
}

def get_type_for_typeobject(typeobject):
    check_isinstance(typeobject, gcc.VarDecl)
    if typeobject.name not in type_dict:
        return None

    type_name = type_dict[typeobject.name]
    return get_global_typedef(type_name)

def register_type_object(typeobject, typedef):
    check_isinstance(typeobject, gcc.VarDecl)
    type_dict[typeobject.name] = typedef
