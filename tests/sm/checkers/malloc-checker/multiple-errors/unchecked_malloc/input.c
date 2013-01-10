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

#include <stdlib.h>
#include <string.h>

struct foo {
  int i;
  int j;
  int k;
};

struct foo *test(void)
{
  struct foo *p = (struct foo*)malloc(4096);

  /* BUG: usage of p without checking if malloc return NULL: */
  p->i = 1;

  /* Only the first such usage should be reported: */
  p->j = 2;
  p->k = 3;

  return p;
}
