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

#include <stdio.h>

char *test(const char *name)
{
  char buffer[1024];
  char *result = NULL;

  snprintf(buffer, 1024, "hello %s", name);

  /* Note that if we simply
       "return buffer;"
     gcc is smart enough by itself to issue
        "warning: function returns address of local variable [enabled by default]"
     from c-typeck.c:c_finish_return as it builds the return statement.

     However, if we introduce some dataflow, this warning isn't issued by
     that code - but our points_to_stack.sm script can it:
  */
  result = buffer;

  /* BUG: returns pointer to variable on the stack: */
  return result;
}

char *test2(const char *name)
{
  static char buffer[1024];
  char *result = NULL;

  snprintf(buffer, 1024, "hello %s", name);

  result = buffer;

  /* Not a bug: buffer is static */
  return result;
}

char other_buffer[1024];

char *test3(const char *name)
{
  char *result = NULL;

  snprintf(other_buffer, 1024, "hello %s", name);

  result = other_buffer;

  /* Not a bug: other_buffer is global */
  return result;
}
