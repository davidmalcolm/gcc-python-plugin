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

#include "gcc-cfg.h"

#include "tree.h"
#include "gimple.h"
#include "params.h"
#include "cp/name-lookup.h"	/* for global_namespace */
#include "tree.h"
#include "function.h"
#include "diagnostic.h"
#include "cgraph.h"
#include "opts.h"
#include "c-family/c-pragma.h"	/* for parse_in */
#include "basic-block.h"
#include "rtl.h"

/***********************************************************
   gcc_cfg
************************************************************/
GCC_IMPLEMENT_PRIVATE_API (struct gcc_cfg)
gcc_private_make_cfg (struct control_flow_graph *inner)
{
  struct gcc_cfg result;
  result.inner = inner;
  return result;
}

GCC_IMPLEMENT_PUBLIC_API (void) gcc_cfg_mark_in_use (gcc_cfg cfg)
{
  gt_ggc_mx_control_flow_graph (cfg.inner);
}

GCC_IMPLEMENT_PUBLIC_API (gcc_cfg_block) gcc_cfg_get_entry (gcc_cfg cfg)
{
  return gcc_private_make_cfg_block (cfg.inner->x_entry_block_ptr);
}

GCC_IMPLEMENT_PUBLIC_API (gcc_cfg_block) gcc_cfg_get_exit (gcc_cfg cfg)
{
  return gcc_private_make_cfg_block (cfg.inner->x_exit_block_ptr);
}

GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_cfg_for_each_block (gcc_cfg cfg,
			bool (*cb) (gcc_cfg_block block, void *user_data),
			void *user_data)
{
  int i;

  for (i = 0; i < cfg.inner->x_n_basic_blocks; i++)
    {
      if (cb (gcc_private_make_cfg_block (VEC_index (basic_block,
						     cfg.inner->
						     x_basic_block_info, i)),
	      user_data))
	{
	  return true;
	}
    }
  return false;

}

/***********************************************************
  gcc_cfg_block
************************************************************/
GCC_IMPLEMENT_PRIVATE_API (struct gcc_cfg_block)
gcc_private_make_cfg_block (basic_block inner)
{
  struct gcc_cfg_block result;
  result.inner = inner;
  return result;
}

GCC_IMPLEMENT_PUBLIC_API (void)
gcc_cfg_block_mark_in_use (gcc_cfg_block block)
{
  gt_ggc_mx_basic_block_def (block.inner);
}

GCC_IMPLEMENT_PUBLIC_API (int)
gcc_cfg_block_get_index (gcc_cfg_block block)
{
  return block.inner->index;
}

static bool
for_each_edge (VEC (edge, gc) * vec_edges,
	       bool (*cb) (gcc_cfg_edge edge, void *user_data),
	       void *user_data)
{
  int i;
  edge e;

  FOR_EACH_VEC_ELT (edge, vec_edges, i, e)
  {
    if (cb (gcc_private_make_cfg_edge (e), user_data))
      {
	return true;
      }
  }

  return false;
}

GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_cfg_block_for_each_pred_edge (gcc_cfg_block block,
				  bool (*cb) (gcc_cfg_edge edge,
					      void *user_data),
				  void *user_data)
{
  return for_each_edge (block.inner->preds, cb, user_data);
}

GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_cfg_block_for_each_succ_edge (gcc_cfg_block block,
				  bool (*cb) (gcc_cfg_edge edge,
					      void *user_data),
				  void *user_data)
{
  return for_each_edge (block.inner->succs, cb, user_data);
}


GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_cfg_block_for_each_gimple_phi (gcc_cfg_block block,
				   bool (*cb) (gcc_gimple_phi phi,
					       void *user_data),
				   void *user_data)
{
  gimple_stmt_iterator gsi;

  if (block.inner->flags & BB_RTL)
    {
      return false;
    }

  if (NULL == block.inner->il.gimple)
    {
      return false;
    }

  for (gsi = gsi_start (block.inner->il.gimple->seq);
       !gsi_end_p (gsi); gsi_next (&gsi))
    {

      gimple stmt = gsi_stmt (gsi);
      if (cb (gcc_private_make_gimple_phi (stmt), user_data))
	{
	  return true;
	}
    }

  return false;
}

GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_cfg_block_for_each_gimple (gcc_cfg_block block,
			       bool (*cb) (gcc_gimple stmt, void *user_data),
			       void *user_data)
{
  gimple_stmt_iterator gsi;

  if (block.inner->flags & BB_RTL)
    {
      return false;
    }

  if (NULL == block.inner->il.gimple)
    {
      return false;
    }

  for (gsi = gsi_start (block.inner->il.gimple->seq);
       !gsi_end_p (gsi); gsi_next (&gsi))
    {

      gimple stmt = gsi_stmt (gsi);
      if (cb (gcc_private_make_gimple (stmt), user_data))
	{
	  return true;
	}
    }

  return false;
}

GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_cfg_block_for_each_rtl_insn (gcc_cfg_block block,
				 bool (*cb) (gcc_rtl_insn insn,
					     void *user_data),
				 void *user_data)
{
  rtx insn;

  if (!(block.inner->flags & BB_RTL))
    {
      return false;
    }

  FOR_BB_INSNS (block.inner, insn)
  {
    if (cb (gcc_private_make_rtl_insn (insn), user_data))
      {
	return true;
      }
  }

  return false;
}

/***********************************************************
   gcc_cfg_edge
************************************************************/
GCC_IMPLEMENT_PRIVATE_API (struct gcc_cfg_edge)
gcc_private_make_cfg_edge (edge inner)
{
  struct gcc_cfg_edge result;
  result.inner = inner;
  return result;
}

GCC_IMPLEMENT_PUBLIC_API (void) gcc_cfg_edge_mark_in_use (gcc_cfg_edge edge)
{
  gt_ggc_mx_edge_def (edge.inner);
}

GCC_IMPLEMENT_PUBLIC_API (gcc_cfg_block)
gcc_cfg_edge_get_src (gcc_cfg_edge edge)
{
  return gcc_private_make_cfg_block (edge.inner->src);
}

GCC_IMPLEMENT_PUBLIC_API (gcc_cfg_block)
gcc_cfg_edge_get_dest (gcc_cfg_edge edge)
{
  return gcc_private_make_cfg_block (edge.inner->dest);
}

GCC_PUBLIC_API (bool) gcc_cfg_edge_is_true_value (gcc_cfg_edge edge)
{
  return (edge.inner->flags & EDGE_TRUE_VALUE) == EDGE_TRUE_VALUE;
}

GCC_PUBLIC_API (bool) gcc_cfg_edge_is_false_value (gcc_cfg_edge edge)
{
  return (edge.inner->flags & EDGE_FALSE_VALUE) == EDGE_FALSE_VALUE;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
