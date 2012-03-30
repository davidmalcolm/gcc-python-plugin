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

/* GccFunctionI */
GCC_IMPLEMENT_PUBLIC_API(void)
GccFunctionI_MarkInUse(GccFunctionI func)
{
    gt_ggc_mx_function(func.inner);
}

GCC_IMPLEMENT_PRIVATE_API(struct GccFunctionI)
GccPrivate_make_FunctionI(struct function *inner)
{
    struct GccFunctionI result;
    result.inner = inner;
    return result;
}

GCC_IMPLEMENT_PUBLIC_API(GccCfgI)
GccFunctionI_GetCfg(GccFunctionI func)
{
    return GccPrivate_make_CfgI(func.inner->cfg);
}

GCC_IMPLEMENT_PUBLIC_API(int)
GccFunctionI_GetIndex(GccFunctionI func)
{
    return func.inner->funcdef_no;
}

GCC_IMPLEMENT_PUBLIC_API(GccLocationI)
GccFunctionI_GetStart(GccFunctionI func)
{
    return GccPrivate_make_LocationI(func.inner->function_start_locus);
}

GCC_IMPLEMENT_PUBLIC_API(GccLocationI)
GccFunctionI_GetEnd(GccFunctionI func)
{
    return GccPrivate_make_LocationI(func.inner->function_end_locus);
}

GCC_IMPLEMENT_PUBLIC_API(GccFunctionI)
Gcc_GetCurrentFunction(void)
{
    return GccPrivate_make_FunctionI(cfun);
}


/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
