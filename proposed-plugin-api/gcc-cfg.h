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

#include "proposed-plugin-api/gcc-common.h"

/* Declarations: control flow graphs */

/* GccCfgI */
GCC_PUBLIC_API(void)
GccCfgI_MarkInUse(GccCfgI cfg);

GCC_PUBLIC_API(GccCfgBlockI)
GccCfgI_GetEntry(GccCfgI cfg);

GCC_PUBLIC_API(GccCfgBlockI)
GccCfgI_GetExit(GccCfgI cfg);

GCC_PUBLIC_API(bool)
GccCfgI_ForEachBlock(GccCfgI cfg,
                     bool (*cb)(GccCfgBlockI block, void *user_data),
                     void *user_data);

/* GccCfgBlockI: */
GCC_PUBLIC_API(void)
GccCfgBlockI_MarkInUse(GccCfgBlockI block);

GCC_PUBLIC_API(int)
GccCfgBlockI_GetIndex(GccCfgBlockI block);

/* Iterate over predecessor edges; terminate if the callback returns truth
   (for linear search) */
GCC_PUBLIC_API(bool)
GccCfgBlockI_ForEachPredEdge(GccCfgBlockI block,
                             bool (*cb)(GccCfgEdgeI edge, void *user_data),
                             void *user_data);

/* Same, but for successor edges */
GCC_PUBLIC_API(bool)
GccCfgBlockI_ForEachSuccEdge(GccCfgBlockI block,
                             bool (*cb)(GccCfgEdgeI edge, void *user_data),
                             void *user_data);

/*
  Iterate over phi nodes (if any); terminate if the callback returns truth
  (for linear search).
  These will only exist at a certain phase of the compilation
*/
GCC_PUBLIC_API(bool)
GccCfgBlockI_ForEachPhiNode(GccCfgBlockI block,
                            bool (*cb)(GccGimplePhiI phi, void *user_data),
                            void *user_data);

/*
  Iterate over GIMPLE statements (if any); terminate if the callback returns
  truth (for linear search)
  These will only exist at a certain phase of the compilation
*/
GCC_PUBLIC_API(bool)
GccCfgBlockI_ForEachGimple(GccCfgBlockI block,
                           bool (*cb)(GccGimpleI stmt, void *user_data),
                           void *user_data);

/*
  Iterate over RTL instructions (if any); terminate if the callback returns
  truth (for linear search)
  These will only exist at a certain phase of the compilation
*/
GCC_PUBLIC_API(bool)
GccCfgBlockI_ForEachRtlInsn(GccCfgBlockI block,
                            bool (*cb)(GccRtlInsnI insn, void *user_data),
                            void *user_data);

/* GccCfgEdgeI: */
GCC_PUBLIC_API(GccCfgBlockI)
GccCfgEdgeI_GetSrc(GccCfgEdgeI edge);

GCC_PUBLIC_API(GccCfgBlockI)
GccCfgEdgeI_GetDest(GccCfgEdgeI edge);

/* If you store a (gcc_cfg_edge*), you are explicitly responsible for calling
   this during the "mark" phase of GCC's garbage collector */
GCC_PUBLIC_API(void)
GccCfgEdgeI_MarkInUse(GccCfgEdgeI edge);

/*
    for flag in ('EDGE_FALLTHRU', 'EDGE_ABNORMAL', 'EDGE_ABNORMAL_CALL',
                 'EDGE_EH', 'EDGE_FAKE', 'EDGE_DFS_BACK', 'EDGE_CAN_FALLTHRU',
                 'EDGE_IRREDUCIBLE_LOOP', 'EDGE_SIBCALL', 'EDGE_LOOP_EXIT',
                 'EDGE_TRUE_VALUE', 'EDGE_FALSE_VALUE', 'EDGE_EXECUTABLE',
                 'EDGE_CROSSING'):
*/
GCC_PUBLIC_API(bool)
GccCfgEdgeI_IsFallthru(GccCfgEdgeI edge);
/* etc */

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
