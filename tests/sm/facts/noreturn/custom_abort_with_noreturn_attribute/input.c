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

#include <stdio.h>
#include <stdlib.h>

extern void marker_A(void);
extern void marker_B(void);

void custom_abort(const char *msg)  __attribute__ ((__noreturn__));

void custom_abort(const char *msg)
{
  fprintf(stderr, "%s", msg);
  abort();
}

void test(void *ptr)
{
  marker_A();

  if (!ptr) {
    custom_abort("ptr was NULL");
  }

  /* Hence the fact-finder ought to know (ptr != 0) here: */
  marker_B();
}
