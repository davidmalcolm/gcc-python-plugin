/*
   Copyright 2012, 2017 David Malcolm <dmalcolm@redhat.com>
   Copyright 2012, 2017 Red Hat, Inc.

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

/* get_pure_location and get_finish were added to gcc's input.h in
   gcc's r238792 (aka f17776ffcba650feb512137e3e22a04f3f433c84).
   get_start was added to gcc's input.h in gcc's r239831
   (aka aca2a315073c72fb7c9ab1be779c290cc91f564c).
   I believe that makes them available in gcc 7 onwards.  */

#if (GCC_VERSION >= 7000)

GCC_IMPLEMENT_PUBLIC_API (gcc_location)
gcc_location_get_caret (gcc_location loc)
{
  return gcc_private_make_location (get_pure_location (loc.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_location)
gcc_location_get_start (gcc_location loc)
{
  return gcc_private_make_location (get_start (loc.inner));
}

GCC_IMPLEMENT_PUBLIC_API (gcc_location)
gcc_location_get_finish (gcc_location loc)
{
  return gcc_private_make_location (get_finish (loc.inner));
}

#endif

/* linemap_position_for_loc_and_offset was added in gcc's r217383
   (aka 766928aa6ac2c846c2d098ef4ef9e220feb4dcab).
   It's present in gcc 5.1. */

#if (GCC_VERSION >= 5000)

GCC_IMPLEMENT_PUBLIC_API(gcc_location)
gcc_location_offset_column (gcc_location loc, int offset)
{
  return gcc_private_make_location
    (linemap_position_for_loc_and_offset (line_table, loc.inner,
                                          offset));
}

#endif

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
