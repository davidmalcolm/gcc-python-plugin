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

Whole-program Analysis via Link-Time Optimization (LTO)
=======================================================
You can enable GCC's "link time optimization" feature by passing `-flto`.

When this is enabled, gcc adds extra sections to the compiled .o file
containing the SSA-Gimple internal representation of every function, so that
this SSA representation is available at link-time.  This allows gcc to inline
functions defined in one source file into functions defined in another
source file at link time.

Although the feature is intended for optimization, we can also use it for
code analysis, and it's possible to run the Python plugin at link time.

This means we can do interprocedural analysis across multiple source files.

.. warning:: Running a gcc plugin from inside link-time optimization is
   rather novel, and you're more likely to run into bugs.  See e.g.
   http://gcc.gnu.org/bugzilla/show_bug.cgi?id=54962

An invocation might look like this:

.. code-block:: bash

  gcc \
     -flto \
     -flto-partition=none \
     -v \
     -fplugin=PATH/TO/python.so \
     -fplugin-arg-python-script=PATH/TO/YOUR/SCRIPT.py \
     INPUT-1.c \
     INPUT-2.c \
     ...
     INPUT-n.c

Looking at the above options in turn:

  * `-flto` enables link-time optimization

  * `-flto-partition=none` : by default, gcc with LTO partitions the code
    and generates summary information for each partition, then combines the
    results of the summaries (known as "WPA" and "LTRANS" respectively).
    This appears to be of use for optimization, but to get at the function
    bodies, for static analysis, you should pass this option, which instead
    gathers all the code into one process.

  * `-v` means "verbose" and is useful for seeing all of the subprograms
    that gcc invokes, along with their command line options.  Given the
    above options, you should see invocations of `cc1` (the C compiler),
    `collect2` (the linker) and `lto1` (the link-time optimizer).

For example,

.. code-block:: bash

   $ ./gcc-with-python \
     examples/show-lto-supergraph.py \
     -flto \
     -flto-partition=none \
     tests/examples/lto/input-*.c

will render a bitmap of the supergraph like this:

    .. figure:: sample-supergraph.png
      :scale: 50 %
      :alt: image of a supergraph

.. py:function:: gcc.is_lto()

   :rtype: bool

   Determine whether or not we're being invoked during link-time
   optimization (i.e. from within the `lto1` program)

   .. warning:: The underlying boolean is not set up until passes are being
      invoked: it is always `False` during the initial invocation of the
      Python script.

