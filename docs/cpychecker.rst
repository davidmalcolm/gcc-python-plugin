.. Copyright 2011, 2012 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011, 2012 Red Hat, Inc.

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

.. _cpychecker:

Usage example: a static analysis tool for CPython extension code
================================================================

.. note:: This code is under heavy development, and still contains bugs.  It
   is not unusual to see Python tracebacks when running the checker.  You
   should verify what the checker reports before acting on it: it could be
   wrong.

An example of using the plugin is a static analysis tool I'm working on which
checks the C source of CPython extension modules for common coding errors.

This was one of my main motivations for writing the GCC plugin, and I often
need to extend the plugin to support this use case.

For this reason, the checker is embedded within the gcc-python source tree
itself for now:

   * `gcc-with-cpychecker` is a harness script, which invokes GCC, adding
     the arguments necessary to use the Python plugin, using the
     `libcpychecker` Python code

   * the `libcpychecker` subdirectory contains the code that does the actual
     work

   * various test cases (in the source tree, below `tests/cpychecker`)

So it should be possible to use the checker on arbitrary CPython extension
code by replacing "gcc" with "gcc-with-cpychecker" in your build with
something like::

   make CC=/path/to/built/plugin/gcc-with-cpychecker

to override the Makefile variable `CC`.

You may need to supply an absolute path, especially if the "make" recursively
invokes "make" within subdirectories (thus having a different working
directory).

Similarly, for projects that use `distutils
<http://docs.python.org/library/distutils.html>`_, the code is typically built
with an invocation like this::

   python setup.py build

This respects the environment variable `CC`, so typically you can replace the
above with something like this in order to add the additional checks::

   CC=/path/to/built/plugin/gcc-with-cpychecker python setup.py build

Reference-count checking
------------------------
The checker attempts to analyze all possible paths through each function,
tracking the various ``PyObject*`` objects encountered.

For each path through the function and ``PyObject*``, it determines what the
reference count ought to be at the end of the function, issuing warnings for
any that are incorrect.

The warnings are in two forms: the classic textual output to GCC's standard
error stream, together with an HTML report indicating the flow through the
function, in graphical form.

For example, given this buggy C code:

.. code-block:: c

   PyObject *
   test(PyObject *self, PyObject *args)
   {
       PyObject *list;
       PyObject *item;
       list = PyList_New(1);
       if (!list)
           return NULL;
       item = PyLong_FromLong(42);
       /* This error handling is incorrect: it's missing an
          invocation of Py_DECREF(list): */
       if (!item)
           return NULL;
       /* This steals a reference to item; item is not leaked when we get here: */
       PyList_SetItem(list, 0, item);
       return list;
   }

the checker emits these messages to stderr::

   input.c: In function 'test':
   input.c:38:1: warning: ob_refcnt of '*list' is 1 too high [enabled by default]
   input.c:38:1: note: was expecting final ob_refcnt to be N + 0 (for some unknown N)
   input.c:38:1: note: but final ob_refcnt is N + 1
   input.c:27:10: note: PyListObject allocated at:     list = PyList_New(1);
   input.c:27:10: note: when PyList_New() succeeds at:     list = PyList_New(1);
   input.c:27:10: note: ob_refcnt is now refs: 1 + N where N >= 0
   input.c:28:8: note: taking False path at:     if (!list)
   input.c:30:10: note: reaching:     item = PyLong_FromLong(42);
   input.c:30:10: note: when PyLong_FromLong() fails at:     item = PyLong_FromLong(42);
   input.c:33:8: note: taking True path at:     if (!item)
   input.c:34:9: note: reaching:         return NULL;
   input.c:38:1: note: returning
   input.c:24:1: note: graphical error report for function 'test' written out to 'input.c.test-refcount-errors.html'

along with this HTML report (as referred to by the final line on stderr):

   .. figure:: sample-html-error-report.png
      :alt: screenshot of the HTML report

The HTML report is intended to be relatively self-contained, and thus easy to
attach to bug tracking systems (it embeds its own CSS inline, and references
the JavaScript it uses via URLs to the web).

.. note:: The arrow graphics in the HTML form of the report are added by using
   the JSPlumb JavaScript library to generate HTML 5 <canvas> elements.  You
   may need a relatively modern browser to see them.

.. note:: The checker tracks reference counts in an abstract way, in two parts:
   a part of the reference count that it knows about within the context of the
   function, along with a second part: all of the other references held by the
   rest of the program.

   For example, in a call to PyInt_FromLong(0), it is assumed that if the call
   succeeds, the object has a reference count of 1 + N, where N is some unknown
   amount of other references held by the rest of the program.   The checker
   knows that N >= 0.

   If the object is then stored in an opaque container which is known to
   increment the reference count, the checker can say that the reference count
   is then 1 + (N+1).

   If the function then decrements the reference count (to finish transferring
   the reference to the opaque container), the checker now treats the object as
   having a reference count of 0 + (N+1): it no longer owns any references on
   the object, but the reference count is actually unchanged relative to the
   original 1 + N amount.  It also knows, given that N >= 0 that the actual
   reference count is >= 1, and thus the object won't (yet) be deallocated.

Assumptions and configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
For any function returning a ``PyObject*``, it assumes that the ``PyObject*``
should be either a new reference to an object, or NULL (with an exception set)
- the function's caller should "own" a reference to that object.  For all
other ``PyObject*``, it assumes that there should be no references owned by the
function when the function terminates.

It will assume this behavior for any function (or call through a function
pointer) that returns a ``PyObject*``.

It is possible to override this behavior using custom compiler attributes as
follows:

Marking functions that return borrowed references
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The checker provides a custom GCC attribute:

.. code-block:: c

   __attribute__((cpychecker_returns_borrowed_ref))

which can be used to mark function declarations:

.. code-block:: c

  /* The checker automatically defines this preprocessor name when creating
     the custom attribute: */
  #if defined(WITH_CPYCHECKER_RETURNS_BORROWED_REF_ATTRIBUTE)
    #define CPYCHECKER_RETURNS_BORROWED_REF \
      __attribute__((cpychecker_returns_borrowed_ref))
  #else
    #define CPYCHECKER_RETURNS_BORROWED_REF
  #endif

  PyObject *foo(void)
    CPYCHECKER_RETURNS_BORROWED_REF;

Given the above, the checker will assume that invocations of ``foo()`` are
returning a borrowed reference (or NULL), rather than a new reference.  It
will also check that this is that case when verifying the implementation of
``foo()`` itself.

Marking functions that steal references to their arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The checker provides a custom GCC attribute:

.. code-block:: c

     __attribute__((cpychecker_steals_reference_to_arg(n)))

which can be used to mark function declarations:

.. code-block:: c

  /* The checker automatically defines this preprocessor name when creating
     the custom attribute: */
  #if defined(WITH_CPYCHECKER_STEALS_REFERENCE_TO_ARG_ATTRIBUTE)
    #define CPYCHECKER_STEALS_REFERENCE_TO_ARG(n) \
     __attribute__((cpychecker_steals_reference_to_arg(n)))
  #else
   #define CPYCHECKER_STEALS_REFERENCE_TO_ARG(n)
  #endif

  extern void foo(PyObject *obj)
    CPYCHECKER_STEALS_REFERENCE_TO_ARG(1);

Given the above, the checker will assume that invocations of ``foo()`` steal
a reference to the first argument (``obj``).  It will also verify that this is
the case when analyzing the implementation of ``foo()`` itself.

More then one argument can be marked:

.. code-block:: c

  extern void bar(int i, PyObject *obj, int j, PyObject *other)
    CPYCHECKER_STEALS_REFERENCE_TO_ARG(2)
    CPYCHECKER_STEALS_REFERENCE_TO_ARG(4);

The argument indices are 1-based (the above example is thus referring to
``obj`` and to ``other``).

All such arguments to the attribute should be ``PyObject*`` (or a pointer to a
derived structure type).

It is assumed that such references are stolen for all possible outcomes of the
function - if a function can either succeed or fail, the reference is stolen in
both possible worlds.

Error-handling checking
-----------------------
The checker has knowledge of much of the CPython C API, and will generate
a trace tree containing many of the possible error paths.   It will issue
warnings for code that appears to not gracefully handle an error.

(TODO: show example)

As noted above, it assumes that any function that returns a ``PyObject*`` can
return can either NULL (setting an exception), or a new reference.  It knows
about much of the other parts of the CPython C API, including many other
functions that can fail.

The checker will emit warnings for various events:

  * if it detects a dereferencing of a ``NULL`` value

  * if a ``NULL`` value is erroneously passed to various CPython API
    entrypoints which are known to implicitly dereference those arguments
    (which would lead to a segmentation fault if that code path were executed)::

      input.c: In function 'test':
      input.c:38:33: warning: calling PyString_AsString with NULL (gcc.VarDecl('repr_args')) as argument 1 at input.c:38
      input.c:31:15: note: when PyObject_Repr() fails at:     repr_args = PyObject_Repr(args);
      input.c:38:33: note: PyString_AsString() invokes Py_TYPE() on the pointer via the PyString_Check() macro, thus accessing (NULL)->ob_type
      input.c:27:1: note: graphical error report for function 'test' written out to 'input.c.test-refcount-errors.html'

  * if it detects that an uninitialized local variable has been used

  * if it detects access to an object that has been deallocated, or such an
    object being returned::

       input.c: In function 'test':
       input.c:43:1: warning: returning pointer to deallocated memory
       input.c:29:15: note: when PyLong_FromLong() succeeds at:     PyObject *tmp = PyLong_FromLong(0x1000);
       input.c:31:8: note: taking False path at:     if (!tmp) {
       input.c:39:5: note: reaching:     Py_DECREF(tmp);
       input.c:39:5: note: when taking False path at:     Py_DECREF(tmp);
       input.c:39:5: note: reaching:     Py_DECREF(tmp);
       input.c:39:5: note: calling tp_dealloc on PyLongObject allocated at input.c:29 at:     Py_DECREF(tmp);
       input.c:42:5: note: reaching:     return tmp;
       input.c:43:1: note: returning
       input.c:39:5: note: memory deallocated here
       input.c:27:1: note: graphical error report for function 'returning_dead_object' written out to 'input.c.test.html'

Errors in exception-handling
----------------------------
The checker keeps track of the per-thread exception state.  It will issue a
warning about any paths through functions returning a ``PyObject*`` that return
NULL for which the per-thread exception state has not been set::

   input.c: In function 'test':
   input.c:32:5: warning: returning (PyObject*)NULL without setting an exception

The checker does not emit the warning for cases where it is known that such
behavior is acceptable.  Currently this covers functions used as `tp_iternext
<http://docs.python.org/c-api/typeobj.html#tp_iternext>`_ callbacks of a
``PyTypeObject``.

If you have a helper function that always sets an exception, you can mark this
property using a custom GCC attribute:

.. code-block:: c

    __attribute__((cpychecker_sets_exception))

which can be used to mark function declarations.

.. code-block:: c

  /* The checker automatically defines this preprocessor name when creating
     the custom attribute: */
   #if defined(WITH_CPYCHECKER_SETS_EXCEPTION_ATTRIBUTE)
     #define CPYCHECKER_SETS_EXCEPTION \
        __attribute__((cpychecker_sets_exception))
   #else
     #define CPYCHECKER_SETS_EXCEPTION
   #endif

   extern void raise_error(const char *msg)
     CPYCHECKER_SETS_EXCEPTION;

Given the above, the checker will know that an exception is set whenever a
call to `raise_error()` occurs.  It will also verify that `raise_error()`
actually behaves this way when compiling the implementation of `raise_error`.

There is an analogous attribute for the case where a function returns a
negative value to signify an error, where the exception state is set whenever
a **negative** value is returned:

.. code-block:: c

    __attribute__((cpychecker_negative_result_sets_exception))

which can be used to mark function declarations.

.. code-block:: c

  /* The checker automatically defines this preprocessor name when creating
     the custom attribute: */
   #if defined(WITH_CPYCHECKER_NEGATIVE_RESULT_SETS_EXCEPTION_ATTRIBUTE)
     #define CPYCHECKER_NEGATIVE_RESULT_SETS_EXCEPTION \
        __attribute__((cpychecker_negative_result_sets_exception))
   #else
     #define CPYCHECKER_NEGATIVE_RESULT_SETS_EXCEPTION
   #endif

   extern int foo(void)
     CPYCHECKER_NEGATIVE_RESULT_SETS_EXCEPTION;

Given the above, the checker will know that an exception is raised whenever a
call to `foo` returns a negative value.  It will also verify that `foo`
actually behaves this way when compiling the implementation of `foo`.

The checker already knows about many of the functions within the CPython API
which behave this way.

Format string checking
----------------------

The checker will analyze some `Python APIs that take format strings
<http://docs.python.org/c-api/arg.html>`_  and detect mismatches between the
number and types of arguments that are passed in, as compared with those
described by the format string.

It currently verifies the arguments to the following API entrypoints:

  * `PyArg_ParseTuple
    <http://docs.python.org/c-api/arg.html#PyArg_ParseTuple>`_

  * `PyArg_ParseTupleAndKeywords
    <http://docs.python.org/c-api/arg.html#PyArg_ParseTupleAndKeywords>`_

  * `PyArg_Parse
    <http://docs.python.org/c-api/arg.html#PyArg_Parse>`_

  * `Py_BuildValue
    <http://docs.python.org/c-api/arg.html#Py_BuildValue>`_

  * `PyObject_CallFunction
    <http://docs.python.org/c-api/object.html#PyObject_CallFunction>`_

  * `PyObject_CallMethod
    <http://docs.python.org/c-api/object.html#PyObject_CallMethod>`_

along with the variants that occur if you define `PY_SSIZE_T_CLEAN` before
`#include <Python.h>`.

For example, type mismatches between ``int`` vs ``long`` can lead to flaws
when the code is compiled on big-endian 64-bit architectures, where
``sizeof(int) != sizeof(long)`` and the in-memory layout of those types differs
from what you might expect.

The checker will also issue a warning if the list of keyword arguments in a
call to PyArg_ParseTupleAndKeywords is not NULL-terminated.

.. note:: All of the various "#" codes in these format strings are affected by
   the presence of the macro `PY_SSIZE_T_CLEAN`. If the macro was defined
   before including Python.h, the various lengths for these format codes are of
   C type `Py_ssize_t` rather than `int`.

   This behavior was clarified in the Python 3 version of the C API
   documentation, though the Python 2 version of the API docs leave the matter
   of which codes are affected somewhat ambiguous.

   Nevertheless, the API *does* work this way in Python 2: all format codes
   with a "#" do work this way.

   Internally, the C preprocessor converts such function calls into invocations
   of:

      * `_PyArg_ParseTuple_SizeT`
      * `_PyArg_ParseTupleAndKeywords_SizeT`

   The checker handles this behavior correctly, by checking "#" codes in the
   regular functions against `int` and those in the modified functions against
   `Py_ssize_t`.

Associating PyTypeObject instances with compile-time types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The "O!" format code to ``PyArg_ParseTuple`` takes a ``PyTypeObject`` followed
by the address of an object.  This second argument can point to a
``PyObject*``, but it can also point to a pointer to a derived class.

For example, CPython's own implementation contains code like this:

.. code-block:: c

  static PyObject *
  unicodedata_decomposition(PyObject *self, PyObject *args)
  {
      PyUnicodeObject *v;

      /* ...snip... */

      if (!PyArg_ParseTuple(args, "O!:decomposition",
                            &PyUnicode_Type, &v))

      /* ...etc... */

in which the input argument is written out into the ``PyUnicodeObject*``,
provided that it is indeed a unicode instance.

When the cpychecker verifies the types in this format string it verifies that
the run-time type of the ``PyTypeObject`` matches the compile-time type
(``PyUnicodeObject *``).   It is able to do this since it contains hard-coded
associations between these worlds for all of Python's built-in types: for the
above case, it "knows" that ``PyUnicode_Type`` is associated with
``PyUnicodeObject``.

If you need to provide a similar association for an extension type, the checker
provides a custom GCC attribute:

.. code-block:: c

     __attribute__((cpychecker_type_object_for_typedef(typename)))

which can be used to mark PyTypeObject instance, giving the name of the typedef
that PyObject instances of that type can be safely cast to.

.. code-block:: c

  /* The checker automatically defines this preprocessor name when creating
     the custom attribute: */
  #if defined(WITH_CPYCHECKER_TYPE_OBJECT_FOR_TYPEDEF_ATTRIBUTE)
    #define CPYCHECKER_TYPE_OBJECT_FOR_TYPEDEF(typename) \
       __attribute__((cpychecker_type_object_for_typedef(typename)))
  #else
    /* This handles the case where we're compiling with a "vanilla"
       compiler that doesn't supply this attribute: */
    #define CPYCHECKER_TYPE_OBJECT_FOR_TYPEDEF(typename)
  #endif

  /* Define some PyObject subclass, as both a struct and a typedef */
  struct OurObjectStruct {
      PyObject_HEAD
      /* other fields */
  };
  typedef struct OurObjectStruct OurExtensionObject;

  /*
    Declare the PyTypeObject, using the custom attribute to associate it with
    the typedef above:
  */
  extern PyTypeObject UserDefinedExtension_Type
    CPYCHECKER_TYPE_OBJECT_FOR_TYPEDEF("OurExtensionObject");

Given the above, the checker will associate the given ``PyTypeObject`` with the
given typedef.


Verification of PyMethodDef tables
----------------------------------

The checker will verify the types within tables of `PyMethodDef
<http://docs.python.org/c-api/structures.html#PyMethodDef>`_ initializers: the
callbacks are typically cast to ``PyCFunction``, but the exact type needs to
correspond to the flags given.  For example ``(METH_VARARGS | METH_KEYWORDS)``
implies a different function signature to the default, which the vanilla C
compiler has no way of verifying.

.. code-block:: c

   /*
     BUG: there's a mismatch between the signature of the callback and
     that implied by ml_flags below.
    */
   static PyObject *widget_display(PyObject *self, PyObject *args);

   static PyMethodDef widget_methods[] = {
       {"display",
        (PyCFunction)widget_display,
        (METH_VARARGS | METH_KEYWORDS), /* ml_flags */
        NULL},

       {NULL, NULL, 0, NULL} /* terminator */
   };

Given the above, the checker will emit an error like this::

   input.c:59:6: warning: flags do not match callback signature for 'widget_display' within PyMethodDef table
   input.c:59:6: note: expected ml_meth callback of type "PyObject (fn)(someobject *, PyObject *args, PyObject *kwargs)" due to METH_KEYWORDS flag (3 arguments)
   input.c:59:6: note: actual type of underlying callback: struct PyObject * <Tc53> (struct PyObject *, struct PyObject *) (2 arguments)
   input.c:59:6: note: see http://docs.python.org/c-api/structures.html#PyMethodDef

It will also warn about tables of ``PyMethodDef`` initializers that are
lacking a ``NULL`` sentinel value to terminate the iteration:

.. code-block:: c

   static PyMethodDef widget_methods[] = {
       {"display",
        (PyCFunction)widget_display,
        0, /* ml_flags */
        NULL},

       /* BUG: this array is missing a NULL value to terminate
          the list of methods, leading to a possible segfault
          at run-time */
   };

Given the above, the checker will emit this warning::

  input.c:39:6: warning: missing NULL sentinel value at end of PyMethodDef table

Additional tests
----------------

* the checker will verify the argument lists of invocations of
  `PyObject_CallFunctionObjArgs
  <http://docs.python.org/c-api/object.html#PyObject_CallFunctionObjArgs>`_ and
  `PyObject_CallMethodObjArgs
  <http://docs.python.org/c-api/object.html#PyObject_CallMethodObjArgs>`_,
  checking that all of the arguments are of the correct type
  (PyObject* or subclasses), and that the list is NULL-terminated::

     input.c: In function 'test':
     input.c:33:5: warning: argument 2 had type char[12] * but was expecting a PyObject* (or subclass)
     input.c:33:5: warning: arguments to PyObject_CallFunctionObjArgs were not NULL-terminated

Limitations and caveats
-----------------------

Compiling with the checker is significantly slower than with "vanilla" gcc.
I have been focussing on correctness and features, rather than optimization.
I hope that it will be possible to greatly speed up the checker via
ahead-of-time compilation of the Python code (e.g. using Cython).

The checker does not yet fully implement all of C: expect to see Python
tracebacks when it encounters less common parts of the language.  (We'll fix
those bugs as we come to them)

The checker has a rather simplistic way of tracking the flow through a
function: it builds a tree of all possible traces of execution through a
function.  This brings with it some shortcomings:

  * In order to guarantee that the analysis terminates, the checker will only
    track the first time through any loop, and stop analysing that trace for
    subsequent iterations.  This appears to be good enough for detecting many
    kinds of reference leaks, especially in simple wrapper code, but is clearly
    suboptimal.

  * In order to avoid combinatorial explosion, the checker will stop analyzing
    a function once the trace tree gets sufficiently large.  When it reaches
    this cutoff, a warning is issued::

      input.c: In function 'add_module_objects':
      input.c:31:1: note: this function is too complicated for the reference-count checker to analyze

  * The checker doesn't yet match up similar traces, and so a single bug that
    affects multiple traces in the trace tree can lead to duplicate error
    reports.

Only a subset of the CPython API has been modelled so far.  The functions
known to the checker are:

`PyArg_Parse and _PyArg_Parse_SizeT <http://docs.python.org/c-api/arg.html#PyArg_Parse>`_,
`PyArg_ParseTuple and _PyArg_ParseTuple_SizeT <http://docs.python.org/c-api/arg.html#PyArg_ParseTuple>`_,
`PyArg_ParseTupleAndKeywords and _PyArg_ParseTupleAndKeywords_SizeT <http://docs.python.org/c-api/arg.html#PyArg_ParseTupleAndKeywords>`_,
`PyArg_UnpackTuple <http://docs.python.org/c-api/arg.html#PyArg_UnpackTuple>`_,
`Py_AtExit <http://docs.python.org/c-api/sys.html#Py_AtExit>`_,
`PyBool_FromLong <http://docs.python.org/c-api/bool.html#PyBool_FromLong>`_,
`Py_BuildValue and _Py_BuildValue_SizeT <http://docs.python.org/c-api/arg.html#Py_BuildValue>`_,
`PyCallable_Check <http://docs.python.org/c-api/object.html#PyCallable_Check>`_,
`PyCapsule_GetPointer <http://docs.python.org/c-api/capsule.html#PyCapsule_GetPointer>`_,
`PyCObject_AsVoidPtr <http://docs.python.org/c-api/cobject.html#PyCObject_AsVoidPtr>`_,
`PyCObject_FromVoidPtr <http://docs.python.org/c-api/cobject.html#PyCObject_FromVoidPtr>`_,
`PyCObject_FromVoidPtrAndDesc <http://docs.python.org/c-api/cobject.html#PyCObject_FromVoidPtrAndDesc>`_,
`PyCode_New <http://docs.python.org/c-api/code.html#PyCode_New>`_,
`PyDict_GetItem <http://docs.python.org/c-api/dict.html#PyDict_GetItem>`_,
`PyDict_GetItemString <http://docs.python.org/c-api/dict.html#PyDict_GetItemString>`_,
`PyDict_New <http://docs.python.org/c-api/dict.html#PyDict_New>`_,
`PyDict_SetItem <http://docs.python.org/c-api/dict.html#PyDict_SetItem>`_,
`PyDict_SetItemString <http://docs.python.org/c-api/dict.html#PyDict_SetItemString>`_,
`PyDict_Size <http://docs.python.org/c-api/dict.html#PyDict_Size>`_,
`PyErr_Format <http://docs.python.org/c-api/exceptions.html#PyErr_Format>`_,
`PyErr_NewException <http://docs.python.org/c-api/exceptions.html#PyErr_NewException>`_,
`PyErr_NoMemory <http://docs.python.org/c-api/exceptions.html#PyErr_NoMemory>`_,
`PyErr_Occurred <http://docs.python.org/c-api/exceptions.html#PyErr_Occurred>`_,
`PyErr_Print <http://docs.python.org/c-api/exceptions.html#PyErr_Print>`_,
`PyErr_PrintEx <http://docs.python.org/c-api/exceptions.html#PyErr_PrintEx>`_,
`PyErr_SetFromErrno <http://docs.python.org/c-api/exceptions.html#PyErr_SetFromErrno>`_,
`PyErr_SetFromErrnoWithFilename <http://docs.python.org/c-api/exceptions.html#PyErr_SetFromErrnoWithFilename>`_,
`PyErr_SetNone <http://docs.python.org/c-api/exceptions.html#PyErr_SetNone>`_,
`PyErr_SetObject <http://docs.python.org/c-api/exceptions.html#PyErr_SetObject>`_,
`PyErr_SetString <http://docs.python.org/c-api/exceptions.html#PyErr_SetString>`_,
`PyErr_WarnEx <http://docs.python.org/c-api/exceptions.html#PyErr_WarnEx>`_,
`PyEval_CallMethod`,
`PyEval_CallObjectWithKeywords`,
`PyEval_InitThreads <http://docs.python.org/c-api/init.html#PyEval_InitThreads>`_,
`PyEval_RestoreThread <http://docs.python.org/c-api/init.html#PyEval_RestoreThread>`_,
`PyEval_SaveThread <http://docs.python.org/c-api/init.html#PyEval_SaveThread>`_,
`Py_FatalError <http://docs.python.org/c-api/sys.html#Py_FatalError>`_,
`PyFile_SoftSpace <http://docs.python.org/c-api/file.html#PyFile_SoftSpace>`_,
`PyFile_WriteString <http://docs.python.org/c-api/file.html#PyFile_WriteString>`_,
`Py_Finalize <http://docs.python.org/c-api/init.html#Py_Finalize>`_,
`PyFrame_New`,
`Py_GetVersion <http://docs.python.org/c-api/init.html#Py_GetVersion>`_,
`PyGILState_Ensure <http://docs.python.org/c-api/init.html#PyGILState_Ensure>`_,
`PyGILState_Release <http://docs.python.org/c-api/init.html#PyGILState_Release>`_,
`PyImport_AddModule <http://docs.python.org/c-api/import.html#PyImport_AddModule>`_,
`PyImport_AppendInittab <http://docs.python.org/c-api/import.html#PyImport_AppendInittab>`_,
`PyImport_ImportModule <http://docs.python.org/c-api/import.html#PyImport_ImportModule>`_,
`Py_Initialize <http://docs.python.org/c-api/init.html#Py_Initialize>`_,
`Py_InitModule4_64`,
`PyInt_AsLong <http://docs.python.org/c-api/int.html#PyInt_AsLong>`_,
`PyInt_FromLong <http://docs.python.org/c-api/int.html#PyInt_FromLong>`_,
`PyList_Append <http://docs.python.org/c-api/list.html#PyList_Append>`_,
`PyList_GetItem <http://docs.python.org/c-api/list.html#PyList_GetItem>`_,
`PyList_New <http://docs.python.org/c-api/list.html#PyList_New>`_,
`PyList_SetItem <http://docs.python.org/c-api/list.html#PyList_SetItem>`_,
`PyList_Size <http://docs.python.org/c-api/list.html#PyList_Size>`_,
`PyLong_FromLong <http://docs.python.org/c-api/long.html#PyLong_FromLong>`_,
`PyLong_FromLongLong <http://docs.python.org/c-api/long.html#PyLong_FromLongLong>`_,
`PyLong_FromString <http://docs.python.org/c-api/long.html#PyLong_FromString>`_,
`PyLong_FromVoidPtr <http://docs.python.org/c-api/long.html#PyLong_FromVoidPtr>`_,
`PyMapping_Size <http://docs.python.org/c-api/mapping.html#PyMapping_Size>`_,
`PyMem_Free <http://docs.python.org/c-api/memory.html#PyMem_Free>`_,
`PyMem_Malloc <http://docs.python.org/c-api/memory.html#PyMem_Malloc>`_,
`PyModule_AddIntConstant <http://docs.python.org/c-api/module.html#PyModule_AddIntConstant>`_,
`PyModule_AddObject <http://docs.python.org/c-api/module.html#PyModule_AddObject>`_,
`PyModule_AddStringConstant <http://docs.python.org/c-api/module.html#PyModule_AddStringConstant>`_,_,
`PyModule_GetDict <http://docs.python.org/c-api/module.html#PyModule_GetDict>`_,
`PyNumber_Int <http://docs.python.org/c-api/number.html#PyNumber_Int>`_,
`PyNumber_Remainer <http://docs.python.org/c-api/number.html#PyNumber_Remainder>`_,
`PyObject_AsFileDescriptor <http://docs.python.org/c-api/object.html#PyObject_AsFileDescriptor>`_,
`PyObject_Call <http://docs.python.org/c-api/object.html#PyObject_Call>`_,
`PyObject_CallFunction and _PyObject_CallFunction_SizeT <http://docs.python.org/c-api/object.html#PyObject_CallFunction>`_,
`PyObject_CallFunctionObjArgs <http://docs.python.org/c-api/object.html#PyObject_CallFunctionObjArgs>`_,
`PyObject_CallMethod and _PyObject_CallMethod_SizeT <http://docs.python.org/c-api/object.html#PyObject_CallMethod>`_,
`PyObject_CallMethodObjArgs <http://docs.python.org/c-api/object.html#PyObject_CallMethodObjArgs>`_,
`PyObject_CallObject <http://docs.python.org/c-api/object.html#PyObject_CallObject>`_,
`PyObject_GetAttr <http://docs.python.org/c-api/object.html#PyObject_GetAttr>`_,
`PyObject_GetAttrString <http://docs.python.org/c-api/object.html#PyObject_GetAttrString>`_,
`PyObject_GetItem <http://docs.python.org/c-api/object.html#PyObject_GetItem>`_,
`PyObject_GenericGetAttr <http://docs.python.org/c-api/object.html#PyObject_GenericGetAttr>`_,
`PyObject_GenericSetAttr <http://docs.python.org/c-api/object.html#PyObject_GenericSetAttr>`_,
`PyObject_HasAttrString <http://docs.python.org/c-api/object.html#PyObject_HasAttrString>`_,
`PyObject_IsTrue <http://docs.python.org/c-api/object.html#PyObject_IsTrue>`_,
`_PyObject_New`,
`PyObject_Repr <http://docs.python.org/c-api/object.html#PyObject_Repr>`_,
`PyObject_SetAttr <http://docs.python.org/c-api/object.html#PyObject_SetAttr>`_,
`PyObject_SetAttrString <http://docs.python.org/c-api/object.html#PyObject_SetAttrString>`_,
`PyObject_Str <http://docs.python.org/c-api/object.html#PyObject_Str>`_,
`PyOS_snprintf <http://docs.python.org/c-api/conversion.html#PyOS_snprintf>`_,
`PyRun_SimpleFileExFlags <http://docs.python.org/c-api/veryhigh.html#PyRun_SimpleFileExFlags>`_,
`PyRun_SimpleStringFlags <http://docs.python.org/c-api/veryhigh.html#PyRun_SimpleStringFlags>`_,
`PySequence_Concat <http://docs.python.org/c-api/sequence.html#PySequence_Concat>`_,
`PySequence_GetItem <http://docs.python.org/c-api/sequence.html#PySequence_GetItem>`_,
`PySequence_GetSlice <http://docs.python.org/c-api/sequence.html#PySequence_GetSlice>`_,
`PySequence_SetItem <http://docs.python.org/c-api/sequence.html#PySequence_SetItem>`_,
`PyString_AsString <http://docs.python.org/c-api/string.html#PyString_AsString>`_,
`PyString_Concat <http://docs.python.org/c-api/string.html#PyString_Concat>`_,
`PyString_ConcatAndDel <http://docs.python.org/c-api/string.html#PyString_ConcatAndDel>`_,
`PyString_FromFormat <http://docs.python.org/c-api/string.html#PyString_FromFormat>`_,
`PyString_FromString <http://docs.python.org/c-api/string.html#PyString_FromString>`_,
`PyString_FromStringAndSize <http://docs.python.org/c-api/string.html#PyString_FromStringAndSize>`_,
`PyString_InternFromString <http://docs.python.org/c-api/string.html#PyString_InternFromString>`_,
`PyString_Size <http://docs.python.org/c-api/string.html#PyString_Size>`_,
`PyStructSequence_InitType`,
`PyStructSequence_New`,
`PySys_GetObject <http://docs.python.org/c-api/sys.html#PySys_GetObject>`_,
`PySys_SetObject <http://docs.python.org/c-api/sys.html#PySys_SetObject>`_,
`PyTraceBack_Here`,
`PyTuple_GetItem <http://docs.python.org/c-api/tuple.html#PyTuple_GetItem>`_,
`PyTuple_New <http://docs.python.org/c-api/tuple.html#PyTuple_New>`_,
`PyTuple_Pack <http://docs.python.org/c-api/tuple.html#PyTuple_Pack>`_,
`PyTuple_SetItem <http://docs.python.org/c-api/tuple.html#PyTuple_SetItem>`_,
`PyTuple_Size <http://docs.python.org/c-api/tuple.html#PyTuple_Size>`_,
`PyType_IsSubtype <http://docs.python.org/dev/c-api/type.html#PyType_IsSubtype>`_,
`PyType_Ready <http://docs.python.org/dev/c-api/type.html#PyType_Ready>`_,
`PyUnicodeUCS4_AsUTF8String <http://docs.python.org/c-api/unicode.html#PyUnicode_AsUTF8String>`_,
`PyUnicodeUCS4_DecodeUTF8 <http://docs.python.org/c-api/unicode.html#PyUnicode_DecodeUTF8>`_,
`PyWeakref_GetObject <http://docs.python.org/c-api/weakref.html#PyWeakref_GetObject>`_


Ideas for future tests
----------------------

Here's a list of some other C coding bugs I intend for the tool to detect:

  * tp_traverse errors (which can mess up the garbage collector); missing it
    altogether, or omitting fields

  * errors in GIL-handling

    * lock/release mismatches

    * missed opportunities to release the GIL (e.g. compute-intensive
      functions; functions that wait on IO/syscalls)

Ideas for other tests are most welcome (patches even more so!)

We will probably need various fallbacks and suppression modes for turning off
individual tests (perhaps pragmas, perhaps compile-line flags, etc)


Reusing this code for other projects
------------------------------------
It may be possible to reuse the analysis engine from cpychecker for other
kinds of analysis - hopefully the python-specific parts are relatively
self-contained.  Email the `gcc-python-plugin's mailing list
<https://fedorahosted.org/mailman/listinfo/gcc-python-plugin/>`_ if you're
interested in adding verifiers for other kinds of code.
