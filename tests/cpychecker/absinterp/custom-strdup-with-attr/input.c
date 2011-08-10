/*
   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011 Red Hat, Inc.

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

#include <Python.h>

/*
   Ensure that we can cope with a strdup function, with a custom allocator.

   Verifying this function exercises various aspects of idiomatic C code.

   Use non-standard allocation and strlen, so that the analyzer can't know
   anything about the results:
*/
extern void *custom_allocator(size_t size);
extern size_t custom_strlen(const char *str);

/*
  This version of test_strdup has the "nonnull" attribute, so the checker
  ought not to complain about possibly reads through NULL "str":
*/
char *
test_strdup(const char *str) __attribute__((nonnull));

char *
test_strdup(const char *str)
{
    char *result;
    char *dst;

    result = (char*)custom_allocator(custom_strlen(str) + 1);

    if (!result) {
        return NULL;
    }

    dst = result;
    while (*str) {
        *(dst++) = *(str++);
    }
    *dst = '\0';

    return result;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
