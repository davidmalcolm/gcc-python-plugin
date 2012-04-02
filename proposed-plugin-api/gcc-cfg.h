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

/* gcc_cfg */
GCC_PUBLIC_API(void)
gcc_cfg_mark_in_use(gcc_cfg cfg);

GCC_PUBLIC_API(gcc_cfg_block)
gcc_cfg_get_entry(gcc_cfg cfg);

GCC_PUBLIC_API(gcc_cfg_block)
gcc_cfg_get_exit(gcc_cfg cfg);

GCC_PUBLIC_API(bool)
gcc_cfg_for_each_block(gcc_cfg cfg,
                       bool (*cb)(gcc_cfg_block block, void *user_data),
                       void *user_data);

/* gcc_cfg_block: */
GCC_PUBLIC_API(void)
gcc_cfg_block_mark_in_use(gcc_cfg_block block);

GCC_PUBLIC_API(int)
gcc_cfg_block_get_index(gcc_cfg_block block);

/* Iterate over predecessor edges; terminate if the callback returns truth
   (for linear search) */
GCC_PUBLIC_API(bool)
gcc_cfg_block_for_each_pred_edge(gcc_cfg_block block,
                                 bool (*cb)(gcc_cfg_edge edge, void *user_data),
                                 void *user_data);

/* Same, but for successor edges */
GCC_PUBLIC_API(bool)
gcc_cfg_block_for_each_succ_edge(gcc_cfg_block block,
                                 bool (*cb)(gcc_cfg_edge edge, void *user_data),
                                 void *user_data);

/*
  Iterate over phi nodes (if any); terminate if the callback returns truth
  (for linear search).
  These will only exist at a certain phase of the compilation
*/
GCC_PUBLIC_API(bool)
gcc_cfg_block_for_each_gimple_phi(gcc_cfg_block block,
                                  bool (*cb)(gcc_gimple_phi phi, void *user_data),
                                  void *user_data);

/*
  Iterate over non-phi GIMPLE statements (if any); terminate if the callback
  returns truth (for linear search)
  These will only exist at a certain phase of the compilation
*/
GCC_PUBLIC_API(bool)
gcc_cfg_block_for_each_gimple(gcc_cfg_block block,
                              bool (*cb)(gcc_gimple stmt, void *user_data),
                              void *user_data);

/*
  Iterate over RTL instructions (if any); terminate if the callback returns
  truth (for linear search)
  These will only exist at a certain phase of the compilation
*/
GCC_PUBLIC_API(bool)
gcc_cfg_block_for_each_rtl_insn(gcc_cfg_block block,
                                bool (*cb)(gcc_rtl_insn insn, void *user_data),
                                void *user_data);

/* gcc_cfg_edge: */
GCC_PUBLIC_API(void)
gcc_cfg_edge_mark_in_use(gcc_cfg_edge edge);

GCC_PUBLIC_API(gcc_cfg_block)
gcc_cfg_edge_get_src(gcc_cfg_edge edge);

GCC_PUBLIC_API(gcc_cfg_block)
gcc_cfg_edge_get_dest(gcc_cfg_edge edge);

/* How many of the flags do we want to expose? */
GCC_PUBLIC_API(bool)
gcc_cfg_edge_is_true_value(gcc_cfg_edge edge);

GCC_PUBLIC_API(bool)
gcc_cfg_edge_is_false_value(gcc_cfg_edge edge);

/* etc */

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
