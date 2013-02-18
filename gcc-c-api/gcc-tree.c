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

#include "gcc-common.h"
#include "gcc-tree.h"
#include "ggc.h"
#include "gcc-internal.h"
#include <assert.h>
#include "tree.h"

/*
  Trees
*/

/* gcc_tree */
GCC_IMPLEMENT_PUBLIC_API (void) gcc_tree_mark_in_use (gcc_tree node)
{
  /* Mark the underlying object (recursing into its fields): */
  gt_ggc_mx_tree_node (node.inner);
}

GCC_IMPLEMENT_PRIVATE_API (struct gcc_tree)
gcc_private_make_tree (tree inner)
{
  struct gcc_tree result;
  /* FIXME: type-checking */
  result.inner = inner;
  return result;
}

GCC_IMPLEMENT_PRIVATE_API (struct gcc_block)
gcc_private_make_block (tree inner)
{
  struct gcc_block result;
  result.inner = BLOCK_CHECK (inner);
  return result;
}

/* gcc_binary */
  GCC_IMPLEMENT_PUBLIC_API (void) gcc_binary_mark_in_use (gcc_binary node);

GCC_IMPLEMENT_PUBLIC_API(gcc_location)
gcc_binary_get_location(gcc_binary node)
{
  return gcc_private_make_location (EXPR_LOCATION (node.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_bitwise_and_expr)
gcc_binary_as_gcc_bitwise_and_expr (gcc_binary node);

GCC_IMPLEMENT_PUBLIC_API (gcc_bitwise_ior_expr)
gcc_binary_as_gcc_bitwise_ior_expr (gcc_binary node);

GCC_IMPLEMENT_PUBLIC_API (gcc_bitwise_xor_expr)
gcc_binary_as_gcc_bitwise_xor_expr (gcc_binary node);


/* gcc_bitwise_and_expr */
GCC_IMPLEMENT_PUBLIC_API (void)
gcc_bitwise_and_expr_mark_in_use (gcc_bitwise_and_expr node);

/* gcc_bitwise_ior_expr */
GCC_IMPLEMENT_PUBLIC_API (void)
gcc_bitwise_ior_expr_mark_in_use (gcc_bitwise_ior_expr node);

/* gcc_bitwise_xor_expr */
GCC_IMPLEMENT_PUBLIC_API (void)
gcc_bitwise_xor_expr_mark_in_use (gcc_bitwise_xor_expr node);

/* gcc_block */
GCC_IMPLEMENT_PUBLIC_API (void)
gcc_block_mark_in_use (gcc_block node);

/***************************************************************************
 gcc_comparison
 **************************************************************************/
GCC_IMPLEMENT_PUBLIC_API(gcc_location)
gcc_comparison_get_location(gcc_comparison node)
{
  return gcc_private_make_location (EXPR_LOCATION (node.inner));
}

/***************************************************************************
 gcc_expression
 **************************************************************************/
GCC_IMPLEMENT_PUBLIC_API(gcc_location)
gcc_expression_get_location(gcc_expression node)
{
  return gcc_private_make_location (EXPR_LOCATION (node.inner));
}

/***************************************************************************
 gcc_reference
 **************************************************************************/
GCC_IMPLEMENT_PUBLIC_API(gcc_location)
gcc_reference_get_location(gcc_reference node)
{
  return gcc_private_make_location (EXPR_LOCATION (node.inner));
}


/***************************************************************************
 gcc_ssa_name
 **************************************************************************/
  GCC_IMPLEMENT_PUBLIC_API (gcc_tree) gcc_ssa_name_get_var (gcc_ssa_name node)
{
  return gcc_private_make_tree (SSA_NAME_VAR (node.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_gimple)
gcc_ssa_name_get_def_stmt (gcc_ssa_name node)
{
  return gcc_private_make_gimple (SSA_NAME_DEF_STMT (node.inner));
}

GCC_IMPLEMENT_PUBLIC_API (int) gcc_ssa_name_get_version (gcc_ssa_name node)
{
  return SSA_NAME_VERSION (node.inner);
}

/***************************************************************************
 gcc_statement
 **************************************************************************/
  GCC_IMPLEMENT_PUBLIC_API (void)
gcc_statement_mark_in_use (gcc_statement node);

GCC_IMPLEMENT_PUBLIC_API(gcc_location)
gcc_statement_get_location(gcc_statement node)
{
  return gcc_private_make_location (EXPR_LOCATION (node.inner));
}

/***************************************************************************
 gcc_case_label_expr
 **************************************************************************/
GCC_IMPLEMENT_PRIVATE_API (struct gcc_case_label_expr)
gcc_private_make_case_label_expr (tree inner)
{
  struct gcc_case_label_expr result;
  /* FIXME: type-checking */
  result.inner = inner;
  return result;
}

GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_case_label_expr_get_low (gcc_case_label_expr node)
{
  return gcc_private_make_tree (CASE_LOW (node.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_tree)
gcc_case_label_expr_get_high (gcc_case_label_expr node)
{
  return gcc_private_make_tree (CASE_HIGH (node.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_label_decl)
gcc_case_label_expr_get_target (gcc_case_label_expr node)
{
  return
    gcc_tree_as_gcc_label_decl (gcc_private_make_tree
				(CASE_LABEL (node.inner)));
}

/***************************************************************************
 gcc_unary
 **************************************************************************/
GCC_IMPLEMENT_PUBLIC_API(gcc_location)
gcc_unary_get_location(gcc_unary node)
{
  return gcc_private_make_location (EXPR_LOCATION (node.inner));
}

GCC_IMPLEMENT_PUBLIC_API(gcc_tree)
gcc_unary_get_operand(gcc_unary node)
{
  return gcc_private_make_tree (TREE_OPERAND (node.inner, 0));
}

/***************************************************************************
 gcc_vlexp
 **************************************************************************/
GCC_IMPLEMENT_PUBLIC_API(gcc_location)
gcc_vlexp_get_location(gcc_vlexp node)
{
  return gcc_private_make_location (EXPR_LOCATION (node.inner));
}

/*
Local variables:
c-basic-offset: 2
indent-tabs-mode: nil
End:
*/
