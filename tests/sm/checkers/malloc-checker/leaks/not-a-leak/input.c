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

struct foo
{
  void *q;
};

struct foo f;

void test(void)
{
  void *p;

  p = malloc(1024);

  /* Store p somewhere, thus it is not a leak when p goes out of scope */
  f.q = p;
}

/* FIXME: we shouldn't need a caller of test() for the checker to work;
   currently we do */
void test2(void)
{
  test();
}

