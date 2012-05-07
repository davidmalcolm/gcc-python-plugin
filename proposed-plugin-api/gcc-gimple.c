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

#include "proposed-plugin-api/gcc-gimple.h"

//#include "tree.h"
#include "gimple.h"
#if 0
#include "params.h"
#include "cp/name-lookup.h" /* for global_namespace */
#include "tree.h"
#include "function.h"
#include "diagnostic.h"
#include "cgraph.h"
#include "opts.h"
#include "c-family/c-pragma.h" /* for parse_in */
#include "basic-block.h"
#include "rtl.h"
#endif

#include <gcc-plugin.h>

GCC_IMPLEMENT_PUBLIC_API(void)
gcc_gimple_mark_in_use(gcc_gimple stmt)
{
    /* Mark the underlying object (recursing into its fields): */
    gt_ggc_mx_gimple_statement_d(stmt.inner);
}

GCC_IMPLEMENT_PRIVATE_API(struct gcc_gimple_phi)
gcc_private_make_gimple_phi(gimple inner)
{
    struct gcc_gimple_phi result;
    /* FIXME: type-checking */
    result.inner = inner;
    return result;
}

GCC_IMPLEMENT_PRIVATE_API(struct gcc_gimple_call)
gcc_private_make_gimple_call(gimple inner)
{
    struct gcc_gimple_call result;
    /* FIXME: type-checking */
    result.inner = inner;
    return result;
}


GCC_IMPLEMENT_PRIVATE_API(struct gcc_gimple)
gcc_private_make_gimple(gimple inner)
{
    struct gcc_gimple result;
    result.inner = inner;
    return result;
}

GCC_IMPLEMENT_PUBLIC_API(gcc_location)
gcc_gimple_get_location(gcc_gimple stmt)
{
    return gcc_private_make_location(gimple_location(stmt.inner));
}

GCC_IMPLEMENT_PUBLIC_API(gcc_gimple)
gcc_gimple_phi_upcast(gcc_gimple_phi phi)
{
    return gcc_private_make_gimple(phi.inner);
}

GCC_IMPLEMENT_PUBLIC_API(gcc_gimple)
gcc_gimple_call_upcast(gcc_gimple_call call)
{
    return gcc_private_make_gimple(call.inner);
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
