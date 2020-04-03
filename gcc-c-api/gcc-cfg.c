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

#include "gcc-cfg.h"

#include "tree.h"
#include "function.h"
#include "basic-block.h"

#if (GCC_VERSION >= 4009)
#include "tree-ssa-alias.h" /* needed by gimple.h in 4.9 */
#include "internal-fn.h" /* needed by gimple.h in 4.9 */
#include "is-a.h" /* needed by gimple.h in 4.9 */
#include "predict.h" /* needed by gimple.h in 4.9 */
#include "gimple-expr.h" /* needed by gimple.h in 4.9 */
#endif
#include "gimple.h"

/* gcc 4.9 moved gimple_stmt_iterator into this header */
#if (GCC_VERSION >= 4009)
#include "gimple-iterator.h"
#endif

/* gcc 10 removed this header */
#if (GCC_VERSION < 10000)
#include "params.h"
#endif

#include "tree.h"
#include "diagnostic.h"
#include "cgraph.h"
#include "opts.h"
#include "rtl.h"

#include "gcc-private-compat.h"

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
      basic_block bb = GCC_COMPAT_VEC_INDEX (basic_block,
                                             cfg.inner->x_basic_block_info,
                                             i);
      if (cb (gcc_private_make_cfg_block (bb), user_data))
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
for_each_edge (
#if (GCC_VERSION >= 4008)
               vec<edge, va_gc> *vec_edges,
#else
               VEC (edge, gc) * vec_edges,
#endif
	       bool (*cb) (gcc_cfg_edge edge, void *user_data),
	       void *user_data)
{
  int i;
  edge e;

  GCC_COMPAT_FOR_EACH_VEC_ELT (edge, vec_edges, i, e)
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

/* In GCC 4.7, struct basic_block_def had a
     struct gimple_bb_info * gimple;
   within its il union.

   In GCC 4.8, this became:
     struct gimple_bb_info gimple
   i.e. it is no longer dereferenced
*/
static struct gimple_bb_info *
checked_get_gimple_info(gcc_cfg_block block)
{
  if (block.inner->flags & BB_RTL)
    {
      return NULL;
    }

#if (GCC_VERSION >= 4008)
  return &block.inner->il.gimple;
#else
  return block.inner->il.gimple;
#endif
}


GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_cfg_block_for_each_gimple_phi (gcc_cfg_block block,
				   bool (*cb) (gcc_gimple_phi phi,
					       void *user_data),
				   void *user_data)
{
  gimple_stmt_iterator gsi;
  struct gimple_bb_info *info;

  info = checked_get_gimple_info(block);

  if (NULL == info)
    {
      return false;
    }

  for (gsi = gsi_start (info->phi_nodes);
       !gsi_end_p (gsi); gsi_next (&gsi))
    {

      gimple_stmt_ptr stmt = gsi_stmt (gsi);
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
  struct gimple_bb_info *info;

  info = checked_get_gimple_info(block);

  if (NULL == info)
    {
      return false;
    }

  for (gsi = gsi_start (info->seq);
       !gsi_end_p (gsi); gsi_next (&gsi))
    {

      gimple_stmt_ptr stmt = gsi_stmt (gsi);
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
#if (GCC_VERSION >= 5000)
  rtx_insn *insn;
#else
  rtx insn;
#endif

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

GCC_PUBLIC_API(bool)
gcc_cfg_edge_is_loop_exit(gcc_cfg_edge edge)
{
  return (edge.inner->flags & EDGE_LOOP_EXIT) == EDGE_LOOP_EXIT;
}

GCC_PUBLIC_API(bool)
gcc_cfg_edge_get_can_fallthru(gcc_cfg_edge edge)
{
  return (edge.inner->flags & EDGE_CAN_FALLTHRU) == EDGE_CAN_FALLTHRU;
}

GCC_PUBLIC_API(bool)
gcc_cfg_edge_is_complex(gcc_cfg_edge edge)
{
  return (edge.inner->flags & EDGE_COMPLEX);
}

GCC_PUBLIC_API(bool)
gcc_cfg_edge_is_eh(gcc_cfg_edge edge)
{
  return (edge.inner->flags & EDGE_EH) == EDGE_EH;
}


/*
Local variables:
c-basic-offset: 2
indent-tabs-mode: nil
End:
*/
