.. Copyright 2011 David Malcolm <dmalcolm@redhat.com>
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

Interprocedural analysis (IPA)
==============================
GCC builds a "call graph", recording which functions call which other
functions, and it uses this for various optimizations.

It is constructed by the `"*build_cgraph_edges"` pass.

In case it's of interest, it is available via the following Python API:

.. py:function:: gcc.get_callgraph_nodes()

   Get a list of all :py:class:`gcc.CallgraphNode` instances

.. py:function:: gccutils.callgraph_to_dot()

   Return the GraphViz source for a rendering of the current callgraph, as a
   string.

   Here's an example of such a rendering:

   .. figure:: sample-callgraph.png
      :alt: image of a call graph

.. py:class:: gcc.CallgraphNode

   .. py:attribute:: decl

      The :py:class:`gcc.FunctionDecl` for this node within the callgraph

   .. py:attribute:: callees

      The function calls made by this function, as a list of :py:class:`gcc.CallgraphEdge` instances

   .. py:attribute:: callers

      The places that call this function, as a list of :py:class:`gcc.CallgraphEdge` instances

   Internally, this wraps a `struct cgraph_node *`

.. py:class:: gcc.CallgraphEdge

   .. py:attribute:: caller

      The function that makes this call, as a :py:class:`gcc.CallgraphNode`

   .. py:attribute:: callee

      The function that is called here, as a :py:class:`gcc.CallgraphNode`

   .. py:attribute:: call_stmt

      The :py:class:`gcc.GimpleCall` statememt for the function call

   Internally, this wraps a `struct cgraph_edge *`
