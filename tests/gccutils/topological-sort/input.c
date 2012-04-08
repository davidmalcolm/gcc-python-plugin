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

/*
   Verify that the topological sort code in gccutils works
*/

int a(int);
int b(int);
int c(int);
int d(int);
int e(int);
int f(int);
int g(int);
int h(int);
int j(int);
int k(int);

int a(int i)
{
    return e(i) + c(i);
}

int b(int i)
{
    return 42 - i;
}

int c(int i)
{
    return i * i;
}

int d(int i)
{
    return a(i) + b(c(i));
}

/* Directly recursive (actually factorial) */
int e(int i)
{
    if (i>1) {
        return i * e(i-1);
    } else {
        return 1;
    }
}

/* f and g are mutually recursive */
int f(int i)
{
    return g(i) + b(i);
}

int g(int i)
{
    return f(i) + c(i) + k(i);
}

/* h is entirely disjoint from the rest of the graph */
int h(int i)
{
    return i;
}

int j(int i)
{
    return 2 * f(i);
}

/* k is not defined */

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
