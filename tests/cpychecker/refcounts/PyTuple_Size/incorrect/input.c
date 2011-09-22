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

#include <Python.h>

/*
  Test of incorrect call to PyTuple_Size
*/

PyObject *
test(PyObject *self, PyObject *args)
{
    PyObject *dict;
    dict = PyDict_New();

    /*
      This can go wrong in two ways:
      - if the allocation failed, then we have a read through NULL
      - it the allocation succeeded, it's a dict, not a tuple
    */
    PyTuple_Size(dict);

    /* "dict" should either be NULL or have an ob_refcnt of 1 */
    return dict;
}
static PyMethodDef test_methods[] = {
    {"test_method",  test, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
