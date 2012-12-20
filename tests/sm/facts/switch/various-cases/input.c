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
extern void marker_G(void);

void test(int i)
{
  marker_A();

  switch (i) {
    case 0 ... 10: /* GCC's "case ranges" extension to C */
    case 20 ... 30:
      marker_B();
      break;

    case 0x42:
    case 42:
      marker_C();
      break;

    case 70:
      marker_D();
      /* fallthrough: */
    case 80:
      marker_E();
      break;

    default:
      marker_F();
      break;

  }

  marker_G();
}
