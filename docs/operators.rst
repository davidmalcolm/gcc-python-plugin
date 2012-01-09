.. Copyright 2012 David Malcolm <dmalcolm@redhat.com>
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

:py:class:`gcc.Tree` operators by symbol
----------------------------------------

.. _get_symbols:

The following shows the symbol used for each expression subclass in debug
dumps, as returned by the various `get_symbol()` class methods.

There are some duplicates (e.g. `-` is used for both :py:class:`gcc.MinusExpr`
as an infix binary operator, and by :py:class:`gcc.NegateExpr` as a prefixed
unary operator).

.. include:: ../tests/plugin/expressions/get_symbol/stdout.txt
