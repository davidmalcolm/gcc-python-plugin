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

void *test(int a)
{
  if (a) {
    void *p = malloc(4096);
    return p; /* not a leak: returned to caller */
    /* FIXME: currently the checked issues a false warning about this */
    /* FIXME: do we need to propagate extra facts within the ErrorGraph, and
       suppress it there?  If we do (implemented), then we get an ErrorGraph in
       which we know p == returnval in the only path through the graph, but
       it's too late to do leak suppression at that point
    */
  } else {
    return NULL;
  }
}
