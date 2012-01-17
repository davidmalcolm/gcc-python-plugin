/*
   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
   Copyright 2012 Red Hat, Inc.

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
  Verify that the checker detects reference-count errors on PyObject
  subclasses where the object is referred to via a subclass pointer,
  and where the subclass embeds ob_refcnt and ob_type only indirectly
*/

/* The checker should treat this as a PyObject subclass */
struct FooObject {
    PyObject_HEAD
    int i;
};

/* The checker should treat this as a PyObject subclass also: */
struct BarObject {
    struct FooObject ba_head;
    int  ba_int;
    char ba_char;
};

void
test_function(struct BarObject *self)
{
    /*
      The checker ought to check the refcount of self, and complain that it
      erroneously gains 5 references:
    */
    Py_INCREF(self);
    Py_INCREF(self);
    Py_INCREF(self);
    Py_INCREF(self);
    Py_INCREF(self);
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
