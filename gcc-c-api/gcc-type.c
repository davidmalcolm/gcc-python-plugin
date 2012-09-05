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
#include "gcc-type.h"
#include "gcc-constant.h"
#include "gcc-tree.h"
#include "gcc-internal.h"
#include "tree.h"

/*
  Types
*/

GCC_IMPLEMENT_PRIVATE_API (gcc_pointer_type)
gcc_private_make_pointer_type (tree inner)
{
  struct gcc_pointer_type result;
  result.inner = inner;
  return result;
}

/***************************************************************************
 gcc_type
 **************************************************************************/

GCC_IMPLEMENT_PUBLIC_API (gcc_tree) gcc_type_get_name (gcc_type node)
{
  return gcc_private_make_tree (TYPE_NAME (node.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_pointer_type)
gcc_type_get_pointer (gcc_type node)
{
  return gcc_private_make_pointer_type (build_pointer_type (node.inner));
}

IMPLEMENT_CAST (gcc_type, gcc_tree)
IMPLEMENT_CAST (gcc_type, gcc_array_type)
IMPLEMENT_CAST (gcc_type, gcc_boolean_type)
IMPLEMENT_CAST (gcc_type, gcc_bound_template_template_parm)
IMPLEMENT_CAST (gcc_type, gcc_category_implementation_type)
IMPLEMENT_CAST (gcc_type, gcc_category_interface_type)
IMPLEMENT_CAST (gcc_type, gcc_class_implementation_type)
IMPLEMENT_CAST (gcc_type, gcc_class_interface_type)
IMPLEMENT_CAST (gcc_type, gcc_complex_type)
IMPLEMENT_CAST (gcc_type, gcc_decl_type_type)
IMPLEMENT_CAST (gcc_type, gcc_enumeral_type)
IMPLEMENT_CAST (gcc_type, gcc_fixed_point_type)
IMPLEMENT_CAST (gcc_type, gcc_function_type)
IMPLEMENT_CAST (gcc_type, gcc_integer_type)
IMPLEMENT_CAST (gcc_type, gcc_lang_type)
IMPLEMENT_CAST (gcc_type, gcc_method_type)
IMPLEMENT_CAST (gcc_type, gcc_null_ptr_type)
IMPLEMENT_CAST (gcc_type, gcc_offset_type)
IMPLEMENT_CAST (gcc_type, gcc_pointer_type)
IMPLEMENT_CAST (gcc_type, gcc_protocol_interface_type)
IMPLEMENT_CAST (gcc_type, gcc_qual_union_type)
IMPLEMENT_CAST (gcc_type, gcc_real_type)
IMPLEMENT_CAST (gcc_type, gcc_record_type)
IMPLEMENT_CAST (gcc_type, gcc_reference_type)
IMPLEMENT_CAST (gcc_type, gcc_template_template_parm)
IMPLEMENT_CAST (gcc_type, gcc_template_type_parm)
IMPLEMENT_CAST (gcc_type, gcc_type_argument_pack)
IMPLEMENT_CAST (gcc_type, gcc_type_pack_expansion)
IMPLEMENT_CAST (gcc_type, gcc_typename_type)
IMPLEMENT_CAST (gcc_type, gcc_typeof_type)
IMPLEMENT_CAST (gcc_type, gcc_unbound_class_template)
IMPLEMENT_CAST (gcc_type, gcc_unconstrained_array_type)
IMPLEMENT_CAST (gcc_type, gcc_union_type)
IMPLEMENT_CAST (gcc_type, gcc_vector_type)
IMPLEMENT_CAST (gcc_type, gcc_void_type)
/***************************************************************************
 gcc_array_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_array_type, gcc_type)
IMPLEMENT_CAST (gcc_array_type, gcc_tree)
/***************************************************************************
 gcc_boolean_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_boolean_type, gcc_type)
IMPLEMENT_CAST (gcc_boolean_type, gcc_tree)
/***************************************************************************
 gcc_bound_template_template_parm
 **************************************************************************/
  IMPLEMENT_CAST (gcc_bound_template_template_parm, gcc_type)
IMPLEMENT_CAST (gcc_bound_template_template_parm, gcc_tree)
/***************************************************************************
 gcc_category_implementation_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_category_implementation_type, gcc_type)
IMPLEMENT_CAST (gcc_category_implementation_type, gcc_tree)
/***************************************************************************
 gcc_category_interface_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_category_interface_type, gcc_type)
IMPLEMENT_CAST (gcc_category_interface_type, gcc_tree)
/***************************************************************************
 gcc_class_implementation_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_class_implementation_type, gcc_type)
IMPLEMENT_CAST (gcc_class_implementation_type, gcc_tree)
/***************************************************************************
 gcc_class_interface_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_class_interface_type, gcc_type)
IMPLEMENT_CAST (gcc_class_interface_type, gcc_tree)
/***************************************************************************
 gcc_complex_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_complex_type, gcc_type)
IMPLEMENT_CAST (gcc_complex_type, gcc_tree)
/***************************************************************************
 gcc_decl_type_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_decl_type_type, gcc_type)
IMPLEMENT_CAST (gcc_decl_type_type, gcc_tree)
/***************************************************************************
 gcc_enumeral_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_enumeral_type, gcc_type)
IMPLEMENT_CAST (gcc_enumeral_type, gcc_tree)
/***************************************************************************
 gcc_fixed_point_type
 **************************************************************************/

GCC_IMPLEMENT_PUBLIC_API (int)
gcc_fixed_point_type_get_precision (gcc_fixed_point_type node)
{
  return TYPE_PRECISION (node.inner);
}

  IMPLEMENT_CAST (gcc_fixed_point_type, gcc_type)
IMPLEMENT_CAST (gcc_fixed_point_type, gcc_tree)
/***************************************************************************
 gcc_function_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_function_type, gcc_type)
IMPLEMENT_CAST (gcc_function_type, gcc_tree)
/***************************************************************************
 gcc_integer_type
 **************************************************************************/
  GCC_IMPLEMENT_PUBLIC_API (gcc_integer_constant)
gcc_integer_type_get_max_value (gcc_integer_type node)
{
  return gcc_private_make_integer_constant (TYPE_MAX_VALUE (node.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_integer_constant)
gcc_integer_type_get_min_value (gcc_integer_type node)
{
  return gcc_private_make_integer_constant (TYPE_MIN_VALUE (node.inner));
}

GCC_IMPLEMENT_PUBLIC_API (int)
gcc_integer_type_get_precision (gcc_integer_type node)
{
  return TYPE_PRECISION (node.inner);
}

IMPLEMENT_CAST (gcc_integer_type, gcc_type)
/* gcc_integer_type */
  GCC_IMPLEMENT_PRIVATE_API (gcc_integer_constant)
gcc_private_make_integer_constant (tree inner)
{
  gcc_integer_constant result;
  result.inner = INTEGER_CST_CHECK (inner);
  return result;
}


/***************************************************************************
 gcc_lang_type
 **************************************************************************/

IMPLEMENT_CAST (gcc_lang_type, gcc_type)
IMPLEMENT_CAST (gcc_lang_type, gcc_tree)
/***************************************************************************
 gcc_method_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_method_type, gcc_type)
IMPLEMENT_CAST (gcc_method_type, gcc_tree)
/***************************************************************************
 gcc_null_ptr_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_null_ptr_type, gcc_type)
IMPLEMENT_CAST (gcc_null_ptr_type, gcc_tree)
/***************************************************************************
 gcc_offset_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_offset_type, gcc_type)
IMPLEMENT_CAST (gcc_offset_type, gcc_tree)
/***************************************************************************
 gcc_pointer_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_pointer_type, gcc_type)
IMPLEMENT_CAST (gcc_pointer_type, gcc_tree)
/***************************************************************************
 gcc_protocol_interface_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_protocol_interface_type, gcc_type)
IMPLEMENT_CAST (gcc_protocol_interface_type, gcc_tree)
/***************************************************************************
 gcc_qual_union_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_qual_union_type, gcc_type)
IMPLEMENT_CAST (gcc_qual_union_type, gcc_tree)
/***************************************************************************
 gcc_real_type
 **************************************************************************/
GCC_IMPLEMENT_PUBLIC_API (int)
gcc_real_type_get_precision (gcc_real_type node)
{
  return TYPE_PRECISION (node.inner);
}

  IMPLEMENT_CAST (gcc_real_type, gcc_type)
IMPLEMENT_CAST (gcc_real_type, gcc_tree)
/***************************************************************************
 gcc_record_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_record_type, gcc_type)
IMPLEMENT_CAST (gcc_record_type, gcc_tree)
/***************************************************************************
 gcc_reference_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_reference_type, gcc_type)
IMPLEMENT_CAST (gcc_reference_type, gcc_tree)
/***************************************************************************
 gcc_template_template_parm
 **************************************************************************/
  IMPLEMENT_CAST (gcc_template_template_parm, gcc_type)
IMPLEMENT_CAST (gcc_template_template_parm, gcc_tree)
/***************************************************************************
 gcc_template_type_parm
 **************************************************************************/
  IMPLEMENT_CAST (gcc_template_type_parm, gcc_type)
IMPLEMENT_CAST (gcc_template_type_parm, gcc_tree)
/***************************************************************************
 gcc_type_argument_pack
 **************************************************************************/
  IMPLEMENT_CAST (gcc_type_argument_pack, gcc_type)
IMPLEMENT_CAST (gcc_type_argument_pack, gcc_tree)
/***************************************************************************
 gcc_type_pack_expansion
 **************************************************************************/
  IMPLEMENT_CAST (gcc_type_pack_expansion, gcc_type)
IMPLEMENT_CAST (gcc_type_pack_expansion, gcc_tree)
/***************************************************************************
 gcc_typename_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_typename_type, gcc_type)
IMPLEMENT_CAST (gcc_typename_type, gcc_tree)
/***************************************************************************
 gcc_typeof_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_typeof_type, gcc_type)
IMPLEMENT_CAST (gcc_typeof_type, gcc_tree)
/***************************************************************************
 gcc_unbound_class_template
 **************************************************************************/
  IMPLEMENT_CAST (gcc_unbound_class_template, gcc_type)
IMPLEMENT_CAST (gcc_unbound_class_template, gcc_tree)
/***************************************************************************
 gcc_unconstrained_array_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_unconstrained_array_type, gcc_type)
IMPLEMENT_CAST (gcc_unconstrained_array_type, gcc_tree)
/***************************************************************************
 gcc_union_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_union_type, gcc_type)
IMPLEMENT_CAST (gcc_union_type, gcc_tree)
/***************************************************************************
 gcc_vector_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_vector_type, gcc_type)
IMPLEMENT_CAST (gcc_vector_type, gcc_tree)
/***************************************************************************
 gcc_void_type
 **************************************************************************/
  IMPLEMENT_CAST (gcc_void_type, gcc_type)
IMPLEMENT_CAST (gcc_void_type, gcc_tree)
/*
Local variables:
c-basic-offset: 2
indent-tabs-mode: nil
End:
*/
