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

#include "gcc-location.h"

/***********************************************************
   gcc_location
************************************************************/
GCC_IMPLEMENT_PRIVATE_API (struct gcc_location)
gcc_private_make_location (location_t inner)
{
  struct gcc_location result;
  result.inner = inner;
  return result;
}

GCC_IMPLEMENT_PUBLIC_API (void) gcc_location_mark_in_use (gcc_location loc)
{
  /* empty */
}

GCC_IMPLEMENT_PUBLIC_API (const char *)
gcc_location_get_filename (gcc_location loc)
{
  return LOCATION_FILE (loc.inner);
}

GCC_IMPLEMENT_PUBLIC_API (int) gcc_location_get_line (gcc_location loc)
{
  return LOCATION_LINE (loc.inner);
}

GCC_IMPLEMENT_PUBLIC_API (int) gcc_location_get_column (gcc_location loc)
{
  expanded_location exploc = expand_location (loc.inner);
  return exploc.column;
}

GCC_PUBLIC_API (bool) gcc_location_is_unknown (gcc_location loc)
{
  return UNKNOWN_LOCATION == loc.inner || !gcc_location_get_filename(loc);
}

GCC_IMPLEMENT_PUBLIC_API (bool) gcc_location_get_in_system_header (gcc_location loc)
{
  return in_system_header_at (loc.inner);
}

GCC_IMPLEMENT_PUBLIC_API (void) gcc_set_input_location (gcc_location loc)
{
  input_location = loc.inner;
}

GCC_IMPLEMENT_PUBLIC_API (gcc_location) gcc_get_input_location (void)
{
  return gcc_private_make_location (input_location);
}

/*
Local variables:
c-basic-offset: 2
indent-tabs-mode: nil
End:
*/
