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
  Verify that the checker can detect PyObject subclasses
*/

/* The checker should treat this as a PyObject subclass */
struct FooObject {
    PyObject_HEAD
    int i;
};

/* Likewise */
struct BarObject {
    PyObject_VAR_HEAD
    char *str;
};

/* Likewise */
struct BazObject {
    struct FooObject baz_head;
    int baz_int;
};

/* This isn't one: */
struct NotAnObject {
    PyObject *array[10];
};

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
