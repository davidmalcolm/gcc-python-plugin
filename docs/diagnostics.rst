.. Copyright 2011-2012, 2017 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011-2012, 2017 Red Hat, Inc.

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

Generating custom errors and warnings
=====================================

.. py:function:: gcc.warning(location, message, option=None)

   Emits a compiler warning at the given :py:class:`gcc.Location`, potentially
   controlled by a :py:class:`gcc.Option`.

   If no option is supplied (or `None` is supplied), then the warning is an
   unconditional one, always issued::

      gcc.warning(func.start, 'this is an unconditional warning')

   .. code-block:: bash

      $ ./gcc-with-python script.py input.c
      input.c:25:1: warning: this is an unconditional warning [enabled by default]

   and will be an error if `-Werror` is supplied as a command-line argument to
   GCC:

   .. code-block:: bash

      $ ./gcc-with-python script.py -Werror input.c
      input.c:25:1: error: this is an unconditional warning [-Werror]

   It's possible to associate the warning with a command-line option, so that
   it is controlled by that option.

   For example, given this Python code::

      gcc.warning(func.start, 'Incorrect formatting', gcc.Option('-Wformat'))

   if the given warning is enabled, a warning will be printed to stderr:

   .. code-block:: bash

      $ ./gcc-with-python script.py input.c
      input.c:25:1: warning: incorrect formatting [-Wformat]

   If the given warning is being treated as an error (through the usage
   of `-Werror`), then an error will be printed:

   .. code-block:: bash

      $ ./gcc-with-python script.py -Werror input.c
      input.c:25:1: error: incorrect formatting [-Werror=format]
      cc1: all warnings being treated as errors

   .. code-block:: bash

      $ ./gcc-with-python script.py -Werror=format input.c
      input.c:25:1: error: incorrect formatting [-Werror=format]
      cc1: some warnings being treated as errors

   If the given warning is disabled, the warning will not be printed:

   .. code-block:: bash

      $ ./gcc-with-python script.py -Wno-format input.c

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

.. py:function:: gcc.inform(location, message)

   This is a wrapper around GCC's `inform` function.

   Expects an instance of :py:class:`gcc.Location` or
   :py:class:`gcc.RichLocation`, (not None) and a string

   Emit an informational message at that location.

   For example::

     gcc.inform(stmt.loc, 'this is where X was defined')

   would lead to this informational message being printed to stderr:

   .. code-block:: bash

     $ ./gcc-with-python script.py input.c
     input.c:23:3: note: this is where X was defined
