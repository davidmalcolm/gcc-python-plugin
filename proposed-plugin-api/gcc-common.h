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

