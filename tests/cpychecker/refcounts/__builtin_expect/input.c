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
  Reproducer for false-positive read-through-NULL warnings reported for
  Cython-generated code (lxml)

  For modern GCCs, Cython defines likely() and unlikely() macros in terms
  of __builtin_expect().  This was confusing our checker, which regarded it
  as an unknown function, and thus regarded the return value as unknown.

  Specifically, within the code generated for a call to:
     python.PyErr_NoMemory()
  within:
     lxml-2.3/src/lxml/apihelpers.pxi
  the generated C code contained:

    __pyx_t_5 = PyErr_NoMemory(); if (unlikely(!__pyx_t_5)) {__pyx_filename = __pyx_f[2]; __pyx_lineno = 1061; __pyx_clineno = __LINE__; goto __pyx_L1_error;}
    __Pyx_GOTREF(__pyx_t_5);

  and the checker was erroneously considering both possible outcomes of:

     if (unlikely(!__pyx_t_5)) ...

  despite knowing that __pyx_t_5 is NULL (due to the semantics of
  PyErr_NoMemory), thus erroneously reporting:

    dereferencing NULL (__pyx_t_5->ob_refcnt) at src/lxml/lxml.etree.c:19587

  for the unreachable next line:  __Pyx_GOTREF(__pyx_t_5);
*/

#define unlikely(x) __builtin_expect(!!(x), 0)

void
test(void)
{
    PyObject *obj = PyErr_NoMemory();

    /*
       The checker should know that the result of unlikely() is equal to that
       the conditional, rather than an UnknownValue
    */
    if (unlikely(!obj)) {
        return;
    }

    /* if obj == NULL, we shouldn't get here: */
    Py_DECREF(obj);
    return;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
