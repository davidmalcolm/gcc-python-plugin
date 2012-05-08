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
#include "gcc-internal.h"

GCC_IMPLEMENT_PRIVATE_API(struct gcc_function_decl)
gcc_private_make_function_decl(tree inner)
{
    struct gcc_function_decl result;
    result.inner = inner;
    return result;
}

GCC_PRIVATE_API(struct gcc_translation_unit_decl)
gcc_private_make_translation_unit_decl(tree inner)
{
    struct gcc_translation_unit_decl result;
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

GCC_IMPLEMENT_PUBLIC_API(gcc_decl)
gcc_translation_unit_decl_upcast(gcc_translation_unit_decl fndecl)
{
    gcc_decl decl;
    decl.inner = fndecl.inner;
    return decl;
}

IMPLEMENT_DOWNCAST(gcc_decl, gcc_translation_unit_decl)

GCC_IMPLEMENT_PUBLIC_API(gcc_block)
gcc_translation_unit_decl_get_block(gcc_translation_unit_decl node)
{
    return gcc_private_make_block(DECL_INITIAL(node.inner));
}

GCC_IMPLEMENT_PUBLIC_API(const char*)
gcc_translation_unit_decl_get_language(gcc_translation_unit_decl node)
{
    return TRANSLATION_UNIT_LANGUAGE(node.inner);
}


GCC_IMPLEMENT_PUBLIC_API(bool)
gcc_for_each_translation_unit_decl(
    bool (*cb)(gcc_translation_unit_decl node, void *user_data),
    void *user_data)
{
    int i;
    tree t;

    /*
      all_translation_units was made globally visible in gcc revision 164331:
        http://gcc.gnu.org/ml/gcc-cvs/2010-09/msg00625.html
        http://gcc.gnu.org/viewcvs?view=revision&revision=164331
    */
    FOR_EACH_VEC_ELT(tree, all_translation_units, i, t) {
        if (cb(gcc_private_make_translation_unit_decl(t),
               user_data)) {
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
