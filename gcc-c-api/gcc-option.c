/*
   Copyright 2012, 2013 David Malcolm <dmalcolm@redhat.com>
   Copyright 2012, 2013 Red Hat, Inc.

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

#include "gcc-option.h"
#include "opts.h"

/*
  Command-line options
*/

/* gcc_option */

GCC_IMPLEMENT_PRIVATE_API (struct gcc_option)
gcc_private_make_option (enum opt_code inner)
{
  struct gcc_option result;
  result.inner = inner;
  return result;
}

GCC_IMPLEMENT_PUBLIC_API (void)
gcc_option_mark_in_use (gcc_option opt)
{
  /* empty */
}


GCC_IMPLEMENT_PUBLIC_API (const char*)
gcc_option_get_text (gcc_option opt)
{
  return cl_options[opt.inner].opt_text;
}

GCC_IMPLEMENT_PUBLIC_API (bool)
gcc_for_each_option (bool (*cb)(gcc_option opt, void *user_data),
    void *user_data)
{
  int i;
  for (i = 0; i < cl_options_count; i++)
    {
      gcc_option opt = gcc_private_make_option ((enum opt_code)i);
      if (cb (opt, user_data) )
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
