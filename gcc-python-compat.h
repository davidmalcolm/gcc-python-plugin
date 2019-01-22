/*
   Copyright 2011, 2012, 2014 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011, 2012, 2014 Red Hat, Inc.

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

#if GCC_VERSION < 8000
typedef int dump_flags_t;
#endif

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
dump_gimple_stmt (pretty_printer *buffer, gimple gs, int spc, dump_flags_t flags);

/*
   This is declared in gcc/tree-pretty-print.c (around line 580); it was only
   exposed to plugin headers (in tree-pretty-print.h) in GCC commit r203113
   (aka 0d9585ca35b919263b973afb371f0eda04857159, 2013-10-02), as part of
   GCC 4.9

   The signature was changed by GCC 8 commit r248140 (aka
   3f6e5ced7eb1cf5b3212b2391c5b70ec3dcaf136, 2017-05-17), which introduced
   dump_flags_t.
 */
#if GCC_VERSION < 4009
extern int
dump_generic_node (pretty_printer *buffer, tree node, int spc, dump_flags_t flags,
		   bool is_stmt);
#endif

/* Within gcc/gcc-internal.h, not exposed by plugin API */
extern bool ggc_force_collect;

/* From c-family/c-common.h */
#if GCC_VERSION < 4008
extern tree c_sizeof_or_alignof_type (location_t, tree, bool, int);
#endif


/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/

#endif /* INCLUDED__GCC_PYTHON_COMPAT_H */
