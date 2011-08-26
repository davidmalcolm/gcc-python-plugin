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

extern void __cpychecker_log(const char *);
extern void __cpychecker_assert_equal(int, int);

int test_comparison_expressions(void)
{
    /*
       Force the absinterp code to evaluate various boolean expressions,
       checking the results
    */
    int one;
    int other_one;
    int two;

    one = 1;
    /* we need a second copy to stop GCC optimizing away some comparisons: */
    other_one = 1;
    two = 2;

    __cpychecker_log("Comparing 1 with 1");
    __cpychecker_assert_equal(one < other_one, 0);
    __cpychecker_assert_equal(one <= other_one, 1);
    __cpychecker_assert_equal(one == other_one, 1);
    __cpychecker_assert_equal(one != other_one, 0);
    __cpychecker_assert_equal(one >= other_one, 1);
    __cpychecker_assert_equal(one > other_one, 0);

    __cpychecker_log("Comparing 1 with 2");
    __cpychecker_assert_equal(one < two, 1);
    __cpychecker_assert_equal(one <= two, 1);
    __cpychecker_assert_equal(one == two, 0);
    __cpychecker_assert_equal(one != two, 1);
    __cpychecker_assert_equal(one >= two, 0);
    __cpychecker_assert_equal(one > two, 0);

    __cpychecker_log("Comparing 2 with 1");
    __cpychecker_assert_equal(two < one, 0);
    __cpychecker_assert_equal(two <= one, 0);
    __cpychecker_assert_equal(two == one, 0);
    __cpychecker_assert_equal(two != one, 1);
    __cpychecker_assert_equal(two >= one, 1);
    __cpychecker_assert_equal(two > one, 1);
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
