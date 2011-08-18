/*
   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011 Red Hat, Inc.

   This is free software: you can redistribute it and/or modify it
   under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see
   <http://www.gnu.org/licenses/>.
*/

/*
  The Python source tree uses "O!" in a couple of places with explicit PyObject
  subclassses:

Objects/funcobject.c: In function ‘func_new’:
Objects/funcobject.c:377:37: error: Mismatching type in call to PyArg_ParseTupleAndKeywords with format code "O!O!|OOO:function" [-fpermissive]
  argument 6 ("&code") had type
    "struct PyCodeObject * *"
  but was expecting
    "PyObject * *"
  for format code "O!"

Objects/typeobject.c: In function ‘super_init’:
Objects/typeobject.c:6632:26: error: Mismatching type in call to PyArg_ParseTuple with format code "O!|O:super" [-fpermissive]
  argument 4 ("&type") had type
    "struct PyTypeObject * *"
  but was expecting
    "PyObject * *"
  for format code "O!"

  "O!" does check that the object is of the appropriate type, so the usage is
  reasonable.

  This plugin itself uses it in a few places. FIXME: does it?

  We can examine a struct and verify that it has the same first fields as the
  fields of a PyObject.

  But how to map back from a PyTypeObject instance to the struct?
  (i.e. how to ensure that the specific subclass type is correct?
  (we might now even have the defn of the type object)
*/
#include <Python.h>

/*
  Example of a PyTypeObject which we can't know the value of at compile time:
*/
extern PyTypeObject *unknown_type_obj_ptr;

/*
  Example of an extension type, where cpychecker has no way to associate
  the PyTypeObject with, say, "struct ExtensionObject"
*/

PyTypeObject Extension_Type = {};

PyObject *
handle_subclasses(PyObject *self, PyObject *args)
{
    PyCodeObject *code_obj;
    PyObject *base_obj;
    PyTypeObject *type_obj = NULL;
    PyLongObject *long_obj;
    struct UnknownObject *unknown_obj;
    struct ExtensionObject *extension_obj;

    if (!PyArg_ParseTuple(args, "O!O!O!O!O!O!",
                          /* This is correct, PyCode_Type -> PyCodeObject */
                          &PyCode_Type, &code_obj,

                          /* This is correct: PyCode_Type -> PyObject also */
                          &PyCode_Type, &base_obj,

                          /* This is correct: PyType_Type -> PyTypeObject*/
                          &PyType_Type, &type_obj,

                          /* This is incorrect: wrong subclass (unicode vs long): */
                          &PyUnicode_Type, long_obj,

                          /* This must report a warning; we can't know which
                             PyTypeObject is in use, and thus can't know if
                             struct UnknownObject is OK: */
                          unknown_type_obj_ptr, &unknown_obj,

                          /* This must report a warning: we don't know about
                             the association between Extension_Type and
                             struct ExtensionObject: */
                          &Extension_Type, &extension_obj)) {
        return NULL;
    }

    Py_RETURN_NONE;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
