Basic usage of the plugin
=========================

The process for building and installing the plugin is still a bit messy; you'll
need to read the Makefile and use your own judgement.


You can invoke a Python script like this::

  gcc -fplugin=python.so -fplugin-arg-python-script=PATH_TO_SCRIPT.py OTHER_ARGS

and have it run your script as the plugin starts up.  However at the moment
you have to supply absolute paths to the plugin, and to the script.  (There's
also a gccutil.py, and you have to set PYTHONPATH for the plugin to be able to
find it).

The exact API is still in flux; you can currently connect to events by
registering callbacks e.g. to be called for each function in the source at
different passes.

It exposes GCC's various types as Python objects, within a "gcc" module.  You
can see the API by running::

    import gcc
    help(gcc)

Accessing parameters
--------------------

.. py:data:: argument_dict

   Exposes the arguments passed to the plugin as a dictionary.

   For example, running::

      gcc -fplugin=python.so -fplugin-arg-python-script=script.py -fplugin-arg-python-foo=bar

   with script.py containing::

      import gcc
      print(gcc.argument_dict)

   has output::

      {'script': 'test.py', 'foo': 'bar'}

.. py:data:: argument_tuple


  Exposes the arguments passed to the plugin as a tuple of (key, value) pairs,
  so you have ordering.  (Probably worth removing, and replacing
  :py:data:`argument_dict` with an OrderedDict instead)

Wiring up callbacks
-------------------

Hopefully we'll eventually have the ability to write new GCC passes in Python.
In the meantime, the main way to write scripts is to register callback functions
to be called when various events happen during compilation, such as using
:py:data::`gcc.PLUGIN_PASS_EXECUTION` to piggyback off of an existing GCC pass.

.. py:function:: gcc.register_callback

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

The various events are exposed as constants within the `gcc` module and
directly wrap GCC's plugin mechanism.  The exact arguments you get aren't
well-documented there, and may be subject to change.  I've tried to document
what I've seen in GCC 4.6 here, but it's worth experimenting and printing args
and kwargs as shown above.

Currently useful callback events
--------------------------------

.. py:data:: gcc.PLUGIN_PASS_EXECUTION

   Called when GCC runs one of its passes on a function

   Arguments passed to the callback are:

      (`ps`, `fun`, `*extraargs`)

   where `ps` is a :py:class:`gcc.Pass` and `fun` is a :py:class:`gcc.Function`.
   Your callback will typically be called many times: there are many passes,
   and each can be invoked zero or more times per function (in the code bein
   compiled)

.. py:data:: gcc.PLUGIN_PRE_GENERICIZE

   Arguments passed to the callback are:

      (`fndecl`, `*extraargs`)

   where `fndecl` is a :py:class:`gcc.Tree` representing a function declaration
   within the source code being compiled.

Other callback events
---------------------

The following may need work before they're meaningfully usable from Python
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

.. py:data:: gcc.PLUGIN_FINISH_UNIT

    gcc_data=0x0
    Called from: compile_file () at ../../gcc/toplev.c:668

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
