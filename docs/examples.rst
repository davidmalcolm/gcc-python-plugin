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

Example scripts
===============

There are various sample scripts located in the `examples` subdirectory.

Once you've built the plugin (with `make`), you can run them via:

   .. code-block:: bash

      $ ./gcc-with-python examples/NAME-OF-SCRIPT.py test.c

`show-docs.py`
--------------

  A trivial script to make it easy to read the builtin documentation for the
  gcc API:

   .. code-block:: bash

     $ ./gcc-with-python examples/show-docs.py test.c

  with this source:

   .. literalinclude:: ../examples/show-docs.py
    :lines: 17-
    :language: python

  giving output::

     Help on built-in module gcc:

     NAME
         gcc

     FILE
         (built-in)

     CLASSES
         __builtin__.object
             BasicBlock
             Cfg
             Edge
             Function
             Gimple
     (truncated)

`show-passes.py`
----------------

You can see the passes being executed via:

   .. code-block:: bash

     $ ./gcc-with-python examples/show-passes.py test.c

This is a simple script that registers a trivial callback:

   .. literalinclude:: ../examples/show-passes.py
    :lines: 17-
    :language: python

Sample output, showing passes being called on two different functions (`main`
and `helper_function`)::

     (gcc.GimplePass(name='*warn_unused_result'), gcc.Function('main'))
     (gcc.GimplePass(name='omplower'), gcc.Function('main'))
     (gcc.GimplePass(name='lower'), gcc.Function('main'))
     (gcc.GimplePass(name='eh'), gcc.Function('main'))
     (gcc.GimplePass(name='cfg'), gcc.Function('main'))
     (gcc.GimplePass(name='*warn_function_return'), gcc.Function('main'))
     (gcc.GimplePass(name='*build_cgraph_edges'), gcc.Function('main'))
     (gcc.GimplePass(name='*warn_unused_result'), gcc.Function('helper_function'))
     (gcc.GimplePass(name='omplower'), gcc.Function('helper_function'))
     (gcc.GimplePass(name='lower'), gcc.Function('helper_function'))
     (gcc.GimplePass(name='eh'), gcc.Function('helper_function'))
     (gcc.GimplePass(name='cfg'), gcc.Function('helper_function'))
     [...truncated...]


`show-gimple.py`
----------------

A simple script for viewing each function in the source file after it's been
converted to "GIMPLE" form, using GraphViz to visualize the control flow graph:

   .. code-block:: bash

      $ ./gcc-with-python examples/show-gimple.py test.c

It will generate a file `test.png` for each function, and opens it in an image
viewer.

   .. figure:: sample-gimple-cfg.png
      :scale: 50 %
      :alt: image of a control flow graph in GIMPLE form

The Python code for this is:

   .. literalinclude:: ../examples/show-gimple.py
    :lines: 19-
    :language: python

`show-ssa.py`
-------------

This is similar to `show-gimple.py`, but shows each function after the GIMPLE
has been converted to Static Single Assignment form ("SSA"):

   .. code-block:: bash

     $ ./gcc-with-python examples/show-ssa.py test.c

As before, it generates an image file for each function and opens it in a
viewer.

.. figure:: sample-gimple-ssa-cfg.png
   :scale: 50 %
   :alt: image of a control flow graph in GIMPLE SSA form

The Python code for this is:

   .. literalinclude:: ../examples/show-ssa.py
    :lines: 17-
    :language: python
