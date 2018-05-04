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

.. For notes on how to document Python in RST form, see e.g.:
.. http://sphinx.pocoo.org/domains.html#the-python-domain

Requirements
============

The plugin has the following requirements:

  * GCC: 4.6 or later (it uses APIs that weren't exposed to plugins in 4.5)

  * Python: requires 2.7 or 3.2 or later

  * "six": The libcpychecker code uses the "six" Python compatibility library to
    smooth over Python 2 vs Python 3 differences, both at build-time and
    run-time:

       http://pypi.python.org/pypi/six/

  * "pygments": The libcpychecker code uses the "pygments" Python
    syntax-highlighting library when writing out error reports:

       http://pygments.org/

  * "lxml": The libcpychecker code uses the "lxml" internally when writing
    out error reports.

  * graphviz: many of the interesting examples use "dot" to draw diagrams
    (e.g. control-flow graphs), so it's worth having graphviz installed.

Prebuilt-packages
=================

Various distributions ship with pre-built copies of the plugin.  If you're
using Fedora, you can install the plugin via RPM on Fedora 16 onwards using:

.. code-block:: bash

   yum install gcc-python2-plugin

as root for the Python 2 build of the plugin, or:

.. code-block:: bash

   yum install gcc-python3-plugin

for the Python 3 build of the plugin.

On Gentoo, use `layman` to add the `dMaggot` overlay and `emerge` the
`gcc-python-plugin` package. This will build the plugin for Python 2 and
Python 3 should you have both of them installed in your system. A live
ebuild is also provided to install the plugin from git sources.

Building the plugin from source
===============================

Build-time dependencies
-----------------------
If you plan to build the plugin from scratch, you'll need the build-time
dependencies.

On a Fedora box you can install them by running the following as root:

.. code-block:: bash

   yum install gcc-plugin-devel python-devel python-six python-pygments graphviz

for building against Python 2, or:

.. code-block:: bash

   yum install gcc-plugin-devel python3-devel python3-six python3-pygments graphviz

when building for Python 3.

Building the code
------------------
You can obtain the source code from git by using::

   $ git clone git@github.com:davidmalcolm/gcc-python-plugin.git

To build the plugin, run:

.. code-block:: bash

   make plugin

To build the plugin and run the selftests, run:

.. code-block:: bash

   make

You can also use::

   make demo

to demonstrate the new compiler errors.

By default, the `Makefile` builds the plugin using the first ``python-config``
tool found in `$PATH` (e.g. `/usr/bin/python-config`), which is typically the
system copy of Python 2.  You can override this (e.g. to build against
Python 3) by overriding the `PYTHON` and `PYTHON_CONFIG` Makefile variables
with:

.. code-block:: bash

   make PYTHON=python3 PYTHON_CONFIG=python3-config

There isn't a well-defined process yet for installing the plugin (though the
rpm specfile in the source tree contains some work-in-progress towards this).

Some notes on GCC plugins can be seen at http://gcc.gnu.org/wiki/plugins and
http://gcc.gnu.org/onlinedocs/gccint/Plugins.html

.. note:: Unfortunately, the layout of the header files for GCC plugin
   development has changed somewhat between different GCC releases.  In
   particular, older builds of GCC flattened the "c-family" directory in the
   installed plugin headers.

   This was fixed in this GCC commit:

      http://gcc.gnu.org/viewcvs?view=revision&revision=176741

   So if you're using an earlier build of GCC using the old layout you'll need
   to apply the following patch (reversed with "-R") to the plugin's source
   tree to get it to compile:

   .. code-block:: bash

      $ git show 215730cbec40a6fe482fabb7f1ecc3d747f1b5d2 | patch -p1 -R

   If you have a way to make the plugin's source work with either layout,
   please email the plugin's `mailing list
   <https://fedorahosted.org/mailman/listinfo/gcc-python-plugin/>`_

Basic usage of the plugin
=========================

Once you've built the plugin, you can invoke a Python script like this:

.. code-block:: bash

  gcc -fplugin=./python.so -fplugin-arg-python-script=PATH_TO_SCRIPT.py OTHER_ARGS

and have it run your script as the plugin starts up.

Alternatively, you can run a one-shot Python command like this:

.. code-block:: bash

  gcc -fplugin=./python.so -fplugin-arg-python-command="python code" OTHER_ARGS

such as:

.. code-block:: bash

  gcc -fplugin=./python.so -fplugin-arg-python-command="import sys; print(sys.path)" OTHER_ARGS

The plugin automatically adds the absolute path to its own directory to the
end of its `sys.path`, so that it can find support modules, such as gccutils.py
and `libcpychecker`.

There is also a helper script, `gcc-with-python`, which expects a python script
as its first argument, then regular gcc arguments:

.. code-block:: bash

  ./gcc-with-python PATH_TO_SCRIPT.py other args follow

For example, this command will use graphviz to draw how GCC "sees" the
internals of each function in `test.c` (within its SSA representation):

.. code-block:: bash

  ./gcc-with-python examples/show-ssa.py test.c


Most of the rest of this document describes the Python API visible for
scripting.

The plugin GCC's various types as Python objects, within a "gcc" module.  You
can see the API by running the following within a script::

    import gcc
    help(gcc)

To make this easier, there's a script to do this for you:

.. code-block:: bash

  ./gcc-python-docs

from where you can review the built-in documentation strings (this document
may be easier to follow though).

The exact API is still in flux: and may well change (this is an early version
of the code; we may have to change things as GCC changes in future releases
also).


Debugging your script
---------------------

You can place a forced breakpoint in your script using this standard Python
one-liner::

   import pdb; pdb.set_trace()

If Python reaches this location it will interrupt the compile and put you
within the `pdb` interactive debugger, from where you can investigate.

See http://docs.python.org/library/pdb.html#debugger-commands for more
information.


If an exception occurs during Python code, and isn't handled by a try/except
before returning into the plugin, the plugin prints the traceback to stderr and
treats it as an error:

.. code-block:: pytb

  /home/david/test.c: In function ‘main’:
  /home/david/test.c:28:1: error: Unhandled Python exception raised within callback
  Traceback (most recent call last):
    File "test.py", line 38, in my_pass_execution_callback
      dot = gccutils.tree_to_dot(fun)
  NameError: global name 'gccutils' is not defined

(In this case, it was a missing `import` statement in the script)

GCC reports errors at a particular location within the source code.  For an
unhandled exception such as the one above, by default, the plugin reports
the error as occurring as the top of the current source function (or the last
location within the current source file for passes and callbacks that aren't
associated with a function).

You can override this using gcc.set_location:

.. py:function:: gcc.set_location(loc)

   Temporarily overrides the error-reporting location, so that if an exception
   occurs, it will use this `gcc.Location`, rather than the default.  This may
   be of use when debugging tracebacks from scripts.  The location is reset
   each time after returning from Python back to the plugin, after printing
   any traceback.


Accessing parameters
--------------------

.. py:data:: gcc.argument_dict

   Exposes the arguments passed to the plugin as a dictionary.

   For example, running:

   .. code-block:: bash

      gcc -fplugin=python.so \
          -fplugin-arg-python-script=test.py \
          -fplugin-arg-python-foo=bar

   with `test.py` containing::

      import gcc
      print(gcc.argument_dict)

   has output::

      {'script': 'test.py', 'foo': 'bar'}

.. py:data:: gcc.argument_tuple


  Exposes the arguments passed to the plugin as a tuple of (key, value) pairs,
  so you have ordering.  (Probably worth removing, and replacing
  :py:data:`argument_dict` with an OrderedDict instead; what about
  duplicate args though?)

Adding new passes to the compiler
---------------------------------
You can create new compiler passes by subclassing the appropriate
:py:class:`gcc.Pass` subclasss.  For example, here's how to wire up a new pass
that displays the control flow graph of each function:

   .. literalinclude:: ../examples/show-gimple.py
    :lines: 19-
    :language: python

For more information, see :ref:`creating-new-passes`

Wiring up callbacks
-------------------

The other way to write scripts is to register callback functions
to be called when various events happen during compilation, such as using
:py:data:`gcc.PLUGIN_PASS_EXECUTION` to piggyback off of an existing GCC pass.

   .. literalinclude:: ../examples/show-passes.py
    :lines: 19-
    :language: python

For more information, see :ref:`callbacks`

Global data access
==================

.. py:function:: gcc.get_variables()

      Get all variables in this compilation unit as a list of
      :py:class:`gcc.Variable`

.. py:class:: gcc.Variable

   Wrapper around GCC's `struct varpool_node`, representing a variable in
   the code being compiled.

   .. py:attribute:: decl

      The declaration of this variable, as a :py:class:`gcc.Tree`

.. py:function:: gccutils.get_variables_as_dict()

      Get a dictionary of all variables, where the keys are the variable names
      (as strings), and the values are instances of :py:class:`gcc.Variable`

.. py:function:: gcc.maybe_get_identifier(str)

      Get the :py:class:`gcc.IdentifierNode` with this name, if it exists,
      otherwise None.  (However, after the front-end has run, the identifier
      node may no longer point at anything useful to you; see
      :py:func:`gccutils.get_global_typedef` for an example of working
      around this)

.. py:function:: gcc.get_translation_units()

      Get a list of all :py:class:`gcc.TranslationUnitDecl` for the compilation
      units within this invocation of GCC (that's "source code files" for the
      layperson).

      .. py:class:: gcc.TranslationUnitDecl

         Subclass of :py:class:`gcc.Tree` representing a compilation unit

	    .. py:attribute:: block

               The :py:class:`gcc.Block` representing global scope within this
               source file.

	    .. py:attribute:: language

	       The source language of this translation unit, as a string
	       (e.g. "GNU C")

.. py:function:: gcc.get_global_namespace()

      C++ only: locate the :py:class:`gcc.NamespaceDecl` for the global
      namespace (a.k.a. "::")

.. py:function:: gccutils.get_global_typedef(name)

      Given a string `name`, look for a C/C++ `typedef` in global scope with
      that name, returning it as a :py:class:`gcc.TypeDecl`, or None if it
      wasn't found

.. py:function:: gccutils.get_global_vardecl_by_name(name)

      Given a string `name`, look for a C/C++ variable in global scope with
      that name, returning it as a :py:class:`gcc.VarDecl`, or None if it
      wasn't found

.. py:function:: gccutils.get_field_by_name(decl, name)

      Given one of a :py:class:`gcc.RecordType`, :py:class:`gcc.UnionType`, or
      :py:class:`gcc.QualUnionType`, along with a string `name`, look for a
      field with that name within the given struct or union, returning it as a
      :py:class:`gcc.FieldDecl`, or None if it wasn't found
