.. Copyright 2011 David Malcolm <dmalcolm@redhat.com>
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

Working with C code
===================

"Hello world"
-------------

Here's a simple "hello world" C program:

  .. literalinclude:: ../tests/examples/hello-world/input.c
    :lines: 19-26
    :language: c

Here's a Python script that locates the function at one pass within the
compile  and prints various interesting things about it:

  .. literalinclude:: ../tests/examples/hello-world/script.py
    :lines: 19-
    :language: python

We can run the script during the compile like this:

   .. code-block:: bash

     ./gcc-with-python script.py test.c

Here's the expected output:

  .. literalinclude:: ../tests/examples/hello-world/stdout.txt

Notice how the call to `printf` has already been optimized into a call
to `__builtin_puts`.


Spell-checking string constants within source code
--------------------------------------------------

This example add a spell-checker pass to GCC: all string constants are run through the "enchant" spelling-checker:

   .. code-block:: bash

     $ ./gcc-with-python tests/examples/spelling-checker/script.py input.c

The Python code for this is:

   .. literalinclude:: ../tests/examples/spelling-checker/script.py
    :lines: 18-
    :language: python

Given this sample C source file:

  .. literalinclude:: ../tests/examples/spelling-checker/input.c
    :lines: 19-29
    :language: c

these warnings are emitted on stderr:

  .. literalinclude:: ../tests/examples/spelling-checker/stderr.txt
