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

Creating custom GCC attributes
==============================

GNU C supports a non-standard `__attribute__(()) syntax
<http://gcc.gnu.org/onlinedocs/gcc/Function-Attributes.html>`_ for marking
declarations with additional information that may be of interest to the
optimizer, and for checking the correctness of the code.

The GCC Python plugin allows you to create custom attributes, which may
be of use to your scripts: you can use this to annotate C code with additional
information.  For example, you could create a custom attribute for functions
describing the interaction of a function on mutex objects:

.. code-block:: c

    extern void some_function(void)
      __attribute__((claims_mutex("io")));

    extern void some_other_function(void)
      __attribute__((releases_mutex("io")));

and use this in a custom code-checker.

Custom attributes can take string and integer parameters.  For example, the
above custom attributes take a single string parameter.  A custom attribute can
take more than one parameter, or none at all.

To create custom attributes from Python, you need to wire up a callback
response to the `gcc.PLUGIN_ATTRIBUTES` event:

   .. literalinclude:: ../tests/examples/attributes/script.py
    :lines: 39-40
    :language: python

This callback should then call :py:func:`gcc.register_attribute` to associate
the name of the attribute with a Python callback to be called when the
attribute is encountered in C code.

.. py:function:: gcc.register_attribute(name, min_length, max_length, \
                                        decl_required, type_required, \
                                        function_type_required, \
                                        callable)

   Registers a new GCC attribute with the given *name* , usable in C source
   code via ``__attribute__(())``.

   :param name: the name of the new attribute
   :type name: str
   :param min_length: the minimum number of arguments expected when the attribute is used
   :type min_length: int
   :param max_length: the maximum number of arguments expected when the
      attribute is used (-1 for no maximum)
   :type max_length: int
   :param decl_required:
   :type decl_required:
   :param type_required:
   :type type_required:
   :param function_type_required:
   :type function_type_required:
   :param callable: the callback to be invoked when the attribute is seen
   :type callable: a callable object, such as a function

In this example, we can simply print when the attribute is seen, to verify that
the callback mechanism is working:

   .. literalinclude:: ../tests/examples/attributes/script.py
    :lines: 22-36
    :language: python

Putting it all together, here is an example Python script for the plugin:

   .. literalinclude:: ../tests/examples/attributes/script.py
    :lines: 18-
    :language: python

Compiling this test C source file:

   .. literalinclude:: ../tests/examples/attributes/input.c
    :lines: 22-29
    :language: c

leads to this output from the script:

   .. literalinclude:: ../tests/examples/attributes/stdout.txt
    :language: bash

Using the preprocessor to guard attribute usage
-----------------------------------------------

Unfortunately, the above C code will only work when it is compiled with the
Python script that adds the custom attributes.

You can avoid this by using :py:func:`gcc.define_macro()` to pre-define a
preprocessor name (e.g. "WITH_ATTRIBUTE_CLAIMS_MUTEX") at the same time as when
you define the attribute:

   .. literalinclude:: ../tests/examples/attributes-with-macros/script.py
    :lines: 18-
    :language: python

This way the user can write this C code instead, and have it work both with
and without the Python script:

   .. literalinclude:: ../tests/examples/attributes-with-macros/input.c
    :lines: 22-45
    :language: c

giving this output from the script:

   .. literalinclude:: ../tests/examples/attributes-with-macros/stdout.txt
    :language: bash
