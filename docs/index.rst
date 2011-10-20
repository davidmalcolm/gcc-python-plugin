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

.. gcc-python-plugin documentation master file, created by
   sphinx-quickstart on Wed Jun  1 15:53:48 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

GCC Python plugin
=================

Contents:

.. toctree::
   :maxdepth: 2

   basics.rst
   gcc-overview.rst
   examples.rst
   working-with-c.rst
   cfg.rst
   tree.rst
   gimple.rst
   passes.rst
   cpychecker.rst
   success.rst
   misc.rst

This document describes the Python plugin I've written for GCC.  In theory the
plugin allows you to write Python scripts that can run inside GCC as it
compiles code, exposing GCC's internal data structures as a collection of
Python classes and functions.  The bulk of the document describes the Python API
it exposes.

Hopefully this will be of use for writing domain-specific warnings, static
analysers, and the like, and for rapid prototyping of new GCC features.

I've tried to stay close to GCC's internal representation, but using classes.
I hope that the resulting API is pleasant to work with.

The plugin is a work-in-progress; the API may well change.

Bear in mind that writing this plugin has been the first time I have worked
with the insides of GCC.  I have only wrapped the types I have needed, and
within them, I've only wrapped properties that seemed useful to me.  There may
well be plenty of interesting class and properties for instances that can be
added (patches most welcome!).  I may also have misunderstood how things work.

Caveat: I'm currently blithely ignoring GCC's garbage collector, which works for
now, but will probably lead to crashes if the collector runs.  I hope to fix
that soon.

Most of my development has been against Python 2 (2.7, actually), but I've tried
to make the source code of the plugin buildable against both Python 2 and
Python 3 (3.2), giving separate python2.so and python3.so plugins.  (I suspect
that it's only possible to use one or the other within a particular invocation
of "gcc", due to awkward dynamic-linker symbol collisions between the two
versions of Python).

The plugin is Free Software, licensed under the GPLv3 (or later).


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

