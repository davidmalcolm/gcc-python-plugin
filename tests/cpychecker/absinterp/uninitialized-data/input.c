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
  Test of handling uninitialized data
*/

extern void fn_that_could_write_back_a_value(int *dst);

int test_void(int i)
{
    int j; /* not initialized */

    if (i == 0) {
        /*
          A comparison against uninitialized data ("j") ought to trigger a
          warning:
        */
        if (i < j) {
            return 0;
        } else {
            return 1;
        }
    } else {

        /*
           Exposing "j" to a function for writing ought to suppress
           the warning:
        */
        fn_that_could_write_back_a_value(&j);

        /*
          A comparison against uninitialized data ought to trigger a warning,
          but "j" is no longer known to be uninitialized, so there should be
          no warning here:
        */
        if (i < j) {
            return 2;
        } else {
            /*
              This should be recorded as an unknown value, from the function
              call:
            */
            return j;
        }
    }
}

/*
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
