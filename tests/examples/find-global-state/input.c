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

static int a_global;

struct {
  int i;
} bar;

extern int foo;

int test(int j)
{
  /* A local variable, which should *not* be reported: */
  int i;
  i = j * 4;
  return i + 1;
}

int test2(int j)
{
  static int i = 0;
  i += j;
  return j * i;
}

int test3(int k)
{
  /* We should *not* report about __FUNCTION__ here: */
  printf("%s:%i:%s\n", __FILE__, __LINE__, __FUNCTION__);
}
