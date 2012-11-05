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
#include "gcc-semiprivate-types.h"
#include "gcc-declaration.h"
#include "tree.h"
#include "gcc-internal.h"

/***************************************************************************
 gcc_decl
 **************************************************************************/

GCC_IMPLEMENT_PUBLIC_API (gcc_location) gcc_decl_get_location (gcc_decl decl)
{
  return gcc_private_make_location (DECL_SOURCE_LOCATION (decl.inner));
}

GCC_IMPLEMENT_PUBLIC_API (bool) gcc_decl_is_artificial (gcc_decl decl)
{
  return DECL_ARTIFICIAL (decl.inner);
}

GCC_IMPLEMENT_PUBLIC_API(bool) gcc_decl_is_builtin(gcc_decl decl)
{
  return DECL_IS_BUILTIN (decl.inner);
}

GCC_IMPLEMENT_PUBLIC_API (gcc_tree) gcc_decl_as_gcc_tree (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_class_method_decl)
gcc_decl_as_gcc_class_method_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_const_decl)
gcc_decl_as_gcc_const_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_debug_expr_decl)
gcc_decl_as_gcc_debug_expr_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_field_decl)
gcc_decl_as_gcc_field_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_function_decl)
gcc_decl_as_gcc_function_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_imported_decl)
gcc_decl_as_gcc_imported_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_instance_method_decl)
gcc_decl_as_gcc_instance_method_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_keyword_decl)
gcc_decl_as_gcc_keyword_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_label_decl)
gcc_decl_as_gcc_label_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_namespace_decl)
gcc_decl_as_gcc_namespace_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_parm_decl)
gcc_decl_as_gcc_parm_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_property_decl)
gcc_decl_as_gcc_property_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_result_decl)
gcc_decl_as_gcc_result_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_template_decl)
gcc_decl_as_gcc_template_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_translation_unit_decl)
gcc_decl_as_gcc_translation_unit_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_type_decl)
gcc_decl_as_gcc_type_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_using_decl)
gcc_decl_as_gcc_using_decl (gcc_decl node);

GCC_IMPLEMENT_PUBLIC_API (gcc_var_decl)
gcc_decl_as_gcc_var_decl (gcc_decl node);

GCC_IMPLEMENT_PRIVATE_API (struct gcc_function_decl)
gcc_private_make_function_decl (tree inner)
{
  struct gcc_function_decl result;
  result.inner = FUNCTION_DECL_CHECK (inner);
  return result;
}

GCC_IMPLEMENT_PRIVATE_API (struct gcc_translation_unit_decl)
gcc_private_make_translation_unit_decl (tree inner)
{
  struct gcc_translation_unit_decl result;
  result.inner = TRANSLATION_UNIT_DECL_CHECK (inner);
  return result;
}


IMPLEMENT_CAST (gcc_decl, gcc_tree)
IMPLEMENT_CAST (gcc_decl, gcc_translation_unit_decl)
/***************************************************************************
 gcc_class_method_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_class_method_decl, gcc_decl)
IMPLEMENT_CAST (gcc_class_method_decl, gcc_tree)
/***************************************************************************
 gcc_const_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_const_decl, gcc_decl)
IMPLEMENT_CAST (gcc_const_decl, gcc_tree)
/***************************************************************************
 gcc_debug_expr_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_debug_expr_decl, gcc_decl)
IMPLEMENT_CAST (gcc_debug_expr_decl, gcc_tree)
/***************************************************************************
 gcc_field_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_field_decl, gcc_decl)
IMPLEMENT_CAST (gcc_field_decl, gcc_tree)
/***************************************************************************
 gcc_function_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_function_decl, gcc_decl)
IMPLEMENT_CAST (gcc_function_decl, gcc_tree)
/***************************************************************************
 gcc_imported_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_imported_decl, gcc_decl)
IMPLEMENT_CAST (gcc_imported_decl, gcc_tree)
/***************************************************************************
 gcc_instance_method_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_instance_method_decl, gcc_decl)
IMPLEMENT_CAST (gcc_instance_method_decl, gcc_tree)
/***************************************************************************
 gcc_keyword_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_keyword_decl, gcc_decl)
IMPLEMENT_CAST (gcc_keyword_decl, gcc_tree)
/***************************************************************************
 gcc_label_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_label_decl, gcc_decl)
IMPLEMENT_CAST (gcc_label_decl, gcc_tree)
/***************************************************************************
 gcc_namespace_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_namespace_decl, gcc_decl)
IMPLEMENT_CAST (gcc_namespace_decl, gcc_tree)
/***************************************************************************
 gcc_parm_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_parm_decl, gcc_decl)
IMPLEMENT_CAST (gcc_parm_decl, gcc_tree)
/***************************************************************************
 gcc_property_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_property_decl, gcc_decl)
IMPLEMENT_CAST (gcc_property_decl, gcc_tree)
/***************************************************************************
 gcc_result_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_result_decl, gcc_decl)
IMPLEMENT_CAST (gcc_result_decl, gcc_tree)
/***************************************************************************
 gcc_template_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_template_decl, gcc_decl)
IMPLEMENT_CAST (gcc_template_decl, gcc_tree)
/***************************************************************************
 gcc_translation_unit_decl
 **************************************************************************/
  GCC_IMPLEMENT_PUBLIC_API (gcc_block)
gcc_translation_unit_decl_get_block (gcc_translation_unit_decl node)
{
  return gcc_private_make_block (DECL_INITIAL (node.inner));
}

GCC_IMPLEMENT_PUBLIC_API (const char *)
gcc_translation_unit_decl_get_language (gcc_translation_unit_decl node)
{
  return TRANSLATION_UNIT_LANGUAGE (node.inner);
}

IMPLEMENT_CAST (gcc_translation_unit_decl, gcc_decl)
IMPLEMENT_CAST (gcc_translation_unit_decl, gcc_tree)
/***************************************************************************
 gcc_type_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_type_decl, gcc_decl)
IMPLEMENT_CAST (gcc_type_decl, gcc_tree)
/***************************************************************************
 gcc_using_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_using_decl, gcc_decl)
IMPLEMENT_CAST (gcc_using_decl, gcc_tree)
/***************************************************************************
 gcc_var_decl
 **************************************************************************/
  IMPLEMENT_CAST (gcc_var_decl, gcc_decl)
IMPLEMENT_CAST (gcc_var_decl, gcc_tree)
/***************************************************************************
 Other things:
 **************************************************************************/
  GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_for_each_translation_unit_decl (bool (*cb)
				    (gcc_translation_unit_decl node,
				     void *user_data), void *user_data)
{
  int i;
  tree t;

  /*
     all_translation_units was made globally visible in gcc revision 164331:
     http://gcc.gnu.org/ml/gcc-cvs/2010-09/msg00625.html
     http://gcc.gnu.org/viewcvs?view=revision&revision=164331
   */
  FOR_EACH_VEC_ELT (tree, all_translation_units, i, t)
  {
    if (cb (gcc_private_make_translation_unit_decl (t), user_data))
      {
	return true;
      }
  }
  return false;
}


/*
Local variables:
c-basic-offset: 2
indent-tabs-mode: nil
End:
*/
