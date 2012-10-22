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

static void *f(int a)
{
  if (a) {
    void *p = malloc(4096);
    return p;
  } else {
    return NULL;
  }
}

static void g(int b, void *q)
{
  if (b==2) {
    g(b, q); /* contrived infinite recursion */
  }
  free(q);
}

void h(int c)
{
  int *r = (int*)f(c);
  r[0] = 42; /* BUG: the malloc in f could have failed */
  g(c, r);
  free(r); /* BUG: doublefree here, given that g frees the ptr */
}

static int factorial(int n)
{
  if (n < 2) {
    return 1;
  } else {
    return n * factorial(n-1);
  }
}
