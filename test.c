/*
   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011 Red Hat, Inc.

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

/*
  Trivial example code to be compiled, for testing purposes
 */

#include <stdio.h>

int
helper_function(void)
{
    printf("I am a helper function\n");
    return 42;
}

int
main(int argc, char **argv)
{
    int i;

    printf("argc: %i\n", argc);

    for (i = 0; i < argc; i++) {
        printf("argv[%i]: %s\n", argv[i]);
    }

    helper_function();

    return 0;
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
