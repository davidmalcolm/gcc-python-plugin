Working with the preprocessor
=============================

For languages that support a preprocessor, it's possible to inject new
"built-in" macros into the compilation from a Python script.

The motivation for this is to better support the creation of custom
attributes, by creating preprocessor names that can be tested against.

.. py:function:: gcc.define_macro(argument)

   Defines a preprocessor macro with the given argument, which may be
   of use for code that needs to test for the presence of your script.
   The argument can either be a simple name, or a name with a
   definition:

   .. code-block:: python

      gcc.define_macro("SOMETHING")  # define as the empty string
      gcc.define_macro("SOMETHING=72")

   This function can only be called from within specific event callbacks,
   since it manipulates the state of the preprocessor for a given source
   file.

   For now, only call it in a handler for the event `gcc.PLUGIN_ATTRIBUTES`:

   .. literalinclude:: ../tests/examples/attributes-with-macros/script.py
    :lines: 18-
    :language: python


