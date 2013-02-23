/*
   Copyright 2013 David Malcolm <dmalcolm@redhat.com>
   Copyright 2013 Red Hat, Inc.

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
  Regression test for:
     TypeError: (struct PyObject *)0 from tests/cpychecker/refcounts/macros/Py_XDECREF/crash/input.c:35 / ConcreteValue(gcctype='struct PyObject *', loc=gcc.Location(file='tests/cpychecker/refcounts/macros/Py_XDECREF/crash/input.c', line=35), value=0) is not an instance of <class 'libcpychecker.absinterp.PointerToRegion'>
*/

void
test(PyObject *callable, PyObject *args)
{
    /*
      This is bogus code: Py_XDECREF expands its argument multiple times,
      so the function is actually called up to 4 times
      (assuming a non pydebug build of CPython).
    */
    Py_XDECREF(PyObject_CallObject(callable, args));

    /* Seen in the wild in:
       python-alsa-1.0.25-1.fc17:
         pyalsa/alsamixer.c:179
         pyalsa/alsahcontrol.c:190
         pyalsa/alsaseq.c:3277

       python-4Suite-XML-1.0.2-14.fc17:
         Ft/Xml/src/domlette/refcounts.c:80
    */
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
