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

extern void marker_A(void);
extern void marker_B(void);
extern void marker_C(void);
extern void marker_D(void);
extern void marker_E(void);
extern void marker_F(void);

/*
  Ensure that the fact-finder can sanely propagate information about
  arithmetic operations
*/

void test(int i, int j)
{
  int k, m;

  if (i > 42) {
    marker_A();

    i += 3;

    /* (we should now know that i > 45) */
    marker_B();

    i -= 1;

    /* (and now have i > 44) */
    marker_C();

    i = 3 * i;

    /* (likewise now i > 132) */
    marker_D();

    i /= 2;

    /* (should now have i > 66: */
    marker_E();

    /* We don't know anything about j, so we don't know anything about k: */
    k = i + j;

    /* However, we should now know that m > 67: */
    m = i + 1;

    marker_F();

  }

}
