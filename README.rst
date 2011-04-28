gcc-python
==========

This is a plugin for GCC, which links against libpython, and (I hope) allows
you to invoke arbitrary Python scripts from inside the compiler.  The aim is to
allow you to write GCC plugins in Python.

It's still at the "experimental proof-of-concept stage"; expect crashes and
tracebacks (I'm new to insides of GCC, and I may have misunderstood things).

It's already possible to use this to add additional compiler errors/warnings,
e.g. domain-specific checks, or static analysis.  One of my goals for this is
to "teach" GCC about the common mistakes people make when writing extensions
for CPython, but it could be used e.g. to teach GCC about GTK's
reference-counting semantics, or about locking in the Linux kernel, or about
signal-safety in APIs.

Other ideas include visualizations of code structure.   Given a `gcc.CFG`
instance, `gccutils.render_to_dot(cfg)` and `gccutils.invoke_dot(cfg)` will
use graphviz and eog to plot a handy visualization of a control flow graph,
showing the source code interleaved with GCC's ``GIMPLE`` internal
representation.


Usage
-----
I use::

    make

to run the tests, which finishes by running ``make demo``, which expects to
fail, demonstrating the new compiler errors.

All of my coding so far has been on Fedora 15 x86_64, using::

    gcc-plugin-devel-4.6.0-0.15.fc15.x86_64

and I don't know to what extent it will be compatible with other versions and
architectures.

The code also makes some assumptions about the Python version you have
installed (grep for "PyRuntime" in the .py files).  I've been using::

    python-devel-2.7.1-5.fc15.x86_64
    python-debug-2.7.1-5.fc15.x86_64
    python3-debug-3.2-0.9.rc1.fc15.x86_64
    python3-devel-3.2-0.9.rc1.fc15.x86_64

but you may have to hack up the `PyRuntime()` invocations in the code to get
it to build on other machines.

There isn't an installer yet.  In theory you should be able to add these
arguments to the gcc invocation::

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

from within a script.


Overview of the code
--------------------
This is currently three projects in one:

gcc-python-*: the plugin for GCC.  The entrypoint (`init_plugin`) is in
gcc-python.c

cpychecker: a script written for the plugin, in which I'm building new compiler
warnings to help people write CPython extension code.

cpybuilder: a handy module for programatically generating C source code for
CPython extensions.  I use this both to generate parts of the GCC plugin, and
also in the selftests for the cpychecker script.  (I initially attempted to use
Cython for the former, but wrapping the "tree" type hierarchy required more
programatic control)

Coding style: Python and GCC each have their own coding style guide for C.
I've chosen to follow Python's (PEP-7), as I prefer it (although my code is
admittedly a mess in places).


Enjoy!
David Malcolm <dmalcolm@redhat.com>
