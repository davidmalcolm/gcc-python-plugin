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
#include "gcc-c-api/gcc-tree.h"
#include "ggc.h"
#include "gcc-internal.h"
#include <assert.h>
#include "tree.h"

/*
  Trees
*/

/* gcc_tree */
GCC_IMPLEMENT_PUBLIC_API(void)
gcc_tree_mark_in_use(gcc_tree node)
{
    /* Mark the underlying object (recursing into its fields): */
    gt_ggc_mx_tree_node(node.inner);
}

GCC_IMPLEMENT_PRIVATE_API(struct gcc_tree)
gcc_private_make_tree(tree inner)
{
    struct gcc_tree result;
    /* FIXME: type-checking */
    result.inner = inner;
    return result;
}

GCC_IMPLEMENT_PRIVATE_API(struct gcc_block)
gcc_private_make_block(tree inner)
{
    struct gcc_block result;
    result.inner = BLOCK_CHECK(inner);
    return result;
}

IMPLEMENT_CAST(gcc_tree, gcc_constant)
IMPLEMENT_CAST(gcc_tree, gcc_decl)
IMPLEMENT_CAST(gcc_tree, gcc_binary)
IMPLEMENT_CAST(gcc_tree, gcc_block)
IMPLEMENT_CAST(gcc_tree, gcc_ssa_name)
IMPLEMENT_CAST(gcc_tree, gcc_statement)
IMPLEMENT_CAST(gcc_tree, gcc_type)
IMPLEMENT_CAST(gcc_tree, gcc_integer_type)
IMPLEMENT_CAST(gcc_tree, gcc_translation_unit_decl)

/* gcc_binary */
GCC_IMPLEMENT_PUBLIC_API(void)
gcc_binary_mark_in_use(gcc_binary node);

GCC_IMPLEMENT_PUBLIC_API(gcc_bitwise_and_expr)
gcc_binary_as_gcc_bitwise_and_expr(gcc_binary node);

GCC_IMPLEMENT_PUBLIC_API(gcc_bitwise_ior_expr)
gcc_binary_as_gcc_bitwise_ior_expr(gcc_binary node);

GCC_IMPLEMENT_PUBLIC_API(gcc_bitwise_xor_expr)
gcc_binary_as_gcc_bitwise_xor_expr(gcc_binary node);


/* gcc_bitwise_and_expr */
GCC_IMPLEMENT_PUBLIC_API(void)
gcc_bitwise_and_expr_mark_in_use(gcc_bitwise_and_expr node);

/* gcc_bitwise_ior_expr */
GCC_IMPLEMENT_PUBLIC_API(void)
gcc_bitwise_ior_expr_mark_in_use(gcc_bitwise_ior_expr node);

/* gcc_bitwise_xor_expr */
GCC_IMPLEMENT_PUBLIC_API(void)
gcc_bitwise_xor_expr_mark_in_use(gcc_bitwise_xor_expr node);

/* gcc_block */
GCC_IMPLEMENT_PUBLIC_API(void)
gcc_block_mark_in_use(gcc_block node);

IMPLEMENT_CAST(gcc_block, gcc_tree)


/***************************************************************************
 gcc_ssa_name
 **************************************************************************/
GCC_IMPLEMENT_PUBLIC_API(gcc_tree)
gcc_ssa_name_get_var(gcc_ssa_name node)
{
    return gcc_private_make_tree(SSA_NAME_VAR(node.inner));
}

GCC_IMPLEMENT_PUBLIC_API(gcc_gimple)
gcc_ssa_name_get_def_stmt(gcc_ssa_name node)
{
    return gcc_private_make_gimple(SSA_NAME_DEF_STMT(node.inner));
}

GCC_IMPLEMENT_PUBLIC_API(int)
gcc_ssa_name_get_version(gcc_ssa_name node)
{
    return SSA_NAME_VERSION(node.inner);
}

IMPLEMENT_CAST(gcc_ssa_name, gcc_tree)


/* gcc_statement */
GCC_IMPLEMENT_PUBLIC_API(void)
gcc_statement_mark_in_use(gcc_statement node);

GCC_IMPLEMENT_PUBLIC_API(gcc_case_label_expr)
gcc_statement_as_gcc_case_label_expr(gcc_statement node);


/* gcc_case_label_expr */
GCC_IMPLEMENT_PUBLIC_API(void)
gcc_case_label_expr_mark_in_use(gcc_case_label_expr node);

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
