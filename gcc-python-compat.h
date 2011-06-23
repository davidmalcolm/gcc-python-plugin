/*
   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011 Red Hat, Inc.

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

#ifndef INCLUDED__GCC_PYTHON_COMPAT_H
#define INCLUDED__GCC_PYTHON_COMPAT_H

#include "gimple.h"
#include "tree.h"

/*
  There are a few GCC symbols that don't seem to be exposed in the plugin
  headers, but I wish were.

  We manually repeated the necessary declarations here.

  This is wrong, but at least it's all captured here in one place.  Hopefully
  these will eventually become officially exposed to plugins, but for now its
  all here.
*/

/*
   This is declared in gcc/gimple-pretty-print.c, but not exposed in any of
   the plugin headers AFAIK:
*/
extern void
dump_gimple_stmt (pretty_printer *buffer, gimple gs, int spc, int flags);


/*
   This is declated in gcc/tree-pretty-print.c (around line 580); it doesn't
   seem to be declared in any of the plugin headers:
 */
extern int
dump_generic_node (pretty_printer *buffer, tree node, int spc, int flags,
		   bool is_stmt);


/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/

#endif /* INCLUDED__GCC_PYTHON_COMPAT_H */
