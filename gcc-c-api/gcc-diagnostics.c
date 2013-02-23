/*
   Copyright 2013 David Malcolm <dmalcolm@redhat.com>
   Copyright 2013 Red Hat, Inc.

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

#include "gcc-diagnostics.h"

#include "diagnostic.h"

GCC_IMPLEMENT_PUBLIC_API(void)
gcc_inform(gcc_location location, const char* message)
{
  return inform(location.inner, "%s", message);
}

GCC_IMPLEMENT_PUBLIC_API(void)
gcc_error_at(gcc_location location, const char* message)
{
  return error_at(location.inner, "%s", message);
}

#if 0
GCC_IMPLEMENT_PUBLIC_API(bool)
gcc_warning_at(gcc_location location, const char* message, gcc_option option)
{
  /* TODO (what about the no-option case?) */
}
#endif

GCC_IMPLEMENT_PUBLIC_API(bool)
gcc_permerror(gcc_location location, const char* message)
{
  return permerror(location.inner, "%s", message);
}

/*
Local variables:
c-basic-offset: 2
indent-tabs-mode: nil
End:
*/
