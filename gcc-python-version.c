/*
   Copyright 2011, 2012 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011, 2012 Red Hat, Inc.

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
#include <structseq.h>
#include "gcc-python.h"
#include "plugin-version.h"

/* Version handling: */

static struct plugin_gcc_version *actual_gcc_version;

/* Define a gcc.Version type, as a structseq */
static struct PyStructSequence_Field gcc_version_fields[] = {
    {"basever", NULL},
    {"datestamp", NULL},
    {"devphase", NULL},
    {"revision", NULL},
    {"configuration_arguments", NULL},
    {0}
};

static struct PyStructSequence_Desc gcc_version_desc = {
    "gcc.Version", /* name */
    NULL, /* doc */
    gcc_version_fields,
    5
};

PyTypeObject GccVersionType;

void
gcc_python_version_init(struct plugin_gcc_version *version)
{
    actual_gcc_version = version;
    PyStructSequence_InitType(&GccVersionType, &gcc_version_desc);
}


static PyObject *
gcc_version_to_object(struct plugin_gcc_version *version)
{
    PyObject *obj = PyStructSequence_New(&GccVersionType);
    if (!obj) {
        return NULL;
    }

#define SET_ITEM(IDX, FIELD) \
    PyStructSequence_SET_ITEM(obj, (IDX), gcc_python_string_or_none(version->FIELD));

    SET_ITEM(0, basever);
    SET_ITEM(1, datestamp);
    SET_ITEM(2, devphase);
    SET_ITEM(3, revision);
    SET_ITEM(4, configuration_arguments);

#undef SET_ITEM

    return obj;
}

PyObject *
gcc_python_get_plugin_gcc_version(PyObject *self, PyObject *args)
{
    /*
       "gcc_version" is compiled in to the plugin, as part of
       plugin-version.h:
    */
    return gcc_version_to_object(&gcc_version);
}

PyObject *
gcc_python_get_gcc_version(PyObject *self, PyObject *args)
{
    /*
       "actual_gcc_version" is passed in when the plugin is initialized
    */
    return gcc_version_to_object(actual_gcc_version);
}


/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
