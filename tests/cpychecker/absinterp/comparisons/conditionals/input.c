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

#include <Python.h>

/*
  Test that we can cope with various kinds of comparisons
*/

extern void should_not_be_reached(void);
extern void should_be_reached(void);

extern void __cpychecker_log(const char *);

int test_conditionals(void)
{
    /*
       Force the absinterp code to run various comparisons

       All of these comparisons should be fully deterministic, and thus
       there should be just a single trace through the function, with
       a particular pattern of "true" and "false" branches taken
    */
    int one;
    int other_one;
    int two;

    one = 1;
    /* we need a second copy to stop GCC optimizing away some comparisons: */
    other_one = 1;
    two = 2;

    __cpychecker_log("Comparing 1 with 1");
    if (one < other_one) {
        should_not_be_reached();
    }
    if (one <= other_one) {
        should_be_reached();
    }
    if (one == other_one) {
        should_be_reached();
    }
    if (one != other_one) {
        should_not_be_reached();
    }
    if (one >= other_one) {
        should_be_reached();
    }
    if (one > other_one) {
        should_not_be_reached();
    }

    __cpychecker_log("Comparing 1 with 2");
    if (one < two) {
        should_be_reached();
    }
    if (one <= two) {
        should_be_reached();
    }
    if (one == two) {
        should_not_be_reached();
    }
    if (one != two) {
        should_be_reached();
    }
    if (one >= two) {
        should_be_reached();
    }
    if (one > two) {
        should_not_be_reached();
    }

    __cpychecker_log("Comparing 2 with 1");
    if (two < one) {
        should_not_be_reached();
    }
    if (two <= one) {
        should_not_be_reached();
    }
    if (two == one) {
        should_not_be_reached();
    }
    if (two != one) {
        should_be_reached();
    }
    if (two >= one) {
        should_be_reached();
    }
    if (two > one) {
        should_be_reached();
    }
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
