Usage example: a static analysis tool for CPython extension code
================================================================

An example of using the plugin is a static analysis tool I'm working on which
checks the C source of CPython extension modules for common coding errors.

This code is under heavy development, and is not yet ready to be used.

This was one of my main motivations for writing the GCC plugin, and I often
need to extend the plugin to support this use case.

For this reason, the checker is embedded within the gcc-python source tree
itself for now:

   * `cpychecker.py` is a short top-level script, which will eventually be
     invoked like this::

      gcc -fplugin=python.so -fplugin-arg-python-script=cpychecker.py OTHER_ARGS

   * the `libcpychecker` subdirectory contains the code that does the actual
     work

   * various test cases

Here's a list of C coding bugs I intend for the tool to detect (each one
followed by its current status):

  * lack of error handling (i.e. assuming that calls to the Python API
    succeed) [AT EARLY, BUGGY, STAGE]

  * reference-counting errors: [AT EARLY, BUGGY, STAGE]

    * missing Py_INCREF/Py_DECREF

    * leaking references to objects, not having enough references to an object

    * using an object after a point where it might have been deleted

  * tp_traverse errors (which can mess up the garbage collector); missing it
    altogether, or omitting fields [NOT IMPLEMENTED YET]

  * errors in PyArg_ParseTuple and friends:

     * type mismatches e.g. `int` vs `long` (often leads to flaws on big-endian
       64-bit architectures, where sizeof(int) != sizeof(long))
       [MOSTLY IMPLEMENTED FOR PyArg_Parse*, NOT IMPLEMENTED FOR Py_BuildValue]

     * reference-counting errors, for the cases where objects are returned with
       either new or borrowed references (depending on the format codes).
       [NOT IMPLEMENTED YET]

  * errors in exception handling, so that we can issue errors about e.g. not
    returning NULL if an exception is set, or returning NULL if an exception is
    not set [NOT IMPLEMENTED YET]

  * errors in GIL-handling [NOT IMPLEMENTED YET]

    * lock/release mismatches

    * missed opportunities to release the GIL (e.g. compute-intensive
      functions; functions that wait on IO/syscalls)

Ideas for other tests are most welcome (patches even more so!)

We will probably need various fallbacks and suppression modes for turning off
individual tests (perhaps pragmas, perhaps compile-line flags, etc)

