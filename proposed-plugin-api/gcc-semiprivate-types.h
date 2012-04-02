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

#ifndef INCLUDED__GCC_SEMIPRIVATE_TYPES_H
#define INCLUDED__GCC_SEMIPRIVATE_TYPES_H

#include "input.h" /* for location_t */

/*
  These "interface types" should be treated like pointers, only that
  users are required to collaborate with the garbage-collector.

  The internal details are exposed here so that the debugger is able to
  identify the real types.  Plugin developers should *not* rely on the
  internal implementation details.

  By being structs, the compiler will be able to complain if plugin code
  directly pokes at a pointer.
*/

/* Semiprivate types: control flow graphs */
struct gcc_cfg {
  struct control_flow_graph *inner;
};

GCC_PRIVATE_API(struct gcc_cfg)
gcc_private_make_cfg(struct control_flow_graph *inner);


struct gcc_cfg_block {
  basic_block inner;
};

GCC_PRIVATE_API(struct gcc_cfg_block)
gcc_private_make_cfg_block(basic_block inner);

struct gcc_cfg_edge {
  edge inner;
};

GCC_PRIVATE_API(struct gcc_cfg_edge)
gcc_private_make_cfg_edge(edge inner);


/* Semiprivate types: GIMPLE representation */
struct gcc_gimple_phi {
  gimple inner;
};

GCC_PRIVATE_API(struct gcc_gimple_phi)
gcc_private_make_gimple_phi(gimple inner);

struct gcc_gimple {
  gimple inner;
};

GCC_PRIVATE_API(struct gcc_gimple)
gcc_private_make_gimple(gimple inner);

/* Semiprivate types: RTL representation */
struct gcc_rtl_insn {
  struct rtx_def *inner;
};

GCC_PRIVATE_API(struct gcc_rtl_insn)
gcc_private_make_rtl_insn(struct rtx_def *inner);

/* Semiprivate types: locations */
struct gcc_location {
  location_t inner;
};

GCC_PRIVATE_API(struct gcc_location)
gcc_private_make_location(location_t inner);

/* Semiprivate types: functions */
struct gcc_function {
  struct function *inner;
};

GCC_PRIVATE_API(struct gcc_function)
gcc_private_make_function(struct function *inner);


#endif /* INCLUDED__GCC_SEMIPRIVATE_TYPES_H */
