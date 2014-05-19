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

#include "gcc-gimple.h"
#include "gcc-tree.h"
#include "gcc-internal.h"

#include "tree.h"
#include "function.h"
#include "basic-block.h"
#if (GCC_VERSION >= 4009)
//#include "alias.h" /* needed by tree-ssa-alias.h in 4.9 */
#include "tree-ssa-alias.h" /* needed by gimple.h in 4.9 */
#include "internal-fn.h" /* needed by gimple.h in 4.9 */
#include "is-a.h" /* needed by gimple.h in 4.9 */
#include "predict.h" /* needed by gimple.h in 4.9 */
#include "gimple-expr.h" /* needed by gimple.h in 4.9 */
#endif
#include "gimple.h"

#if 0
#include "params.h"
#include "cp/name-lookup.h"	/* for global_namespace */
#include "tree.h"
#include "diagnostic.h"
#include "cgraph.h"
#include "opts.h"
#include "c-family/c-pragma.h"	/* for parse_in */
#include "rtl.h"
#endif

#include <gcc-plugin.h>

GCC_IMPLEMENT_PUBLIC_API (void) gcc_gimple_mark_in_use (gcc_gimple stmt)
{
  /* Mark the underlying object (recursing into its fields): */

  /* GCC 4.9 converted gimple to a class hierarchy */
#if (GCC_VERSION >= 4009)
  gt_ggc_mx_gimple_statement_base (stmt.inner);
#else
  gt_ggc_mx_gimple_statement_d (stmt.inner);
#endif
}

GCC_IMPLEMENT_PRIVATE_API (struct gcc_gimple_phi)
gcc_private_make_gimple_phi (gimple inner)
{
  struct gcc_gimple_phi result;
  GIMPLE_CHECK (inner, GIMPLE_PHI);
  result.inner = inner;
  return result;
}

GCC_IMPLEMENT_PRIVATE_API (struct gcc_gimple_call)
gcc_private_make_gimple_call (gimple inner)
{
  struct gcc_gimple_call result;
  GIMPLE_CHECK (inner, GIMPLE_CALL);
  result.inner = inner;
  return result;
}

GCC_IMPLEMENT_PRIVATE_API (struct gcc_gimple)
gcc_private_make_gimple (gimple inner)
{
  struct gcc_gimple result;
  result.inner = inner;
  return result;
}


/***************************************************************************
 gcc_gimple
 **************************************************************************/
GCC_IMPLEMENT_PUBLIC_API (gcc_location)
gcc_gimple_get_location (gcc_gimple stmt)
{
  return gcc_private_make_location (gimple_location (stmt.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_tree) gcc_gimple_get_block (gcc_gimple stmt)
{
  return gcc_private_make_tree (gimple_block (stmt.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_tree) gcc_gimple_get_expr_type (gcc_gimple stmt)
{
  return gcc_private_make_tree (gimple_expr_type (stmt.inner));
}

/***************************************************************************
 gcc_gimple_asm
 **************************************************************************/
  GCC_IMPLEMENT_PUBLIC_API (const char *)
gcc_gimple_asm_get_string (gcc_gimple_asm stmt)
{
  return gimple_asm_string (stmt.inner);
}

/***************************************************************************
 gcc_gimple_assign
 **************************************************************************/
  GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_gimple_assign_get_lhs (gcc_gimple_assign stmt)
{
  return gcc_private_make_tree (gimple_assign_lhs (stmt.inner));
}

/***************************************************************************
 gcc_gimple_call
 **************************************************************************/
  GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_gimple_call_get_lhs (gcc_gimple_call stmt)
{
  return gcc_private_make_tree (gimple_call_lhs (stmt.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_gimple_call_get_fn (gcc_gimple_call stmt)
{
  return gcc_private_make_tree (gimple_call_fn (stmt.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_gimple_call_get_fndecl (gcc_gimple_call stmt)
{
  return gcc_private_make_tree (gimple_call_fndecl (stmt.inner));
}

GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_gimple_call_is_noreturn (gcc_gimple_call stmt)
{
  return gimple_call_noreturn_p (stmt.inner);
}

GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_gimple_call_for_each_arg (gcc_gimple_call stmt,
			      bool (*cb) (gcc_tree node, void *user_data),
			      void *user_data)
{
  int num_args = gimple_call_num_args (stmt.inner);
  int i;

  for (i = 0; i < num_args; i++)
    {
      if (cb (gcc_private_make_tree (gimple_call_arg (stmt.inner, i)),
	      user_data))
	{
	  return true;
	}
    }
  return false;
}

/***************************************************************************
 gcc_gimple_return
 **************************************************************************/
  GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_gimple_return_get_retval (gcc_gimple_return stmt)
{
  return gcc_private_make_tree (gimple_return_retval (stmt.inner));
}

/***************************************************************************
 gcc_gimple_cond
 **************************************************************************/
  GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_gimple_cond_get_lhs (gcc_gimple_cond stmt)
{
  return gcc_private_make_tree (gimple_cond_lhs (stmt.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_gimple_cond_get_rhs (gcc_gimple_cond stmt)
{
  return gcc_private_make_tree (gimple_cond_rhs (stmt.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_gimple_cond_get_true_label (gcc_gimple_cond stmt)
{
  return gcc_private_make_tree (gimple_cond_true_label (stmt.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_gimple_cond_get_false_label (gcc_gimple_cond stmt)
{
  return gcc_private_make_tree (gimple_cond_false_label (stmt.inner));
}

/***************************************************************************
 gcc_gimple_phi
 **************************************************************************/
  GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_gimple_phi_get_lhs (gcc_gimple_phi phi)
{
  return gcc_private_make_tree (gimple_phi_result (phi.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_gimple_phi_get_result (gcc_gimple_phi phi)
{
  return gcc_private_make_tree (gimple_phi_result (phi.inner));
}

/*
  Iterator; terminates if the callback returns truth
  (for linear search)
*/
GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_gimple_phi_for_each_exprs (gcc_gimple_phi phi,
			       bool (*cb) (gcc_tree node, void *user_data),
			       void *user_data);

/*
  Iterator; terminates if the callback returns truth
  (for linear search)
*/
GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_gimple_phi_for_each_edges (gcc_gimple_phi phi,
			       bool (*cb) (gcc_cfg_edge edge,
					   void *user_data), void *user_data);

/***************************************************************************
 gcc_gimple_switch
 **************************************************************************/
  GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_gimple_switch_get_indexvar (gcc_gimple_switch stmt)
{
  return gcc_private_make_tree (gimple_switch_index (stmt.inner));
}

GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_gimple_switch_for_each_label (gcc_gimple_switch stmt,
				  bool (*cb) (gcc_case_label_expr node,
					      void *user_data),
				  void *user_data)
{
  unsigned num_labels = gimple_switch_num_labels (stmt.inner);
  unsigned i;

  for (i = 0; i < num_labels; i++)
    {
      if (cb
	  (gcc_private_make_case_label_expr
	   (gimple_switch_label (stmt.inner, i)), user_data))
	{
	  return true;
	}
    }
  return false;
}

/***************************************************************************
 gcc_gimple_label
 **************************************************************************/
GCC_IMPLEMENT_PUBLIC_API(gcc_label_decl)
gcc_gimple_label_get_label(gcc_gimple_label stmt)
{
  return gcc_tree_as_gcc_label_decl (gcc_private_make_tree (gimple_label_label (stmt.inner)));
}

/*
Local variables:
c-basic-offset: 2
indent-tabs-mode: nil
End:
*/
