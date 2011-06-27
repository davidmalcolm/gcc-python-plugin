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
  The various format codes with a "#" work differently depending on whether
  PY_SSIZE_T_CLEAN was defined before the #include <Python.h>

  This file is #included by each of:
    with_PY_SSIZE_T_CLEAN/input.c
    without_PY_SSIZE_T_CLEAN/input.c
  to verify how well we test these variants of the API
*/
#include <Python.h>

PyObject *
hash_format_codes(PyObject *self, PyObject *args)
{
    const char *str;
    Py_UNICODE *unicode;
    char *writable_str;
    char *buffer = "I am a buffer";
    const char *encoding = "UTF-8";

    int ival;
    Py_ssize_t sval;
    char *keywords[] = {NULL};

    /*
      Verify the "s#" format code.
    */

    /* Try "s#" with an int: */
    if (!PyArg_ParseTuple(args, "s#", &str, &ival)) {
        return NULL;
    }
    if (!PyArg_ParseTupleAndKeywords(args, NULL,
                                     "s#", keywords,
                                     &str, &ival)) {
        return NULL;
    }

    /* Try "s#" with an Py_ssize_t: */
    if (!PyArg_ParseTuple(args, "s#", &str, &sval)) {
        return NULL;
    }
    if (!PyArg_ParseTupleAndKeywords(args, NULL,
                                     "s#", keywords,
                                     &str, &sval)) {
        return NULL;
    }

    /* (hopefully the above gives us sufficient coverage of the "AndKeywords"
       variants) */

    /* Try "z#" with an int... */
    if (!PyArg_ParseTuple(args, "z#", &str, &ival)) {
        return NULL;
    }

    /* ...and with a Py_ssize_t: */
    if (!PyArg_ParseTuple(args, "z#", &str, &sval)) {
        return NULL;
    }


    /* Try "u#" with an int: */
    if (!PyArg_ParseTuple(args, "u#", &unicode, &ival)) {
        return NULL;
    }

    /* ...and with a Py_ssize_t: */
    if (!PyArg_ParseTuple(args, "u#", &unicode, &sval)) {
        return NULL;
    }


    /*  Try "es#" with an int: */
    if (!PyArg_ParseTuple(args, "es#", encoding, &buffer, &ival)) {
        return NULL;
    }

    /* ...and with a Py_ssize_t: */
    if (!PyArg_ParseTuple(args, "es#", encoding, &buffer, &sval)) {
        return NULL;
    }


    /* Try "et#" with an int: */
    if (!PyArg_ParseTuple(args, "et#", encoding, &buffer, &ival)) {
        return NULL;
    }

    /* ...and with a Py_ssize_t: */
    if (!PyArg_ParseTuple(args, "et#", encoding, &buffer, &sval)) {
        return NULL;
    }


    /* Try "t#" with an int: */
    if (!PyArg_ParseTuple(args, "t#", &writable_str, &ival)) {
        return NULL;
    }

    /* ...and with a Py_ssize_t: */
    if (!PyArg_ParseTuple(args, "t#", &writable_str, &sval)) {
        return NULL;
    }


    /* Try "w#" with an int: */
    if (!PyArg_ParseTuple(args, "w#", &writable_str, &ival)) {
        return NULL;
    }

    /* ...and with a Py_ssize_t: */
    if (!PyArg_ParseTuple(args, "w#", &writable_str, &sval)) {
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
