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

/* Test of adding custom attributes */

#if defined(WITH_ATTRIBUTE_CLAIMS_MUTEX)
 #define CLAIMS_MUTEX(x) __attribute__((claims_mutex(x)))
#else
 #define CLAIMS_MUTEX(x)
#endif

#if defined(WITH_ATTRIBUTE_RELEASES_MUTEX)
 #define RELEASES_MUTEX(x) __attribute__((releases_mutex(x)))
#else
 #define RELEASES_MUTEX(x)
#endif


/* Function declarations with custom attributes: */
extern void some_function(void)
    CLAIMS_MUTEX("io");

extern void some_other_function(void)
    RELEASES_MUTEX("io");

extern void yet_another_function(void)
    CLAIMS_MUTEX("db")
    CLAIMS_MUTEX("io")
    RELEASES_MUTEX("io");

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
