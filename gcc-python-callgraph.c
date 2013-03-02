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
#include "gcc-python.h"
#include "gcc-python-wrappers.h"
#include "gcc-c-api/gcc-callgraph.h"

/*
  Wrapper for various types in gcc/cgraph.h
    struct cgraph_edge *
    struct cgraph_node *
*/

PyObject *
PyGccCallgraphEdge_repr(struct PyGccCallgraphEdge * self)
{
    return PyGccString_FromFormat("%s()",
                                         Py_TYPE(self)->tp_name);
}

PyObject *
PyGccCallgraphEdge_str(struct PyGccCallgraphEdge * self)
{
    return PyGccString_FromFormat("%s()",
                                         Py_TYPE(self)->tp_name);
}

PyObject *
PyGccCallgraphNode_repr(struct PyGccCallgraphNode * self)
{
    return PyGccString_FromFormat("%s()",
                                         Py_TYPE(self)->tp_name);
}

PyObject *
PyGccCallgraphNode_str(struct PyGccCallgraphNode * self)
{
    return PyGccString_FromFormat("%s()",
                                         Py_TYPE(self)->tp_name);
}

IMPL_APPENDER(add_cgraph_edge_to_list,
              gcc_cgraph_edge,
              PyGccCallgraphEdge_New)

PyObject *
PyGccCallgraphNode_get_callees(struct PyGccCallgraphNode * self)
{
    IMPL_LIST_MAKER(gcc_cgraph_node_for_each_callee,
                    self->node,
                    add_cgraph_edge_to_list)
}

PyObject *
PyGccCallgraphNode_get_callers(struct PyGccCallgraphNode * self)
{
    IMPL_LIST_MAKER(gcc_cgraph_node_for_each_caller,
                    self->node,
                    add_cgraph_edge_to_list)
}

union gcc_cgraph_edge_as_ptr {
    gcc_cgraph_edge edge;
    void *ptr;
};

PyObject *
real_make_cgraph_edge_wrapper(void *ptr)
{
    struct PyGccCallgraphEdge *obj = NULL;
    union gcc_cgraph_edge_as_ptr u;
    u.ptr = ptr;

    obj = PyGccWrapper_New(struct PyGccCallgraphEdge,
                           &PyGccCallgraphEdge_TypeObj);
    if (!obj) {
        goto error;
    }

    obj->edge = u.edge;

    return (PyObject*)obj;

error:
    return NULL;
}

static PyObject *cgraph_edge_wrapper_cache = NULL;
PyObject *
PyGccCallgraphEdge_New(gcc_cgraph_edge edge)
{
    union gcc_cgraph_edge_as_ptr u;
    u.edge = edge;
    return PyGcc_LazilyCreateWrapper(&cgraph_edge_wrapper_cache,
                                     u.ptr,
                                     real_make_cgraph_edge_wrapper);
}

void
PyGcc_WrtpMarkForPyGccCallgraphEdge(PyGccCallgraphEdge *wrapper)
{
    gcc_cgraph_edge_mark_in_use(wrapper->edge);
}


union gcc_cgraph_node_as_ptr {
    gcc_cgraph_node node;
    void *ptr;
};

PyObject *
real_make_cgraph_node_wrapper(void *ptr)
{
    struct PyGccCallgraphNode *obj = NULL;
    union gcc_cgraph_node_as_ptr u;
    u.ptr = ptr;

    obj = PyGccWrapper_New(struct PyGccCallgraphNode,
                           &PyGccCallgraphNode_TypeObj);
    if (!obj) {
        goto error;
    }

    obj->node = u.node;

    return (PyObject*)obj;

error:
    return NULL;
}

void
PyGcc_WrtpMarkForPyGccCallgraphNode(PyGccCallgraphNode *wrapper)
{
    gcc_cgraph_node_mark_in_use(wrapper->node);
}


static PyObject *cgraph_node_wrapper_cache = NULL;
PyObject *
PyGccCallgraphNode_New(gcc_cgraph_node node)
{
    union gcc_cgraph_node_as_ptr u;
    u.node = node;
    return PyGcc_LazilyCreateWrapper(&cgraph_node_wrapper_cache,
					    u.ptr,
					    real_make_cgraph_node_wrapper);
}

IMPL_APPENDER(add_cgraph_node_to_list,
              gcc_cgraph_node,
              PyGccCallgraphNode_New)

PyObject *
PyGcc_get_callgraph_nodes(PyObject *self, PyObject *args)
{
    /* For debugging, see GCC's dump of things: */
    if (0) {
        fprintf(stderr, "----------------BEGIN----------------\n");
        dump_cgraph (stderr);
        fprintf(stderr, "---------------- END ----------------\n");
    }

    IMPL_GLOBAL_LIST_MAKER(gcc_for_each_cgraph_node,
                           add_cgraph_node_to_list)
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
