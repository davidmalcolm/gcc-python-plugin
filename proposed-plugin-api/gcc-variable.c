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

#include "proposed-plugin-api/gcc-variable.h"
#include "ggc.h"
#include "cgraph.h" /* for varpool_nodes */

/***********************************************************
   gcc_variable
************************************************************/
GCC_IMPLEMENT_PRIVATE_API(struct gcc_variable)
gcc_private_make_variable(struct varpool_node * inner)
{
    struct gcc_variable result;
    result.inner = inner;
    return result;
}

GCC_IMPLEMENT_PUBLIC_API(void)
gcc_variable_mark_in_use(gcc_variable var)
{
    /* Mark the underlying object (recursing into its fields): */
    gt_ggc_mx_varpool_node(var.inner);
}

GCC_IMPLEMENT_PUBLIC_API(gcc_tree)
gcc_variable_get_decl(gcc_variable var)
{
    return gcc_private_make_tree(var.inner->decl);
}

GCC_IMPLEMENT_PUBLIC_API(bool)
gcc_for_each_variable(bool (*cb)(gcc_variable var, void *user_data),
                      void *user_data)
{
    struct varpool_node *n;

    for (n = varpool_nodes; n; n = n->next) {
        if (cb(gcc_private_make_variable(n), user_data)) {
            return true;
        }
    }
    return false;
}


/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
