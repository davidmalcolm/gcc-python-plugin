Usage::

   gcc-with-python PATH_TO_PYTHON_SCRIPT GCC PARAMETERS

`gcc-with-python` is a helper script which invokes GCC, whilst loading the
Python plugin for GCC, running the given python script.

Example::

   gcc-with-python show-ssa.py example.c
