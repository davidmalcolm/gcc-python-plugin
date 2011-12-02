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

Success Stories
===============

If you use the gcc python plugin to improve your code, we'd love to hear about
it.

If you want to share a success story here, please email the plugin's `mailing list
<https://fedorahosted.org/mailman/listinfo/gcc-python-plugin/>`_.

The `GNU Debugger <http://sourceware.org/gdb/>`_
------------------------------------------------
Bugs found in gdb by compiling it with the plugin's
:ref:`gcc-with-cpychecker <cpychecker>` script:

   * http://sourceware.org/bugzilla/show_bug.cgi?id=13308
   * http://sourceware.org/bugzilla/show_bug.cgi?id=13309
   * http://sourceware.org/bugzilla/show_bug.cgi?id=13310
   * http://sourceware.org/bugzilla/show_bug.cgi?id=13316
   * http://sourceware.org/ml/gdb-patches/2011-06/msg00376.html
   * http://sourceware.org/ml/gdb-patches/2011-10/msg00391.html
   * http://sourceware.org/bugzilla/show_bug.cgi?id=13331

Tom Tromey also wrote specialized Python scripts to use the GCC plugin to
locate bugs within GDB.

One of his scripts analyzes gdb's resource-management code, which found some
resource leaks and a possible crasher:

   * http://sourceware.org/ml/gdb-patches/2011-06/msg00408.html

The other generates a whole-program call-graph, annotated with information
on gdb's own exception-handling mechanism.  A script then finds places where
these exceptions were not properly integrated with gdb's embedded Python
support:

   * http://sourceware.org/ml/gdb/2011-11/msg00002.html
   * http://sourceware.org/bugzilla/show_bug.cgi?id=13369


`LibreOffice <http://www.libreoffice.org/>`_
--------------------------------------------
Stephan Bergmann wrote a script to analyze LibreOffice's source code, detecting
a particular usage pattern of C++ method calls:

   * https://fedorahosted.org/pipermail/gcc-python-plugin/2011-December/000136.html
   * https://bugs.freedesktop.org/show_bug.cgi?id=43460

pycups
------
Bugs found in the `Python bindings for the CUPS API
<http://cyberelk.net/tim/software/pycups/>`_ by compiling it with the
plugin's :ref:`gcc-with-cpychecker <cpychecker>` script:

  * https://fedorahosted.org/pycups/ticket/17

python-krbV
-----------

Bug found in the `Python bindings for the Kerberos 5 API
<https://fedorahosted.org/python-krbV/>`_ by compiling it with the
plugin's :ref:`gcc-with-cpychecker <cpychecker>` script:

  * https://fedorahosted.org/python-krbV/ticket/1

Bugs found in itself
--------------------
Bugs found and fixed in the gcc Python plugin itself, by running the the
plugin's :ref:`gcc-with-cpychecker <cpychecker>` script when compiling another
copy:

   * various reference counting errors:

     * http://git.fedorahosted.org/git/?p=gcc-python-plugin.git;a=commitdiff;h=a9f48fac24a66c77007d99bf23f2eab188eb909e

     * http://git.fedorahosted.org/git/?p=gcc-python-plugin.git;a=commitdiff;h=2922ad81c8e0ea954d462433ecc83d86d9ebab68

   * bad format string: https://fedorahosted.org/pipermail/gcc-python-plugin/2011-August/000065.html

   * minor const-correctness error: http://git.fedorahosted.org/git/?p=gcc-python-plugin.git;a=commitdiff;h=4fe4a83288e04be35a96d0bfec332197fb32c358
