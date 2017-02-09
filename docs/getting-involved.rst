.. Copyright 2012, 2017 David Malcolm <dmalcolm@redhat.com>
   Copyright 2012, 2017 Red Hat, Inc.

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

Getting Involved
================

The plugin's web site is this GitHub repository:

   https://github.com/davidmalcolm/gcc-python-plugin

The primary place for discussion of the plugin is the mailing list:
https://fedorahosted.org/mailman/listinfo/gcc-python-plugin

A pre-built version of the HTML documentation can be seen at:

http://readthedocs.org/docs/gcc-python-plugin/en/latest/index.html

The project's mailing list is here: https://fedorahosted.org/mailman/listinfo/gcc-python-plugin

Ideas for using the plugin
--------------------------

Here are some ideas for possible uses of the plugin.  Please email the
plugin's mailing list if you get any of these working (or if you have other
ideas!).  Some guesses as to the usefulness and difficulty level are given in
parentheses after some of the ideas.  Some of them might require new attributes,
methods and/or classes to be added to the plugin (to expose more of GCC
internals), but you can always ask on the mailing list if you need help.

* extend the libcpychecker code to add checking for the standard C library.
  For example, given this buggy C code:

  .. code-block:: c

    int foo() {
         FILE *src, *dst;
         src = fopen("source.txt", "r");
         if (!src) return -1;

         dst = fopen("dest.txt", "w");
         if (!dst) return -1;  /* <<<< BUG: this error-handling leaks "src" */

         /* etc, copy src to dst (or whatever) */
    }

  it would be great if the checker could emit a compile-time warning about
  the buggy error-handling path above (or indeed any paths through
  functions that leak `FILE*`, file descriptors, or other resources). The
  way to do this (I think) is to add a new `Facet` subclass to
  libcpychecker, analogous to the `CPython` facet subclass that already
  exists (though the facet handling is probably rather messy right now).
  (useful but difficult, and a lot of work)

* extend the libcpychecker code to add checking for other libraries.  For
  example:

  * reference-count checking within `glib <http://developer.gnome.org/glib/>`_
    and gobject

  (useful for commonly-used C libraries but difficult, and a lot of work)

* detection of C++ variables with non-trivial constructors that will need to be
  run before `main` - globals and static locals (useful, ought to be fairly
  easy)

* finding unused parameters in definitions of non-virtual functions, so that
  they can be removed - possibly removing further dead code.  Some care would
  be needed for function pointers.  (useful, ought to be fairly easy)

* detection of bad format strings (see e.g. https://lwn.net/Articles/478139/ )

* compile gcc's own test suite with the cpychecker code, to reuse their
  coverage of C and thus shake out more bugs in the checker (useful and easy)

* a new `PyPy gc root finder <http://pypy.readthedocs.org/en/latest/config/translation.gcrootfinder.html>`_,
  running inside GCC (useful for PyPy, but difficult)

* reimplement `GCC-XML <http://www.gccxml.org/HTML/Index.html>`_ in Python
  (probably fairly easy, but does anyone still use GCC-XML now that GCC
  supports plugins?)

* .gir generation for `GObject Introspection <http://live.gnome.org/GObjectIntrospection>`_
  (unknown if the GNOME developers are actually interested in this though)

* create an interface that lets you view the changing internal representation
  of each function as it's modified by the various optimization pases: lets
  you see which passes change a given function, and what the changes are
  (might be useful as a teaching tool, and for understanding GCC)

* add array bounds checking to C (to what extent can GCC already do this?)

* `taint mode <http://perldoc.perl.org/perlsec.html#Taint-mode>`_ for GCC!
  e.g. detect usage of data from network/from disk/etc; identify certain data
  as untrusted, and track how it gets used; issue a warning (very useful, but
  very difficult: how does untainting work? what about pointers and memory
  regions?  is it just too low-level?)

* implement something akin to PyPy's pygame-based viewer, for viewing control
  flow graphs and tree structures: an OpenGL-based GUI giving a fast,
  responsive UI for navigating the data - zooming, panning, search, etc.  (very
  useful, and fairly easy)

* `generation of pxd files for Cython
  <http://comments.gmane.org/gmane.comp.python.cython.user/5970>`_
  (useful for Cython, ought to be fairly easy)

* reverse-engineering a .py or .pyx file from a .c file: turning legacy C
  Python extension modules back into Python or Cython sources (useful but
  difficult)


Tour of the C code
------------------
The plugin's C code heavily uses Python's extension API, and so it's worth
knowing this API if you're going to hack on this part of the project.  A good
tutorial for this can be seen here:

  http://docs.python.org/extending/index.html

and detailed notes on it are here:

  http://docs.python.org/c-api/index.html

Most of the C "glue" for creating classes and registering their methods and
attributes is autogenerated.  Simple C one-liners tend to appear in the
autogenerated C files, whereas longer implementations are broken out into
a hand-written C file.

Adding new methods and attributes to the classes requires editing the
appropriate generate-\*.py script to wire up the new entrypoint.  For
very simple attributes you can embed the C code directly there, but
anything that's more than a one-liner should have its implementation in
the relevant C file.

For example, to add new methods to a :py:class:`gcc.Cfg` you'd edit:

  * `generate-cfg-c.py` to add the new methods and attributes to the relevant
    tables of callbacks

  * `gcc-python-wrappers.h` to add declarations of the new C functions

  * `gcc-python-cfg.c` to add the implementations of the new C functions

Please try to make the API "Pythonic".

My preference with getters is that if the implementation is a simple
field lookup, it should be an attribute (the "getter" is only implicit,
existing at the C level)::

   print(bb.loopcount)

whereas if getting the result involves some work, it should be an
explicit method of the class (where the "getter" is explicit at the
Python level)::

   print(bb.get_loop_count())


Using the plugin to check itself
--------------------------------
Given that the `cpychecker` code implements new error-checking for Python C
code, and that the underlying plugin is itself an example of such code, it's
possible to build the plugin once, then compile it with itself (using
CC=gcc-with-cpychecker as a Makefile variable::

  $ make CC=/path/to/a/clean/build/of/the/plugin/gcc-with-cpychecker

Unfortunately it doesn't quite compile itself cleanly right
now.

.. TODO: add notes on the current known problems


Test suite
----------
There are three test suites:

  * `testcpybuilder.py`: a minimal test suite which is used before the plugin
    itself is built.  This verifies that the `cpybuilder` code works.

  * `make test-suite` (aka `run-test-suite.py`): a test harness and suite
    which was written for this project.  See the notes below on patches.

  * `make testcpychecker` and `testcpychecker.py`: a suite based on Python's
    `unittest` module


Debugging the plugin's C code
-----------------------------

The `gcc` binary is a harness that launches subprocesses, so it can be
fiddly to debug.  Exactly what it launches depend on the inputs and
options. Typically, the subprocesses it launches are (in order):

  * `cc1` or `cc1plus`: The C or C++ compiler, generating a .s assember
    file.
  * `as`: The assembler, converting a .s assembler file to a .o object
    file.
  * `collect2`: The linker, turning one or more .o files into an executable
    (if you're going all the way to building an `a.out`-style executable).

The easiest way to debug the plugin is to add these parameters to the gcc
command line (e.g. to the end)::

   -wrapper gdb,--args

Note the lack of space between the comma and the `--args`.

e.g.::

  ./gcc-with-python examples/show-docs.py test.c -wrapper gdb,--args

This will invoke each of the subprocesses in turn under gdb: e.g. `cc1`,
`as` and `collect2`; the plugin runs with `cc1` (`cc1plus` for C++ code).

For example::

  $ ./gcc-with-cpychecker -c -I/usr/include/python2.7 demo.c -wrapper gdb,--args

  GNU gdb (GDB) Fedora 7.6.50.20130731-19.fc20
  [...snip...]
  Reading symbols from /usr/libexec/gcc/x86_64-redhat-linux/4.8.2/cc1...Reading symbols from /usr/lib/debug/usr/libexec/gcc/x86_64-redhat-linux/4.8.2/cc1.debug...done.
  done.
  (gdb) run
  [...etc...]

Another way to do it is to add "-v" to the gcc command line
(verbose), so that it outputs the commands that it's running.  You can then use
this to launch::

   $ gdb --args ACTUAL PROGRAM WITH ACTUAL ARGS

to debug the subprocess that actually loads the Python plugin.

For example::

  $ gcc -v -fplugin=$(pwd)/python.so -fplugin-arg-python-script=test.py test.c

on my machine emits this::

   Using built-in specs.
   COLLECT_GCC=gcc
   COLLECT_LTO_WRAPPER=/usr/libexec/gcc/x86_64-redhat-linux/4.6.1/lto-wrapper
   Target: x86_64-redhat-linux
   Configured with: ../configure --prefix=/usr --mandir=/usr/share/man --infodir=/usr/share/info --with-bugurl=http://bugzilla.redhat.com/bugzilla --enable-bootstrap --enable-shared --enable-threads=posix --enable-checking=release --with-system-zlib --enable-__cxa_atexit --disable-libunwind-exceptions --enable-gnu-unique-object --enable-linker-build-id --enable-languages=c,c++,objc,obj-c++,java,fortran,ada,go,lto --enable-plugin --enable-java-awt=gtk --disable-dssi --with-java-home=/usr/lib/jvm/java-1.5.0-gcj-1.5.0.0/jre --enable-libgcj-multifile --enable-java-maintainer-mode --with-ecj-jar=/usr/share/java/eclipse-ecj.jar --disable-libjava-multilib --with-ppl --with-cloog --with-tune=generic --with-arch_32=i686 --build=x86_64-redhat-linux
   Thread model: posix
   gcc version 4.6.1 20110908 (Red Hat 4.6.1-9) (GCC) 
   COLLECT_GCC_OPTIONS='-v' '-fplugin=/home/david/coding/gcc-python/gcc-python/contributing/python.so' '-fplugin-arg-python-script=test.py' '-mtune=generic' '-march=x86-64'
    /usr/libexec/gcc/x86_64-redhat-linux/4.6.1/cc1 -quiet -v -iplugindir=/usr/lib/gcc/x86_64-redhat-linux/4.6.1/plugin test.c -iplugindir=/usr/lib/gcc/x86_64-redhat-linux/4.6.1/plugin -quiet -dumpbase test.c -mtune=generic -march=x86-64 -auxbase test -version -fplugin=/home/david/coding/gcc-python/gcc-python/contributing/python.so -fplugin-arg-python-script=test.py -o /tmp/cc1Z3b95.s
   (output of the script follows)

This allows us to see the line in which `cc1` is invoked: in the above
example, it's the final line before the output from the script::

  /usr/libexec/gcc/x86_64-redhat-linux/4.6.1/cc1 -quiet -v -iplugindir=/usr/lib/gcc/x86_64-redhat-linux/4.6.1/plugin test.c -iplugindir=/usr/lib/gcc/x86_64-redhat-linux/4.6.1/plugin -quiet -dumpbase test.c -mtune=generic -march=x86-64 -auxbase test -version -fplugin=/home/david/coding/gcc-python/gcc-python/contributing/python.so -fplugin-arg-python-script=test.py -o /tmp/cc1Z3b95.s

We can then take this line and rerun this subprocess under gdb by adding
`gdb --args` to the front like this::

   $ gdb --args /usr/libexec/gcc/x86_64-redhat-linux/4.6.1/cc1 -quiet -v -iplugindir=/usr/lib/gcc/x86_64-redhat-linux/4.6.1/plugin test.c -iplugindir=/usr/lib/gcc/x86_64-redhat-linux/4.6.1/plugin -quiet -dumpbase test.c -mtune=generic -march=x86-64 -auxbase test -version -fplugin=/home/david/coding/gcc-python/gcc-python/contributing/python.so -fplugin-arg-python-script=test.py -o /tmp/cc1Z3b95.s

This approach to obtaining a debuggable process doesn't seem to work in the
presence of `ccache`, in that it writes to a temporary directory with a name
that embeds the process ID each time, which then gets deleted.  I've worked
around this by uninstalling ccache, but apparently setting::

   CCACHE_DISABLE=1

before invoking `gcc -v` ought to also work around this.

I've also been running into this error from gdb::

  [Thread debugging using libthread_db enabled]
  Cannot find new threads: generic error

Apparently this happens when debugging a process that uses dlopen to load a
library that pulls in libpthread (as does gcc when loading in my plugin), and
a workaround is to link cc1 with -lpthread

The workaround I've been using (to avoid the need to build my own gcc) is to
use LD_PRELOAD, either like this::

   LD_PRELOAD=libpthread.so.0 gdb --args ARGS GO HERE...

or this::

   (gdb) set environment LD_PRELOAD libpthread.so.0


Handy tricks
++++++++++++

Given a (PyGccTree*) named "self"::

   (gdb) call debug_tree(self->t)

will use GCC's prettyprinter to dump the embedded (tree*) and its descendants
to stderr; it can help to put a breakpoint on that function too, to explore the
insides of that type.

Patches
-------
The project doesn't have any copyright assignment requirement: you get
to keep copyright in any contributions you make, though AIUI there's an
implicit licensing of such contributions under the GPLv3 or later, given
that any contribution is a derived work of the plugin, which is itself
licensed under the GPLv3 or later.   I'm not a lawyer, though.

The Python code within the project is intended to be usable with both Python 2
and Python 3 without running 2to3: please stick to the common subset of the two
languages.  For example, please write print statements using parentheses::

   print(42)

Under Python 2 this is a `print` statement with a parenthesized number: (42)
whereas under Python 3 this is an invocation of the `print` function.

Please try to stick `PEP-8 <http://www.python.org/dev/peps/pep-0008/>`_ for
Python code, and to `PEP-7 <http://www.python.org/dev/peps/pep-0007/>`_ for
C code (rather than the GNU coding conventions).

In C code, I strongly prefer to use multiline blocks throughout, even where
single statements are allowed (e.g. in an "if" statement)::

   if (foo()) {
       bar();
   }

as opposed to::

   if (foo())
       bar();

since this practice prevents introducing bugs when modifying such code, and the
resulting "diff" is much cleaner.

A good patch ought to add test cases for the new code that you write, and
documentation.

The test cases should be grouped in appropriate subdirectories of "tests". 
Each new test case is a directory with an:

  * `input.c` (or `input.cc` for C++)

  * `script.py` exercising the relevant Python code

  * `stdout.txt` containing the expected output from the script.

For more realistic examples of test code, put them below `tests/examples`;
these can be included by reference from the docs, so that we have
documentation that's automatically verified by `run-test-suite.py`, and
users can use this to see the relationship between source-code constructs
and the corresponding Python objects.

More information can be seen in `run-test-suite.py`

By default, `run-test-suite.py` will invoke all the tests.  You can pass it
a list of paths and it run all tests found in those paths and below.

You can generate the "gold" stdout.txt by hacking up this line in
run-test-suite.py::

   out.check_for_diff(out.actual, err.actual, p, args, 'stdout', 0)

so that the final 0 is a 1 (the "writeback" argument to `check_for_diff`).
There may need to be a non-empty stdout.txt file in the directory for
this to take effect though.

Unfortunately, this approach over-specifies the selftests, making them
rather "brittle".  Improvements to this approach would be welcome.

To directly see the GCC command line being invoked for each test, and to see
the resulting stdout and stderr, add `--show` to the arguments of
`run-test-suite.py`.

For example::

   $ python run-test-suite.py tests/plugin/diagnostics --show
   tests/plugin/diagnostics: gcc -c -o tests/plugin/diagnostics/output.o -fplugin=/home/david/coding/gcc-python-plugin/python.so -fplugin-arg-python-script=tests/plugin/diagnostics/script.py -Wno-format tests/plugin/diagnostics/input.c
   tests/plugin/diagnostics/input.c: In function 'main':
   tests/plugin/diagnostics/input.c:23:1: error: this is an error (with positional args)
   tests/plugin/diagnostics/input.c:23:1: error: this is an error (with keyword args)
   tests/plugin/diagnostics/input.c:25:1: warning: this is a warning (with positional args) [-Wdiv-by-zero]
   tests/plugin/diagnostics/input.c:25:1: warning: this is a warning (with keyword args) [-Wdiv-by-zero]
   tests/plugin/diagnostics/input.c:23:1: error: a warning with some embedded format strings %s and %i
   tests/plugin/diagnostics/input.c:25:1: warning: this is an unconditional warning [enabled by default]
   tests/plugin/diagnostics/input.c:25:1: warning: this is another unconditional warning [enabled by default]
   expected error was found: option must be either None, or of type gcc.Option
   tests/plugin/diagnostics/input.c:23:1: note: This is the start of the function
   tests/plugin/diagnostics/input.c:25:1: note: This is the end of the function
   OK
   1 success; 0 failures; 0 skipped


Documentation
=============
We use Sphinx for documentation, which makes it easy
to keep the documentation up-to-date.   For notes on how to document
Python in the .rst form accepted by Sphinx, see e.g.:

   http://sphinx.pocoo.org/domains.html#the-python-domain
