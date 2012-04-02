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

/* Gimple statements (generic) */
GCC_PUBLIC_API(void)
gcc_gimple_mark_in_use(gcc_gimple stmt);

GCC_PUBLIC_API(void)
gcc_gimple_print(gcc_gimple stmt,
                 gcc_printer printer,
                 int spc,  /* FIXME: meaning of spc! */
                 int flags); /* FIXME: meaning of flags! */

#if 0
GCC_PUBLIC_API(bool)
gcc_gimple_walk_tree(gcc_gimple stmt,);
#endif               


/* Subclasses of gimple */

/* Gimple phi nodes */
GCC_PUBLIC_API(gcc_gimple)
gcc_gimple_phi_upcast(gcc_gimple_phi phi);
