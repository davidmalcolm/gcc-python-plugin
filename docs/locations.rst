.. Copyright 2011-2012, 2017 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011-2012, 2017 Red Hat, Inc.

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

Locations
=========

.. py:function:: gccutils.get_src_for_loc(loc)

      Given a :py:class:`gcc.Location`, get the source line as a string
      (without trailing whitespace or newlines)

.. py:class:: gcc.Location

   Wrapper around GCC's `location_t`, representing a location within the source
   code.  Use :py:func:`gccutils.get_src_for_loc` to get at the line of actual
   source code.

   The output from __repr__ looks like this::

      gcc.Location(file='./src/test.c', line=42)

   The output from__str__  looks like this::

      ./src/test.c:42

   .. py:attribute:: file

      (string) Name of the source file (or header file)

   .. py:attribute:: line

      (int) Line number within source file (starting at 1, not 0)

   .. py:attribute:: column

      (int) Column number within source file  (starting at 1, not 0)

   .. py:attribute:: in_system_header

      (bool) This attribute flags locations that are within a system header
      file.  It may be of use when writing custom warnings, so that you
      can filter out issues in system headers, leaving just those within
      the user's code::

         # Don't report on issues found in system headers:
         if decl.location.in_system_header:
             return

   From GCC 6 onwards, these values can represent both a caret and a range,
   e.g.::

      a = (foo && bar)
          ~~~~~^~~~~~~

   .. py:attribute:: caret

      (:py:class:`gcc.Location`) The caret location within this location.
      In the above example, the caret is on the first '&' character.

   .. py:attribute:: start

      (:py:class:`gcc.Location`) The start location of this range.
      In the above example, the start is on the opening parenthesis.

   .. py:attribute:: start

      (:py:class:`gcc.Location`) The finish location of this range.
      In the above example, the finish is on the closing parenthesis.

.. py:class:: gcc.RichLocation

   Wrapper around GCC's `rich_location`, representing one or more locations
   within the source code, and zero or more fix-it hints.

   .. method:: add_fixit_replace(self, new_content)

      Add a fix-it hint, suggesting replacement of the content covered
      by range 0 of the rich location with new_content.
