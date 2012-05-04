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
#include "proposed-plugin-api/gcc-semiprivate-types.h"
#include "tree.h"

GCC_IMPLEMENT_PRIVATE_API(struct gcc_function_decl)
gcc_private_make_function_decl(tree inner)
{
    struct gcc_function_decl result;
    result.inner = inner;
    return result;
}

GCC_IMPLEMENT_PUBLIC_API(gcc_location)
gcc_decl_get_location(gcc_decl decl)
{
    return gcc_private_make_location(DECL_SOURCE_LOCATION(decl.inner));
}

GCC_IMPLEMENT_PUBLIC_API(gcc_tree)
gcc_decl_upcast(gcc_decl decl)
{
    gcc_tree tree;
    tree.inner = decl.inner;
    return tree;
}

GCC_IMPLEMENT_PUBLIC_API(gcc_decl)
gcc_function_decl_upcast(gcc_function_decl fndecl)
{
    gcc_decl decl;
    decl.inner = fndecl.inner;
    return decl;
}


/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
