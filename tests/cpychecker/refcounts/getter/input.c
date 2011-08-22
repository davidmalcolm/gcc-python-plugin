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
  Verify that the analyser can cope with getters for
  PyObject subclasses
*/

struct MySubclass {
    PyObject_HEAD
    struct foo *f;
};

extern PyObject *make_wrapper(struct foo *f);

static PyObject *
simple_getter(struct MySubclass *self, void *closure)
{
    /*
      The analyser should assume that self is non-NULL
      and thus not report a NULL ptr dereference below:
    */

    return make_wrapper(self->f);
}

static PyGetSetDef gcc_Variable_getset_table[] = {
    {"test_attrib",
     (getter)simple_getter,
     (setter)NULL,
     NULL,
     NULL},
    {NULL}  /* Sentinel */
};

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
