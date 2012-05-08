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
#include "proposed-plugin-api/gcc-type.h"
#include "proposed-plugin-api/gcc-constant.h"
#include "proposed-plugin-api/gcc-tree.h"
#include "tree.h"

/*
  Types
*/

/* gcc_integer_type */
GCC_IMPLEMENT_PRIVATE_API(gcc_integer_constant)
gcc_private_make_integer_constant(tree inner)
{
    gcc_integer_constant result;
    result.inner = INTEGER_CST_CHECK(inner);
    return result;
}

GCC_IMPLEMENT_PUBLIC_API(gcc_integer_constant)
gcc_integer_type_get_max_value(gcc_integer_type node)
{
    return gcc_private_make_integer_constant(TYPE_MAX_VALUE(node.inner));
}

GCC_IMPLEMENT_PUBLIC_API(gcc_integer_constant)
gcc_integer_type_get_min_value(gcc_integer_type node)
{
    return gcc_private_make_integer_constant(TYPE_MIN_VALUE(node.inner));
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
