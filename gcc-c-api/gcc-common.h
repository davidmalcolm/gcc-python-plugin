/*
   Copyright 2012, 2015 David Malcolm <dmalcolm@redhat.com>
   Copyright 2012, 2015 Red Hat, Inc.

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

#include <gcc-plugin.h>

/* see design.rst for notes */

/* Compatibility macros */

/* For declarations: */
#define GCC_PUBLIC_API(RETURN_TYPE) extern RETURN_TYPE
#define GCC_PRIVATE_API(RETURN_TYPE) extern RETURN_TYPE

#include "gcc-public-types.h"

/* For internal use: */
#define GCC_IMPLEMENT_PUBLIC_API(RETURN_TYPE) RETURN_TYPE
#define GCC_IMPLEMENT_PRIVATE_API(RETURN_TYPE) RETURN_TYPE

#if (GCC_VERSION >= 5000)
#define AS_A_GASM(STMT) (as_a <gasm *> (STMT))
#define AS_A_GCOND(STMT) (as_a <gcond *> (STMT))
#define AS_A_GLABEL(STMT) (as_a <glabel *> (STMT))
#define AS_A_GPHI(STMT) (as_a <gphi *> (STMT))
#define AS_A_GSWITCH(STMT) (as_a <gswitch *> (STMT))
#define AS_A_GRETURN(STMT) (as_a <greturn *> (STMT))
#else
#define AS_A_GASM(STMT) (STMT)
#define AS_A_GCOND(STMT) (STMT)
#define AS_A_GLABEL(STMT) (STMT)
#define AS_A_GPHI(STMT) (STMT)
#define AS_A_GSWITCH(STMT) (STMT)
#define AS_A_GRETURN(STMT) (STMT)
#endif
