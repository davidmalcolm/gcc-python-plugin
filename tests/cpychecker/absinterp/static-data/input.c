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
  Test of handling functions with static data:
*/
int test(void)
{
    static int i;

    /*
      i is implicitly zero-initialized before the first time the function
      is entered, and its state persists between calls to the function.

      The analyzer isn't yet smart enough to determine that i is never
      written to, and so believes that both paths are possible:
    */
    if (i) {
        return 42;
    } else {
        return 43;
    }
}

/*
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
