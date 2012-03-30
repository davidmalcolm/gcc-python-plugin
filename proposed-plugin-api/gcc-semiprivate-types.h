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
struct GccCfgI {
  struct control_flow_graph *inner;
};

GCC_PRIVATE_API(struct GccCfgI)
GccPrivate_make_CfgI(struct control_flow_graph *inner);


struct GccCfgBlockI {
  basic_block inner;
};

GCC_PRIVATE_API(struct GccCfgBlockI)
GccPrivate_make_CfgBlockI(basic_block inner);

struct GccCfgEdgeI {
  edge inner;
};

GCC_PRIVATE_API(struct GccCfgEdgeI)
GccPrivate_make_CfgEdgeI(edge inner);


/* Semiprivate types: GIMPLE representation */
struct GccGimplePhiI {
  gimple inner;
};

GCC_PRIVATE_API(struct GccGimplePhiI)
GccPrivate_make_GimplePhiI(gimple inner);

struct GccGimpleI {
  gimple inner;
};

GCC_PRIVATE_API(struct GccGimpleI)
GccPrivate_make_GimpleI(gimple inner);

/* Semiprivate types: RTL representation */
struct GccRtlInsnI {
  struct rtx_def *inner;
};

GCC_PRIVATE_API(struct GccRtlInsnI)
GccPrivate_make_RtlInsnI(struct rtx_def *inner);

/* Semiprivate types: locations */
struct GccLocationI {
  location_t inner;
};

GCC_PRIVATE_API(struct GccLocationI)
GccPrivate_make_LocationI(location_t inner);

/* Semiprivate types: functions */
struct GccFunctionI {
  struct function *inner;
};

GCC_PRIVATE_API(struct GccFunctionI)
GccPrivate_make_FunctionI(struct function *inner);


#endif /* INCLUDED__GCC_SEMIPRIVATE_TYPES_H */
