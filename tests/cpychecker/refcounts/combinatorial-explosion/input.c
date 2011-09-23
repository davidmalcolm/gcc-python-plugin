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
  Verify that the refcount checker can cope with a combinatorial explosion

  Each function call below can have two possible outcomes on the refcount
  of the object.
*/

PyObject *
test_adding_module_objects(PyObject *m)
{
    PyObject *item = PyString_FromString("foo");
    if (!item) {
        return NULL;
    }

    /*
      Each of these function calls steals a reference to the object if it
      succeeds, but can fail.

      Hence the expected ereference count can change at each function call, so
      that (in theory) there are 2^N possible outcomes.

      The point of the test is to verify that the checker doesn't take O(2^N)
      time for such a case.
    */

    Py_INCREF(item);
    PyModule_AddObject(m, "item_001", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_002", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_003", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_004", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_005", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_006", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_007", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_008", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_009", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_010", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_011", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_012", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_013", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_014", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_015", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_016", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_017", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_018", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_019", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_020", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_021", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_022", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_023", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_024", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_025", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_026", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_027", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_028", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_029", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_030", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_031", item);

    Py_INCREF(item);
    PyModule_AddObject(m, "item_032", item);

    return item;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
