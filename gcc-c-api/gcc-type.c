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

GCC_IMPLEMENT_PRIVATE_API (gcc_type)
gcc_private_make_type (tree inner)
{
  struct gcc_type result;
  result.inner = inner;
  return result;
}

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

/***************************************************************************
 gcc_array_type
 **************************************************************************/
GCC_IMPLEMENT_PUBLIC_API(gcc_type)
gcc_array_type_get_dereference(gcc_array_type node)
{
  return gcc_private_make_type (TREE_TYPE (node.inner));
}

/***************************************************************************
 gcc_boolean_type
 **************************************************************************/
/***************************************************************************
 gcc_bound_template_template_parm
 **************************************************************************/
/***************************************************************************
 gcc_category_implementation_type
 **************************************************************************/
/***************************************************************************
 gcc_category_interface_type
 **************************************************************************/
/***************************************************************************
 gcc_class_implementation_type
 **************************************************************************/
/***************************************************************************
 gcc_class_interface_type
 **************************************************************************/
/***************************************************************************
 gcc_complex_type
 **************************************************************************/
/***************************************************************************
 gcc_decl_type_type
 **************************************************************************/
/***************************************************************************
 gcc_enumeral_type
 **************************************************************************/
/***************************************************************************
 gcc_fixed_point_type
 **************************************************************************/

GCC_IMPLEMENT_PUBLIC_API (int)
gcc_fixed_point_type_get_precision (gcc_fixed_point_type node)
{
  return TYPE_PRECISION (node.inner);
}

/***************************************************************************
 gcc_function_type
 **************************************************************************/
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

GCC_IMPLEMENT_PUBLIC_API(bool)
gcc_integer_type_is_unsigned(gcc_integer_type node)
{
  return TYPE_UNSIGNED (node.inner);
}

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

/***************************************************************************
 gcc_method_type
 **************************************************************************/
/***************************************************************************
 gcc_null_ptr_type
 **************************************************************************/
/***************************************************************************
 gcc_offset_type
 **************************************************************************/
/***************************************************************************
 gcc_pointer_type
 **************************************************************************/
GCC_IMPLEMENT_PUBLIC_API(gcc_type)
gcc_pointer_type_get_dereference(gcc_pointer_type node)
{
  return gcc_private_make_type (TREE_TYPE (node.inner));
}

/***************************************************************************
 gcc_protocol_interface_type
 **************************************************************************/
/***************************************************************************
 gcc_qual_union_type
 **************************************************************************/
/***************************************************************************
 gcc_real_type
 **************************************************************************/
GCC_IMPLEMENT_PUBLIC_API (int)
gcc_real_type_get_precision (gcc_real_type node)
{
  return TYPE_PRECISION (node.inner);
}

/***************************************************************************
 gcc_record_type
 **************************************************************************/
/***************************************************************************
 gcc_reference_type
 **************************************************************************/
/***************************************************************************
 gcc_template_template_parm
 **************************************************************************/
/***************************************************************************
 gcc_template_type_parm
 **************************************************************************/
/***************************************************************************
 gcc_type_argument_pack
 **************************************************************************/
/***************************************************************************
 gcc_type_pack_expansion
 **************************************************************************/
/***************************************************************************
 gcc_typename_type
 **************************************************************************/
/***************************************************************************
 gcc_typeof_type
 **************************************************************************/
/***************************************************************************
 gcc_unbound_class_template
 **************************************************************************/
/***************************************************************************
 gcc_unconstrained_array_type
 **************************************************************************/
/***************************************************************************
 gcc_union_type
 **************************************************************************/
/***************************************************************************
 gcc_vector_type
 **************************************************************************/
GCC_IMPLEMENT_PUBLIC_API(gcc_type)
gcc_vector_type_get_dereference(gcc_vector_type node)
{
  return gcc_private_make_type (TREE_TYPE (node.inner));
}

/***************************************************************************
 gcc_void_type
 **************************************************************************/
/*
Local variables:
c-basic-offset: 2
indent-tabs-mode: nil
End:
*/
