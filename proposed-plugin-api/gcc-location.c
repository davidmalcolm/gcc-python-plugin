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

#include "proposed-plugin-api/gcc-cfg.h"

/***********************************************************
   GccLocationI
************************************************************/
GCC_IMPLEMENT_PRIVATE_API(struct GccLocationI)
GccPrivate_make_LocationI(location_t inner)
{
    struct GccLocationI result;
    result.inner = inner;
    return result;
}

GCC_IMPLEMENT_PUBLIC_API(void)
GccLocationI_MarkInUse(GccLocationI loc)
{
    /* empty */
}

GCC_IMPLEMENT_PUBLIC_API(void)
Gcc_SetInputLocation(GccLocationI loc)
{
    input_location = loc.inner;
}

GCC_IMPLEMENT_PUBLIC_API(GccLocationI)
Gcc_GetInputLocation(void)
{
    return GccPrivate_make_LocationI(input_location);
}

GCC_IMPLEMENT_PUBLIC_API(const char *)
GccLocationI_GetFilename(GccLocationI loc)
{
    return LOCATION_FILE(loc.inner);
}

GCC_IMPLEMENT_PUBLIC_API(int)
GccLocationI_GetLine(GccLocationI loc)
{
    return LOCATION_LINE(loc.inner);
}

GCC_IMPLEMENT_PUBLIC_API(int)
GccLocationI_GetColumn(GccLocationI loc)
{
    expanded_location exploc = expand_location(loc.inner);
    return exploc.column;
}

GCC_PUBLIC_API(bool)
GccLocationI_IsUnknown(GccLocationI loc)
{
    return UNKNOWN_LOCATION == loc.inner;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
