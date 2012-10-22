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
#include <string.h>

struct foo
{
  signed int i;
  char buf[256];
};

char test(FILE *f)
{
  struct foo tmp;

  if (1 == fread(&tmp, sizeof(tmp), 1, f)) {
    /* BUG: the following array lookup trusts that the input data's index is
       in the range 0 <= i < 256; otherwise it's accessing the stack */
    return tmp.buf[tmp.i];
  }
  return 0;
}

char test2(struct foo *f, int i)
{
  /* not a bug: the data is not known to be tainted: */
  return f->buf[f->i];
}

char test3(FILE *f)
{
  struct foo tmp;

  if (1 == fread(&tmp, sizeof(tmp), 1, f)) {
    if (tmp.i >= 0 && tmp.i < 256) {
      /* not a bug: the access is guarded by upper and lower bounds: */
      return tmp.buf[tmp.i];
    }
  }
  return 0;
}

char test4(FILE *f)
{
  struct foo tmp;

  if (1 == fread(&tmp, sizeof(tmp), 1, f)) {
    if (tmp.i >= 0) {
      /* BUG: has a lower bound, but not an upper bound: */
      return tmp.buf[tmp.i];
    }
  }
  return 0;
}

char test5(FILE *f)
{
  struct foo tmp;

  if (1 == fread(&tmp, sizeof(tmp), 1, f)) {
    if (tmp.i < 256) {
      /* BUG: has an upper bound, but not a lower bound: */
      return tmp.buf[tmp.i];
    }
  }
  return 0;
}

/* unsigned types have a natural lower bound of 0 */
struct bar
{
  unsigned int i;
  char buf[256];
};

char test6(FILE *f)
{
  struct bar tmp;

  if (1 == fread(&tmp, sizeof(tmp), 1, f)) {
    if (tmp.i >= 0) {
      /* BUG: has an implicit lower bound, but not an upper bound: */
      return tmp.buf[tmp.i];
    }
  }
  return 0;
}

char test7(FILE *f)
{
  struct bar tmp;

  if (1 == fread(&tmp, sizeof(tmp), 1, f)) {
    if (tmp.i < 256) {
      /* not a bug: has an upper bound, and an implicit lower bound: */
      return tmp.buf[tmp.i];
    }
  }
  return 0;
}

char test8(FILE *f)
{
  struct foo tmp;

  if (1 == fread(&tmp, sizeof(tmp), 1, f)) {
    if (tmp.i == 42) {
      /* not a bug: tmp.i compared against a specific value: */
      return tmp.buf[tmp.i];
    }
  }
  return 0;
}
