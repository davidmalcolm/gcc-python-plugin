.. Copyright 2011, 2013 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011, 2013 Red Hat, Inc.

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

Version handling
================

.. py:function:: gcc.get_gcc_version()

   Get the gcc.Version for this version of GCC

.. py:function:: gcc.get_plugin_gcc_version()

   Get the gcc.Version that this plugin was compiled with

Typically the above will be equal (the plugin-loading mechanism currently
checks for this, and won't load the plugin otherwise).

On my machine, running this currently gives::

   gcc.Version(basever='4.6.0', datestamp='20110321', devphase='Red Hat 4.6.0-0.15', revision='', ...)


.. py:class:: gcc.Version

   Information on the version of GCC being run.  The various fields are
   accessible by name and by index.

   .. py:attribute:: basever

      (string) On my machine, this has value::

         '4.6.0'

   .. py:attribute:: datestamp

      (string) On my machine, this has value::

         '20110321'

   .. py:attribute:: devphase

      (string) On my machine, this has value::

          'Red Hat 4.6.0-0.15'

   .. py:attribute:: revision

      (string) On my machine, this is the empty string

   .. py:attribute:: configuration_arguments

      (string) On my machine, this has value::

         '../configure --prefix=/usr --mandir=/usr/share/man --infodir=/usr/share/info --with-bugurl=http://bugzilla.redhat.com/bugzilla --enable-bootstrap --enable-shared --enable-threads=posix --enable-checking=release --with-system-zlib --enable-__cxa_atexit --disable-libunwind-exceptions --enable-gnu-unique-object --enable-linker-build-id --enable-languages=c,c++,objc,obj-c++,java,fortran,ada,go,lto --enable-plugin --enable-java-awt=gtk --disable-dssi --with-java-home=/usr/lib/jvm/java-1.5.0-gcj-1.5.0.0/jre --enable-libgcj-multifile --enable-java-maintainer-mode --with-ecj-jar=/usr/share/java/eclipse-ecj.jar --disable-libjava-multilib --with-ppl --with-cloog --with-tune=generic --with-arch_32=i686 --build=x86_64-redhat-linux'


   Internally, this is a wrapper around a `struct plugin_gcc_version`

.. py:data:: gcc.GCC_VERSION

   (int) This corresponds to the value of GCC_VERSION within GCC's internal
   code: (MAJOR * 1000) + MINOR:

   ===========   ========================
   GCC version   Value of gcc.GCC_VERSION
   ===========   ========================
   4.6           4006
   4.7           4007
   4.8           4008
   ===========   ========================
