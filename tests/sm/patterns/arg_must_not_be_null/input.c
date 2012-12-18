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

extern void foo(void *ptrA, void *ptrB, void *ptrC)
  __attribute__((nonnull (1, 3)));

extern void bar(void *ptrA, void *ptrB, void *ptrC)
  __attribute__((nonnull (1, 3)));

void foo(void *ptrA, void *ptrB, void *ptrC)
{
}

void test(void)
{
  void *p;
  void *q;
  void *r;

  p = NULL;
  q = NULL;
  r = NULL;

  foo(p, q, r);
  bar(p, q, r);
}
