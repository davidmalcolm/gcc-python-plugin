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
  Test of reading from a bitfield
*/
struct Foo {
    int a : 4;
    int b : 2;
    int c : 1;
};

extern void __cpychecker_dump(int);

int test(struct Foo *foo)
{
    if (foo->a == 3) {
        return 0;
    }
    __cpychecker_dump(foo->a);

    __cpychecker_dump(foo->b);

    if (foo->c) {
        return 1;
    } else {
        return 2;
    }
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
