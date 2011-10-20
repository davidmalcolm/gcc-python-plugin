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

gdb
---
Bugs found in gdb by running the cpychecker script when compiling it:
   * http://sourceware.org/bugzilla/show_bug.cgi?id=13308
   * http://sourceware.org/bugzilla/show_bug.cgi?id=13309
   * http://sourceware.org/bugzilla/show_bug.cgi?id=13310
   * http://sourceware.org/bugzilla/show_bug.cgi?id=13316
   * http://sourceware.org/ml/gdb-patches/2011-06/msg00376.html
   * http://sourceware.org/ml/gdb-patches/2011-10/msg00391.html

Tom Tromey also wrote a specialized Python script to analyze gdb's
resource-management code, which found some resource leaks and a possible
crasher:
   * http://sourceware.org/ml/gdb-patches/2011-06/msg00408.html
