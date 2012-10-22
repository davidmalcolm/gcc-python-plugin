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

#if 1
void double_free(void *ptr)
{
  free(ptr);

  /* BUG: double-free: */
  free(ptr);
}
#endif


#if 1
void unchecked_malloc(void)
{
  void *ptr = malloc(4096);
  memset(ptr, 0, 4096);
}
#endif

#if 1
int correct_usage(void)
{
  void *ptr = malloc(4096);
  if (!ptr)
    return -1; /* FIXME: with a plain return we have a BB with no gimple, and that breaks my checker */
  memset(ptr, 0, 4096);
  free(ptr);
  return 0;
}
#endif

#if 1
int two_ptrs(void)
{
  void *p = malloc(4096);
  void *q = malloc(4096);
  if (p) {
    memset(p, 0, 4096); /* Not a bug: checked */
  } else {
    memset(q, 0, 4096); /* BUG: not checked */
  }
  free(p);
  free(q);
  return 0;
}
#endif

#if 1
void fancy_control_flow(int i, int j)
{
  int k;
  void *ptr;
  for (k = i; k < j; k++) {
    switch(k) {
    case 0:
      ptr = malloc(1024);
      break;
    case 1:
      break;
    case 2:
      break;
    default:
      break;
    }
  }
  memset(ptr, 0, 4096);
  free(ptr);
}
#endif
