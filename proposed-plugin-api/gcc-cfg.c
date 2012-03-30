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

#include "proposed-plugin-api/gcc-cfg.h"

#include "tree.h"
#include "gimple.h"
#include "params.h"
#include "cp/name-lookup.h" /* for global_namespace */
#include "tree.h"
#include "function.h"
#include "diagnostic.h"
#include "cgraph.h"
#include "opts.h"
#include "c-family/c-pragma.h" /* for parse_in */
#include "basic-block.h"
#include "rtl.h"

/***********************************************************
   GccCfgI
************************************************************/
GCC_IMPLEMENT_PRIVATE_API(struct GccCfgI)
GccPrivate_make_CfgI(struct control_flow_graph *inner)
{
    struct GccCfgI result;
    result.inner = inner;
    return result;
}

GCC_IMPLEMENT_PUBLIC_API(void)
GccCfgI_MarkInUse(GccCfgI cfg)
{
    gt_ggc_mx_control_flow_graph(cfg.inner);
}

GCC_IMPLEMENT_PUBLIC_API(GccCfgBlockI)
GccCfgI_GetEntry(GccCfgI cfg)
{
    return GccPrivate_make_CfgBlockI(cfg.inner->x_entry_block_ptr);
}

GCC_IMPLEMENT_PUBLIC_API(GccCfgBlockI)
GccCfgI_GetExit(GccCfgI cfg)
{
    return GccPrivate_make_CfgBlockI(cfg.inner->x_exit_block_ptr);
}

GCC_IMPLEMENT_PUBLIC_API(bool)
GccCfgI_ForEachBlock(GccCfgI cfg,
                     bool (*cb)(GccCfgBlockI block, void *user_data),
                     void *user_data);

/***********************************************************
  GccCfgBlockI
************************************************************/
GCC_IMPLEMENT_PRIVATE_API(struct GccCfgBlockI)
GccPrivate_make_CfgBlockI(basic_block inner)
{
    struct GccCfgBlockI result;
    result.inner = inner;
    return result;
}

GCC_IMPLEMENT_PUBLIC_API(void)
GccCfgBlockI_MarkInUse(GccCfgBlockI block)
{
    gt_ggc_mx_basic_block_def(block.inner);
}

GCC_IMPLEMENT_PUBLIC_API(int)
GccCfgBlockI_GetIndex(GccCfgBlockI block)
{
    return block.inner->index;
}

static bool
for_each_edge(VEC(edge,gc) *vec_edges,
              bool (*cb)(GccCfgEdgeI edge, void *user_data),
              void *user_data)
{
    int i;
    edge e;

    FOR_EACH_VEC_ELT(edge, vec_edges, i, e) {
        if (cb(GccPrivate_make_CfgEdgeI(e),
               user_data)) {
            return true;
        }
    }

    return false;
}

GCC_IMPLEMENT_PUBLIC_API(bool)
GccCfgBlockI_ForEachPredEdge(GccCfgBlockI block,
                             bool (*cb)(GccCfgEdgeI edge, void *user_data),
                             void *user_data)
{
    return for_each_edge(block.inner->preds, cb, user_data);
}

GCC_IMPLEMENT_PUBLIC_API(bool)
GccCfgBlockI_ForEachSuccEdge(GccCfgBlockI block,
                             bool (*cb)(GccCfgEdgeI edge, void *user_data),
                             void *user_data)
{
    return for_each_edge(block.inner->succs, cb, user_data);
}


GCC_IMPLEMENT_PUBLIC_API(bool)
GccCfgBlockI_ForEachGimplePhi(GccCfgBlockI block,
                              bool (*cb)(GccGimplePhiI phi, void *user_data),
                              void *user_data)
{
    gimple_stmt_iterator gsi;

    if (block.inner->flags & BB_RTL) {
        return false;
    }

    if (NULL == block.inner->il.gimple) {
        return false;
    }

    for (gsi = gsi_start(block.inner->il.gimple->seq);
	 !gsi_end_p(gsi);
	 gsi_next(&gsi)) {

	gimple stmt = gsi_stmt(gsi);
        if (cb(GccPrivate_make_GimplePhiI(stmt),
               user_data)) {
            return true;
        }
    }

    return false;
}

GCC_IMPLEMENT_PUBLIC_API(bool)
GccCfgBlockI_ForEachGimple(GccCfgBlockI block,
                           bool (*cb)(GccGimpleI stmt, void *user_data),
                           void *user_data)
{
    gimple_stmt_iterator gsi;

    if (block.inner->flags & BB_RTL) {
        return false;
    }

    if (NULL == block.inner->il.gimple) {
        return false;
    }

    for (gsi = gsi_start(block.inner->il.gimple->seq);
	 !gsi_end_p(gsi);
	 gsi_next(&gsi)) {

	gimple stmt = gsi_stmt(gsi);
        if (cb(GccPrivate_make_GimpleI(stmt),
               user_data)) {
            return true;
        }
    }

    return false;
}

GCC_IMPLEMENT_PUBLIC_API(bool)
GccCfgBlockI_ForEachRtlInsn(GccCfgBlockI block,
                            bool (*cb)(GccRtlInsnI insn, void *user_data),
                            void *user_data)
{
    rtx insn;

    if (!(block.inner->flags & BB_RTL)) {
        return false;
    }

    FOR_BB_INSNS(block.inner, insn) {
        if (cb(GccPrivate_make_RtlInsnI(insn),
               user_data)) {
            return true;
        }
    }

    return false;
}

/***********************************************************
   GccCfgEdgeI
************************************************************/
GCC_IMPLEMENT_PRIVATE_API(struct GccCfgEdgeI)
GccPrivate_make_CfgEdgeI(edge inner)
{
    struct GccCfgEdgeI result;
    result.inner = inner;
    return result;
}

GCC_IMPLEMENT_PUBLIC_API(void)
GccCfgEdgeI_MarkInUse(GccCfgEdgeI edge)
{
    gt_ggc_mx_edge_def(edge.inner);
}

GCC_IMPLEMENT_PUBLIC_API(GccCfgBlockI)
GccCfgEdgeI_GetSrc(GccCfgEdgeI edge)
{
    return GccPrivate_make_CfgBlockI(edge.inner->src);
}

GCC_IMPLEMENT_PUBLIC_API(GccCfgBlockI)
GccCfgEdgeI_GetDest(GccCfgEdgeI edge)
{
    return GccPrivate_make_CfgBlockI(edge.inner->dest);
}

GCC_PUBLIC_API(bool)
GccCfgEdgeI_IsTrueValue(GccCfgEdgeI edge)
{
    return (edge.inner->flags & EDGE_TRUE_VALUE) == EDGE_TRUE_VALUE;
}

GCC_PUBLIC_API(bool)
GccCfgEdgeI_IsFalseValue(GccCfgEdgeI edge)
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
