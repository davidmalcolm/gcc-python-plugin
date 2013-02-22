/*
   Copyright 2012, 2013 David Malcolm <dmalcolm@redhat.com>
   Copyright 2012, 2013 Red Hat, Inc.

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

#include "gcc-variable.h"
#include "ggc.h"
#include "cgraph.h"		/* for varpool_nodes */

/***********************************************************
   gcc_variable
************************************************************/
GCC_IMPLEMENT_PRIVATE_API (struct gcc_variable)
gcc_private_make_variable (struct varpool_node *inner)
{
  struct gcc_variable result;
  result.inner = inner;
  return result;
}

GCC_IMPLEMENT_PUBLIC_API (void) gcc_variable_mark_in_use (gcc_variable var)
{
  /* Mark the underlying object (recursing into its fields): */

  /* In GCC 4.8, struct varpool_node became part of union symtab_node_def */
#if (GCC_VERSION >= 4008)
  gt_ggc_mx_symtab_node_def (var.inner);
#else
  gt_ggc_mx_varpool_node (var.inner);
#endif
}

GCC_IMPLEMENT_PUBLIC_API (gcc_tree) gcc_variable_get_decl (gcc_variable var)
{
  /* gcc 4.8 eliminated the
       tree decl;
     field of varpool_node in favor of
       struct symtab_node_base symbol;
  */
  tree decl;

#if (GCC_VERSION >= 4008)
  decl = var.inner->symbol.decl;
#else
  decl = var.inner->decl;
#endif

  return gcc_private_make_tree (decl);
}

GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_for_each_variable (bool (*cb) (gcc_variable var, void *user_data),
		       void *user_data)
{
  struct varpool_node *n;

#ifdef FOR_EACH_VARIABLE /* added in gcc 4.8 */
  FOR_EACH_VARIABLE(n)
#else
  for (n = varpool_nodes; n; n = n->next)
#endif
    {
      if (cb (gcc_private_make_variable (n), user_data))
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
