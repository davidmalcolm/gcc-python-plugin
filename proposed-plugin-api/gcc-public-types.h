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

#ifndef INCLUDED__GCC_PUBLIC_TYPES_H
#define INCLUDED__GCC_PUBLIC_TYPES_H

#include "gcc-semiprivate-types.h"

/* Opaque types: control flow graphs */
typedef struct gcc_cfg gcc_cfg;
typedef struct gcc_cfg_block gcc_cfg_block;
typedef struct gcc_cfg_edge gcc_cfg_edge;

/* Opaque types: GIMPLE representation */
typedef struct gcc_gimple_phi gcc_gimple_phi;
typedef struct gcc_gimple gcc_gimple;

/* Opaque types: RTL representation */
typedef struct gcc_rtl_insn gcc_rtl_insn;

/* Opaque types: pretty-printing */
typedef struct gcc_printer gcc_printer;

/* Opaque types: locations */
typedef struct gcc_location gcc_location;

/* Opaque types: functions */
typedef struct gcc_function gcc_function;

#endif /* INCLUDED__GCC_PUBLIC_TYPES_H */
