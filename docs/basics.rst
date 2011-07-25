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

.. For notes on how to document Python in RST form, see e.g.:
.. http://sphinx.pocoo.org/domains.html#the-python-domain

.. py:currentmodule:: gcc

Basic usage of the plugin
=========================

To build the plugin, run:

.. code-block:: bash

   make plugin

To build the plugin and run the selftests, run:

.. code-block:: bash

   make

You can also use::

   make demo

to demonstrate the new compiler errors.

There isn't a well-defined process yet for installing the plugin (though the
rpm specfile in the source tree contains some work-in-progress towards this).

Some notes on GCC plugins can be seen at http://gcc.gnu.org/wiki/plugins and
http://gcc.gnu.org/onlinedocs/gccint/Plugins.html

Once you've built the plugin, you can invoke a Python script like this:

.. code-block:: bash

  gcc -fplugin=python.so -fplugin-arg-python-script=PATH_TO_SCRIPT.py OTHER_ARGS

and have it run your script as the plugin starts up.

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

  ./gcc-with-python show-ssa.py test.c


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


Accessing parameters
--------------------

.. py:data:: argument_dict

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

.. py:data:: argument_tuple


  Exposes the arguments passed to the plugin as a tuple of (key, value) pairs,
  so you have ordering.  (Probably worth removing, and replacing
  :py:data:`argument_dict` with an OrderedDict instead; what about
  duplicate args though?)

Wiring up callbacks
-------------------

Hopefully we'll eventually have the ability to write new GCC passes in Python.
In the meantime, the main way to write scripts is to register callback functions
to be called when various events happen during compilation, such as using
:py:data:`gcc.PLUGIN_PASS_EXECUTION` to piggyback off of an existing GCC pass.

.. py:function:: gcc.register_callback(event_id, function, [extraargs,] **kwargs)

   Wire up a python function as a callback.  It will be called when the given
   event occurs during compilation.  For some events, the callback will be
   called just once; for other events, the callback is called once per
   function within the source code being compiled.  In the latter case, the
   plugin passes a :py:class:`gcc.Function` instance as a parameter to your
   callback, so that you can work on it::

     def my_pass_execution_callback(*args, **kwargs):
          print('my_pass_execution_callback was called: args=%r  kwargs=%r'
	        % (args, kwargs))

     import gcc
     gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                           my_pass_execution_callback)

   You can pass additional arguments when registering the callback - they will
   be passed to the callback after any normal arguments.  This is denoted in the
   descriptions of events below by `*extraargs`.

   You can also supply keyword arguments: they will be passed on as keyword
   arguments to the callback.  This is denoted in the description of events
   below by `**kwargs`.

The various events are exposed as constants within the `gcc` module and
directly wrap GCC's plugin mechanism.  The exact arguments you get aren't
well-documented there, and may be subject to change.  I've tried to document
what I've seen in GCC 4.6 here, but it's worth experimenting and printing args
and kwargs as shown above.

If an exception occurs during a callback, and isn't handled by a try/except
before returning into the plugin, the plugin prints the traceback to stderr and
treats it as an error:

.. code-block:: pytb

  /home/david/test.c: In function ‘main’:
  /home/david/test.c:28:1: error: Unhandled Python exception raised within callback
  Traceback (most recent call last):
    File "test.py", line 38, in my_pass_execution_callback
      dot = gccutils.tree_to_dot(fun)
  NameError: global name 'gccutils' is not defined

Currently useful callback events
--------------------------------

.. py:data:: gcc.PLUGIN_PASS_EXECUTION

   Called when GCC runs one of its passes on a function

   Arguments passed to the callback are:

      (`ps`, `fun`, `*extraargs`, `**kwargs`)

   where `ps` is a :py:class:`gcc.Pass` and `fun` is a :py:class:`gcc.Function`.
   Your callback will typically be called many times: there are many passes,
   and each can be invoked zero or more times per function (in the code being
   compiled)

.. py:data:: gcc.PLUGIN_PRE_GENERICIZE

   Arguments passed to the callback are:

      (`fndecl`, `*extraargs`, `**kwargs`)

   where `fndecl` is a :py:class:`gcc.Tree` representing a function declaration
   within the source code being compiled.

.. py:data:: gcc.PLUGIN_FINISH_UNIT

   Called when GCC has finished compiling a particular translation unit.

   Arguments passed to the callback are:

      (`*extraargs`, `**kwargs`)

.. Other callback events
   ---------------------

.. (Commented out for now; probably should finish this and move it to a
   reference section)

.. The following may need work before they're meaningfully usable from Python
   scripts:

   .. py:data:: gcc.PLUGIN_ATTRIBUTES

   Called from: init_attributes () at ../../gcc/attribs.c:187
    However, it seems at this point to have initialized these::

      static const struct attribute_spec *attribute_tables[4];
      static htab_t attribute_hash;

   .. py:data:: gcc.PLUGIN_PRAGMAS

    gcc_data=0x0
    Called from: c_common_init () at ../../gcc/c-family/c-opts.c:1052

   .. py:data:: gcc.PLUGIN_START_UNIT

    gcc_data=0x0
    Called from: compile_file () at ../../gcc/toplev.c:573

   .. py:data:: gcc.PLUGIN_PRE_GENERICIZE

    gcc_data is:  tree fndecl;
    Called from: finish_function () at ../../gcc/c-decl.c:8323

   .. py:data:: gcc.PLUGIN_OVERRIDE_GATE

    gcc_data::

      &gate_status
      bool gate_status;

    Called from : execute_one_pass (pass=0x1011340) at ../../gcc/passes.c:1520

   .. py:data:: gcc.PLUGIN_ALL_IPA_PASSES_START

    gcc_data=0x0
    Called from: ipa_passes () at ../../gcc/cgraphunit.c:1779

   .. py:data:: gcc.PLUGIN_EARLY_GIMPLE_PASSES_START

    gcc_data=0x0
    Called from: execute_ipa_pass_list (pass=0x1011fa0) at ../../gcc/passes.c:1927

   .. py:data:: gcc.PLUGIN_EARLY_GIMPLE_PASSES_END

    gcc_data=0x0
    Called from: execute_ipa_pass_list (pass=0x1011fa0) at ../../gcc/passes.c:1930

   .. py:data:: gcc.PLUGIN_ALL_IPA_PASSES_END

    gcc_data=0x0
    Called from: ipa_passes () at ../../gcc/cgraphunit.c:1821

   .. py:data:: gcc.PLUGIN_ALL_PASSES_START

    gcc_data=0x0
    Called from: tree_rest_of_compilation (fndecl=0x7ffff16b1f00) at ../../gcc/tree-optimize.c:420

   .. py:data:: gcc.PLUGIN_ALL_PASSES_END

    gcc_data=0x0
    Called from: tree_rest_of_compilation (fndecl=0x7ffff16b1f00) at ../../gcc/tree-optimize.c:425

   .. py:data:: gcc.PLUGIN_FINISH

    gcc_data=0x0
    Called from: toplev_main (argc=17, argv=0x7fffffffdfc8) at ../../gcc/toplev.c:1970

   .. py:data:: gcc.PLUGIN_FINISH_TYPE

    gcc_data=tree
    Called from c_parser_declspecs (parser=0x7fffef559730, specs=0x15296d0, scspec_ok=1 '\001', typespec_ok=1 '\001', start_attr_ok=<optimized out>, la=cla_nonabstract_decl) at ../../gcc/c-parser.c:2111

   .. py:data:: gcc.PLUGIN_PRAGMA

    gcc_data=0x0
    Called from: init_pragma at ../../gcc/c-family/c-pragma.c:1321
    to  "Allow plugins to register their own pragmas."

Generating custom errors and warnings
=====================================

.. py:function:: gcc.warning(location, option, message)

   Emits a compiler warning at the given :py:class:`gcc.Location`.

   The warning is controlled by the given :py:class:`gcc.Option`.

   For example, given this Python code::

      gcc.warning(func.start, gcc.Option('-Wformat'), 'Incorrect formatting')

   if the given warning is enabled, a warning will be printed to stderr:

   .. code-block:: bash

      $ ./gcc-with-python script.py input.c
      input.c:25:1: warning: incorrect formatting [-Wformat]

   If the given warning is being treated as an error (through the usage
   of `-Werror`), then an error will be printed:

   .. code-block:: bash

      $ ./gcc-with-python -Werror script.py input.c
      input.c:25:1: error: incorrect formatting [-Werror=format]
      cc1: all warnings being treated as errors

   .. code-block:: bash

      $ ./gcc-with-python -Werror=format script.py input.c
      input.c:25:1: error: incorrect formatting [-Werror=format]
      cc1: some warnings being treated as errors

   If the given warning is disabled, the warning will not be printed:

   .. code-block:: bash

      $ ./gcc-with-python -Wno-format script.py input.c

   .. note:: Due to the way GCC implements some options, it's not always
      possible for the plugin to fully disable some warnings.  See
      :py:attr:`gcc.Option.is_enabled` for more information.

   The function returns a boolean, indicating whether or not anything was
   actually printed.

.. py:function:: gcc.error(location, message)

   Emits a compiler error at the given :py:class:`gcc.Location`.

   For example::

      gcc.error(func.start, 'something bad was detected')

   would lead to this error being printed to stderr:

   .. code-block:: bash

     $ ./gcc-with-python script.py input.c
     input.c:25:1: error: something bad was detected

.. py:function:: gcc.permerror(loc, str)

   This is a wrapper around GCC's `permerror` function.

   Expects an instance of :py:class:`gcc.Location` (not None) and a string

   Emit a "permissive" error at that location, intended for things that really
   ought to be errors, but might be present in legacy code.

   In theory it's suppressable using "-fpermissive" at the GCC command line
   (which turns it into a warning), but this only seems to be legal for C++
   source files.

   Returns True if the warning was actually printed, False otherwise

.. py:function:: gcc.inform(loc, str)

   This is a wrapper around GCC's `inform` function.

   Expects an instance of :py:class:`gcc.Location` (not None) and a string

   Emit an informational message at that location.

   For example::

     gcc.inform(stmt.loc, 'this is where X was defined')

   would lead to this informational message being printed to stderr:

   .. code-block:: bash

     $ ./gcc-with-python script.py input.c
     input.c:23:3: note: this is where X was defined

Global data access
==================

.. py:function:: gcc.get_variables()

      Get all variables in this compilation unit as a list of
      :py:class:`gcc.Variable`

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

      .. note::

         This function is only available when the plugin is built against
	 gcc 4.6 and later, not in 4.5

      .. py:class:: gcc.TranslationUnitDecl

         Subclass of :py:class:`gcc.Tree` representing a compilation unit

	    .. py:attribute:: block

               The :py:class:`gcc.Block` representing global scope within this
               source file.

	    .. py:attribute:: language

	       The source language of this translation unit, as a string
	       (e.g. "GNU C")

.. py:function:: gccutils.get_global_typedef(name)

      Given a string `name`, look for a C/C++ `typedef` in global scope with
      that name, returning it as a :py:class:`gcc.TypeDecl`, or None if it
      wasn't found

      .. note::

         This function is only available when the plugin is built against
	 gcc 4.6 and later, not in 4.5

.. py:function:: gccutils.get_global_vardecl_by_name(name)

      Given a string `name`, look for a C/C++ variable in global scope with
      that name, returning it as a :py:class:`gcc.VarDecl`, or None if it
      wasn't found

      .. note::

         This function is only available when the plugin is built against
	 gcc 4.6 and later, not in 4.5

.. py:function:: gccutils.get_field_by_name(decl, name)

      Given one of a :py:class:`gcc.RecordType`, :py:class:`gcc.UnionType`, or
      :py:class:`gcc.QualUnionType`, along with a string `name`, look for a
      field with that name within the given struct or union, returning it as a
      :py:class:`gcc.FieldDecl`, or None if it wasn't found


Working with source code
========================

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
