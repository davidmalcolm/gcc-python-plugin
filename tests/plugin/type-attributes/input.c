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

/* No nonnull attribute on this one: */
typedef int (example0)(const char *, const char *, const char *);

/* Blanket nonnull attribute on this one: */
typedef int (example1)(const char *, const char *, const char *)
  __attribute__((nonnull));

/* nonnull attribute on args 1 and 3: */
typedef int (example2)(const char *, const char *, const char *)
  __attribute__((nonnull(1, 3)));

/* Repeated nonnull attribute (it's not clear that gcc itself copes with
   this): */
typedef int (example3)(const char *, const char *, const char *)
  __attribute__((nonnull(1)))
  __attribute__((nonnull(3)));

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
