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

#include <stdlib.h>
#include <string.h>

void test(void)
{
  void *p, *q;

  p = malloc(1024);
  if (!p) {
    return;
  }

  q = malloc(1024);
  if (!q) {
    /* BUG: leak of p */
    /* FIXME: the bug is reported, but we could do with a better error
       message covering *how* the leak happened */
    return;
  }

  free(p);
  free(q);
}

/* FIXME: we shouldn't need a caller of test() for the checker to work;
   currently we do */
void test2(void)
{
  test();
}

