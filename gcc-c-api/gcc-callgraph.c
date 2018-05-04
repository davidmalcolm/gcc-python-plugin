/*
   Copyright 2012, 2013, 2015 David Malcolm <dmalcolm@redhat.com>
   Copyright 2012, 2013, 2015 Red Hat, Inc.

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

#include "gcc-callgraph.h"
#include "tree.h"
#include "cgraph.h"
#include "ggc.h"
#include "tree-ssa-alias.h"
#include "basic-block.h"
#if (GCC_VERSION >= 4009)
#include "tree-ssa-alias.h" /* needed by gimple.h in 4.9 */
#include "internal-fn.h" /* needed by gimple.h in 4.9 */
#include "is-a.h" /* needed by gimple.h in 4.9 */
#include "predict.h" /* needed by gimple.h in 4.9 */
#include "gimple-expr.h" /* needed by gimple.h in 4.9 */
#endif
#include "gimple.h"

/***********************************************************
   gcc_cgraph_node
************************************************************/
GCC_IMPLEMENT_PRIVATE_API (struct gcc_cgraph_node)
gcc_private_make_cgraph_node (struct cgraph_node *inner)
{
  struct gcc_cgraph_node result;
  result.inner = inner;
  return result;
}

GCC_PUBLIC_API (void) gcc_cgraph_node_mark_in_use (gcc_cgraph_node node)
{
  /* As of gcc 4.9, a cgraph_node inherits from symtab node and uses that
     struct's marking routine.
  */
#if (GCC_VERSION >= 4009)
  gt_ggc_mx_symtab_node (node.inner);
#else
  gt_ggc_mx_cgraph_node (node.inner);
#endif
}

GCC_PUBLIC_API (gcc_function_decl)
gcc_cgraph_node_get_decl (gcc_cgraph_node node)
{
  /* gcc 4.8 eliminated the
       tree decl;
     field of cgraph_node in favor of
       struct symtab_node_base symbol;

     gcc 4.9 made cgraph_node inherit from symtab_node_base, renaming
     the latter to symtab_node.
  */
  tree decl;

#if (GCC_VERSION >= 4009)
  /* Access decl field of parent class, symtab_node */
  decl = node.inner->decl;
#else
#  if (GCC_VERSION >= 4008)
  decl = node.inner->symbol.decl;
#  else
  decl = node.inner->decl;
#  endif
#endif

  return gcc_private_make_function_decl (decl);
}

GCC_PUBLIC_API (bool)
gcc_cgraph_node_for_each_callee (gcc_cgraph_node node,
				 bool (*cb) (gcc_cgraph_edge edge,
					     void *user_data),
				 void *user_data)
{
  struct cgraph_edge *edge;

  for (edge = node.inner->callees; edge; edge = edge->next_callee)
    {
      if (cb (gcc_private_make_cgraph_edge (edge), user_data))
	{
	  return true;
	}
    }
  return false;
}

GCC_PUBLIC_API (bool)
gcc_cgraph_node_for_each_caller (gcc_cgraph_node node,
				 bool (*cb) (gcc_cgraph_edge edge,
					     void *user_data),
				 void *user_data)
{
  struct cgraph_edge *edge;

  for (edge = node.inner->callers; edge; edge = edge->next_caller)
    {
      if (cb (gcc_private_make_cgraph_edge (edge), user_data))
	{
	  return true;
	}
    }
  return false;
}

/***********************************************************
   gcc_cgraph_edge
************************************************************/
GCC_IMPLEMENT_PRIVATE_API (struct gcc_cgraph_edge)
gcc_private_make_cgraph_edge (struct cgraph_edge *inner)
{
  struct gcc_cgraph_edge result;
  result.inner = inner;
  return result;
}

GCC_PUBLIC_API (void) gcc_cgraph_edge_mark_in_use (gcc_cgraph_edge edge)
{
  gt_ggc_mx_cgraph_edge (edge.inner);
}

GCC_PUBLIC_API (gcc_cgraph_node)
gcc_cgraph_edge_get_caller (gcc_cgraph_edge edge)
{
  return gcc_private_make_cgraph_node (edge.inner->caller);
}

GCC_PUBLIC_API (gcc_cgraph_node)
gcc_cgraph_edge_get_callee (gcc_cgraph_edge edge)
{
  return gcc_private_make_cgraph_node (edge.inner->callee);
}

GCC_PUBLIC_API (gcc_gimple_call)
gcc_cgraph_edge_get_call_stmt (gcc_cgraph_edge edge)
{
  return gcc_private_make_gimple_call (edge.inner->call_stmt);
}

GCC_PUBLIC_API (bool)
gcc_for_each_cgraph_node (bool (*cb) (gcc_cgraph_node node, void *user_data),
			  void *user_data)
{
  struct cgraph_node *node;

  /*
    gcc 4.7 introduced FOR_EACH_DEFINED_FUNCTION
    gcc 4.8 eliminated: extern GTY(()) struct cgraph_node *cgraph_nodes;
    FIXME: does this only visit *defined* functions then?
  */
#if (GCC_VERSION >= 4008)
  FOR_EACH_DEFINED_FUNCTION(node)
#else
  for (node = cgraph_nodes; node; node = node->next)
#endif
    {
      if (cb (gcc_private_make_cgraph_node (node), user_data))
	{
	  return true;
	}
    }
  return false;
}

/*
Local variables:
c-basic-offset: 2
indent-tabs-mode: nil
End:
*/
