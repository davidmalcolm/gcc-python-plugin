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

.. _callbacks:

Working with callbacks
======================

One way to work with GCC from the Python plugin is via callbacks. It's possible
to register callback functions, which will be called when various events happen
during compilation.

For example, it's possible to piggyback off of an existing GCC pass by using
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

   The exact arguments passed to your callback vary: consult the documentation
   for the particular event you are wiring up to (see below).

   You can pass additional arguments when registering the callback - they will
   be passed to the callback after any normal arguments.  This is denoted in the
   descriptions of events below by `*extraargs`.

   You can also supply keyword arguments: they will be passed on as keyword
   arguments to the callback.  This is denoted in the description of events
   below by `**kwargs`.

The various events are exposed as constants within the `gcc` module and
directly wrap GCC's plugin mechanism.

The following GCC events are currently usable from the Python plugin via
:py:func:`gcc.register_callback()`:

===============================================  =========
ID                                               Meaning
===============================================  =========
:py:data:`gcc.PLUGIN_ATTRIBUTES`                 For :doc:`creating custom GCC attributes <attributes>`

:py:data:`gcc.PLUGIN_PRE_GENERICIZE`             For working with the AST in the C and C++ frontends

:py:data:`gcc.PLUGIN_PASS_EXECUTION`             Called before each pass is executed

:py:data:`gcc.PLUGIN_FINISH_UNIT`                At the end of working with a translation unit (aka source file)

:py:data:`gcc.PLUGIN_FINISH_TYPE`                After a type has been parsed

===============================================  =========

.. py:data:: gcc.PLUGIN_ATTRIBUTES

   Called when GCC is creating attributes for use with its non-standard
   `__attribute__(()) syntax
   <http://gcc.gnu.org/onlinedocs/gcc/Function-Attributes.html>`_.

   If you want to create custom GCC attributes, you should register a callback
   on this event and call :py:func:`gcc.register_attribute()` from within that
   callback, so that they are created at the same time as the GCC's built-in
   attributes.

   No arguments are passed to your callback other than those that you supply
   yourself when registering it:

      (`*extraargs`, `**kwargs`)

   See :doc:`creating custom GCC attributes <attributes>` for examples and
   more information.

.. py:data:: gcc.PLUGIN_PASS_EXECUTION

   Called when GCC is about to run one of its passes.

   Arguments passed to the callback are:

      (`ps`, `fun`, `*extraargs`, `**kwargs`)

   where `ps` is a :py:class:`gcc.Pass` and `fun` is a :py:class:`gcc.Function`.
   Your callback will typically be called many times: there are many passes,
   and each can be invoked zero or more times per function (in the code being
   compiled)

   More precisely, some passes have a "gate check": the pass first checks a
   condition, and only executes if the condition is true.

   Any callback registered with `gcc.PLUGIN_PASS_EXECUTION` will get called
   if this condition succeeds.

   The actual work of the pass is done after the callbacks return.

   In pseudocode::

     if pass.has_gate_condition:
         if !pass.test_gate_condition():
	    return
     invoke_all_callbacks()
     actually_do_the_pass()

   For passes working on individual functions, all of the above is done
   per-function.

   To connect to a specific pass, you can simply add a conditional based on the
   name of the pass::

      def my_callback(ps, fun):
          if ps.name != '*warn_function_return':
	      # Not the pass we want
	      return
	  # Do something here
	  print(fun.decl.name)

      gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                            my_callback)


.. py:data:: gcc.PLUGIN_PRE_GENERICIZE

   Arguments passed to the callback are:

      (`fndecl`, `*extraargs`, `**kwargs`)

   where `fndecl` is a :py:class:`gcc.Tree` representing a function declaration
   within the source code being compiled.

.. py:data:: gcc.PLUGIN_FINISH_UNIT

   Called when GCC has finished compiling a particular translation unit.

   Arguments passed to the callback are:

      (`*extraargs`, `**kwargs`)

The remaining GCC events aren't yet usable from the plugin; an attempt to
register a callback on them will lead to an exception being raised. Email
the `gcc-python-plugin's mailing list
<https://fedorahosted.org/mailman/listinfo/gcc-python-plugin/>`_ if you're
interested in working with these):

===============================================  =========
ID                                               Meaning
===============================================  =========
:py:data:`gcc.PLUGIN_PASS_MANAGER_SETUP`         To hook into pass manager
:py:data:`gcc.PLUGIN_FINISH`                     Called before GCC exits
:py:data:`gcc.PLUGIN_INFO`                       Information about the plugin
:py:data:`gcc.PLUGIN_GGC_START`                  For interacting with GCC's garbage collector
:py:data:`gcc.PLUGIN_GGC_MARKING`                (ditto)
:py:data:`gcc.PLUGIN_GGC_END`                    (ditto)
:py:data:`gcc.PLUGIN_REGISTER_GGC_ROOTS`         (ditto)
:py:data:`gcc.PLUGIN_REGISTER_GGC_CACHES`        (ditto)
:py:data:`gcc.PLUGIN_START_UNIT`                 Called before processing a translation unit (aka source file)
:py:data:`gcc.PLUGIN_PRAGMAS`                    For registering pragmas
:py:data:`gcc.PLUGIN_ALL_PASSES_START`           Called before the first pass of the :ref:`"all other passes" gcc.Pass catchall <all_passes>`
:py:data:`gcc.PLUGIN_ALL_PASSES_END`             Called after last pass of the :ref:`"all other passes" gcc.Pass catchall <all_passes>`
:py:data:`gcc.PLUGIN_ALL_IPA_PASSES_START`       Called before the first IPA pass
:py:data:`gcc.PLUGIN_ALL_IPA_PASSES_END`         Called after last IPA pass
:py:data:`gcc.PLUGIN_OVERRIDE_GATE`              Provides a way to disable a built-in pass
:py:data:`gcc.PLUGIN_EARLY_GIMPLE_PASSES_START`
:py:data:`gcc.PLUGIN_EARLY_GIMPLE_PASSES_END`
:py:data:`gcc.PLUGIN_NEW_PASS`
===============================================  =========

.. Notes on the other callback events

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
