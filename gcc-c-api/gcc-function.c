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

#include "gcc-c-api/gcc-common.h"

/* TODO: rationalize these headers */
#include "tree.h"
#include "gimple.h"
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

/* Declarations: functions */

/* gcc_function */
GCC_IMPLEMENT_PUBLIC_API(void)
gcc_function_mark_in_use(gcc_function func)
{
    gt_ggc_mx_function(func.inner);
}

GCC_IMPLEMENT_PRIVATE_API(struct gcc_function)
gcc_private_make_function(struct function *inner)
{
    struct gcc_function result;
    result.inner = inner;
    return result;
}

GCC_IMPLEMENT_PUBLIC_API(gcc_cfg)
gcc_function_get_cfg(gcc_function func)
{
    return gcc_private_make_cfg(func.inner->cfg);
}

GCC_IMPLEMENT_PUBLIC_API(gcc_function_decl)
gcc_function_get_decl(gcc_function func)
{
    return gcc_private_make_function_decl(func.inner->decl);
}

GCC_IMPLEMENT_PUBLIC_API(int)
gcc_function_get_index(gcc_function func)
{
    return func.inner->funcdef_no;
}

GCC_IMPLEMENT_PUBLIC_API(gcc_location)
gcc_function_get_start(gcc_function func)
{
    return gcc_private_make_location(func.inner->function_start_locus);
}

GCC_IMPLEMENT_PUBLIC_API(gcc_location)
gcc_function_get_end(gcc_function func)
{
    return gcc_private_make_location(func.inner->function_end_locus);
}

GCC_IMPLEMENT_PUBLIC_API(gcc_function)
gcc_get_current_function(void)
{
    return gcc_private_make_function(cfun);
}


/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
