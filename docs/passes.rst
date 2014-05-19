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

.. For notes on how to document Python in RST form, see e.g.:
.. http://sphinx.pocoo.org/domains.html#the-python-domain

Optimization passes
===================

Working with existing passes
----------------------------
GCC organizes the optimization work it does as "passes", and these form trees:
passes can have both successors and child passes.

There are actually five "roots" to this tree:

   * The :py:class:`gcc.Pass` holding :ref:`all "lowering" passes <all_lowering_passes>`,
     invoked per function within the callgraph, to turn high-level GIMPLE into
     lower-level forms (this wraps `all_lowering_passes` within gcc/passes.c).

   * The :py:class:`gcc.Pass` holding :ref:`all "small IPA" passes <all_small_ipa_passes>`,
     working on the whole callgraph (IPA is "Interprocedural Analysis";
     `all_small_ipa_passes` within gcc/passes.c)

   * The :py:class:`gcc.Pass` holding :ref:`all regular IPA passes <all_regular_ipa_passes>`
     (`all_regular_ipa_passes` within gcc/passes.c)

   * The :py:class:`gcc.Pass` holding those :ref:`passes relating to link-time-optimization
     <all_lto_gen_passes>` (`all_lto_gen_passes` within gcc/passes.c)

   * The :ref:`"all other passes" gcc.Pass catchall <all_passes>`, holding the
     majority of the passes.  These are called on each function within the call
     graph (`all_passes`  within gcc/passes.c)

.. classmethod:: gcc.Pass.get_roots()

   Returns a 5-tuple of :py:class:`gcc.Pass` instances, giving the 5 top-level
   passes within GCC's tree of passes, in the order described above.

.. classmethod:: gcc.Pass.get_by_name(name)

   Get the :py:class:`gcc.Pass` instance for the pass with the given name,
   raising ValueError if it isn't found

.. py:class:: gcc.Pass

   This wraps one of GCC's `struct opt_pass *` instances.

   Beware:  "pass" is a reserved word in Python, so use e.g. `ps` as a variable
   name for an instance of :py:class:`gcc.Pass`

   .. py:attribute:: name

      The name of the pass, as a string

   .. py:attribute:: sub

      The first child pass of this pass (if any)

   .. py:attribute:: next

      The next sibling pass of this pass (if any)

   .. py:attribute:: properties_required
   .. py:attribute:: properties_provided
   .. py:attribute:: properties_destroyed

      Currently these are int bitfields, expressing the flow of data betweeen
      the various passes.

      They can be accessed using bitwise arithmetic::

          if ps.properties_provided & gcc.PROP_cfg:
	       print(fn.cfg)

      Here are the bitfield flags:

         =========================   ============================================   =========================   =======================
         Mask                        Meaning                                        Which pass sets this up?    Which pass clears this?
         =========================   ============================================   =========================   =======================
         gcc.PROP_gimple_any         Is the full GIMPLE grammar allowed?            (the frontend)              `"expand"`
         gcc.PROP_gimple_lcf         Has control flow been lowered?                 `"lower"`                   `"expand"`
         gcc.PROP_gimple_leh         Has exception-handling been lowered?           `"eh"`                      `"expand"`
         gcc.PROP_cfg                Does the gcc.Function have a non-None "cfg"?   `"cfg"`                     `"*free_cfg"`
         gcc.PROP_referenced_vars    Do we have data on which functions reference   `"\*referenced_vars"`       (none)
	                             which variables? (Dataflow analysis, aka
				     DFA).  This flag was removed in GCC 4.8
         gcc.PROP_ssa                Is the GIMPLE in SSA form?                     `"ssa"`                     `"expand"`
         gcc.PROP_no_crit_edges      Have all critical edges within the CFG been    `"crited"`                  (none)
                                     split?
         gcc.PROP_rtl                Is the function now in RTL form? (rather       `"expand"`                  `"*clean_state"`
	                             than GIMPLE-SSA)
         gcc.PROP_gimple_lomp        Have OpenMP directives been lowered into       `"omplower"`                `"expand"`
	                             explicit calls to the runtime library
				     (libgomp)
         gcc.PROP_cfglayout          Are we reorganizing the CFG into a more        `"into_cfglayout"`          `"outof_cfglayout"`
	                             efficient order?
         gcc.PROP_gimple_lcx         Have operations on complex numbers been        `"cplxlower"`               `"cplxlower0"`
	                             lowered to scalar operations?
         =========================   ============================================   =========================   =======================

   .. py:attribute:: static_pass_number

      (int) The number of this pass, used as a fragment of the dump file name.
      This is assigned automatically for custom passes.

   .. py:attribute:: dump_enabled

      (boolean) Is dumping enabled for this pass?  Set this attribute to `True`
      to enable dumping.  Not available from GCC 4.8 onwards

There are four subclasses of :py:class:`gcc.Pass`:

.. py:class:: gcc.GimplePass

   Subclass of :py:class:`gcc.Pass`, signifying a pass called per-function on
   the GIMPLE representation of that function.

.. py:class:: gcc.RtlPass

   Subclass of :py:class:`gcc.Pass`, signifying a pass called per-function on
   the RTL representation of that function.

.. py:class:: gcc.SimpleIpaPass

   Subclass of :py:class:`gcc.Pass`, signifying a pass called once (not
   per-function)

.. py:class:: gcc.IpaPass

   Subclass of :py:class:`gcc.Pass`, signifying a pass called once (not
   per-function)

.. _creating-new-passes:

Creating new optimization passes
--------------------------------
You can create new optimization passes.  This involves three steps:

   * subclassing the appropriate :py:class:`gcc.Pass` subclass (e.g.
     :py:class:`gcc.GimplePass`)

   * creating an instance of your subclass

   * registering the instance within the pass tree, relative to another pass

Here's an example::

   # Here's the (trivial) implementation of our new pass:
   class MyPass(gcc.GimplePass):
      # This is optional.
      # If present, it should return a bool, specifying whether or not
      # to execute this pass (and any child passes)
      def gate(self, fun):
          print('gate() called for %r' % fun)
          return True

      def execute(self, fun):
          print('execute() called for %r' % fun)

   # We now create an instance of the class:
   my_pass = MyPass(name='my-pass')

   # ...and wire it up, after the "cfg" pass:
   my_pass.register_after('cfg')

For :py:class:`gcc.GimplePass` and :py:class:`gcc.RtlPass`, the signatures of
`gate` and `execute` are:

   .. method:: gate(self, fun)
   .. method:: execute(self, fun)

where fun is a :py:class:`gcc.Function`.

For :py:class:`gcc.SimpleIpaPass` and :py:class:`gcc.IpaPass`, the signature
of `gate` and `execute` are:

   .. method:: gate(self)
   .. method:: execute(self)

.. warning::

   Unfortunately it doesn't appear to be possible to implement `gate()` for
   `gcc.IpaPass` yet; for now, the `gate()` method on such passes will not be
   called.  See http://gcc.gnu.org/bugzilla/show_bug.cgi?id=54959

If an unhandled exception is raised within `gate` or `execute`, it will lead
to a GCC error:

.. code-block:: pytb

   /home/david/test.c:36:1: error: Unhandled Python exception raised calling 'execute' method
   Traceback (most recent call last):
     File "script.py", line 79, in execute
      dot = gccutils.tree_to_dot(fun)
   NameError: global name 'gccutils' is not defined

.. method:: gcc.Pass.register_after(name [, instance_number=0 ])

   Given the name of another pass, register this :py:class:`gcc.Pass` to occur
   immediately after that other pass.

   If the other pass occurs multiple times, the pass will be inserted at the
   specified instance number, or at every instance, if supplied 0.

   .. note::

      The other pass must be of the same kind as this pass.  For example,
      if it is a subclass of :py:class:`gcc.GimplePass`, then this pass must
      also be a subclass of :py:class:`gcc.GimplePass`.

      If they don't match, GCC won't be able to find the other pass, giving
      an error like this::

         cc1: fatal error: pass 'ssa' not found but is referenced by new pass 'my-ipa-pass'

      where we attempted to register a :py:class:`gcc.IpaPass` subclass
      relative to 'ssa', which is a :py:class:`gcc.GimplePass`

.. method:: gcc.Pass.register_before(name [, instance_number=0 ])

   As above, but this pass is registered immediately before the referenced
   pass.

.. method:: gcc.Pass.replace(name [, instance_number=0 ])

   As above, but replace the given pass.  This method is included for
   completeness; the result is unlikely to work well.

Dumping per-pass information
----------------------------
GCC has a logging framework which supports per-pass logging ("dump files").

By default, no logging is done; dumping must be explicitly enabled.

Dumping of passes can be enabled from the command-line in groups:

   * `-fdump-tree-all` enables dumping for all :py:class:`gcc.GimplePass`
     (both builtin, and custom ones from plugins)

   * `-fdump-rtl-all` is similar, but for all :py:class:`gcc.RtlPass`

   * `-fdump-ipa-all` as above, but for all :py:class:`gcc.IpaPass` and
     :py:class:`gcc.SimpleIpaPass`

For more information, see
http://gcc.gnu.org/onlinedocs/gcc/Debugging-Options.html

It's not possible to directly enable dumping for a custom pass from the
command-line (it would require adding new GCC command-line options).  However,
your script *can* directly enable dumping for a custom pass by writing to the
`dump_enabled` attribute (perhaps in response to the arguments passed to
plugin, or a driver script).

If enabled for a pass, then a file is written to the same directory as the
output file, with a name based on the input file and the pass number.

For example, given a custom :py:class:`gcc.Pass` with name `'test-pass'`, then
when `input.c` is compiled to `build/output.o`::

   $ gcc -fdump-tree-all -o build/output.o src/input.c

then a dump file `input.c.225t.test-pass` will be written to the directory
`build`.  In this case, `225` is the `static_pass_number` field, `"t"`
signifies a tree pass, with the pass name appearing as the suffix.

.. py:function:: gcc.dump(obj)

   Write str() of the argument to the current dump file.  No newlines or other
   whitespace are added.

   Note that dumping is disabled by default; in this case, the call will do
   nothing.

.. py:function:: gcc.get_dump_file_name()

   Get the name of the current dump file.

   If called from within a pass for which dumping is enabled, it will return
   the filename in string form.

   If dumping is disabled for this pass, it will return `None`.

The typical output of a dump file will contain::

   ;; Function bar (bar)

   (dumped information when handling function bar goes here)

   ;; Function foo (foo)

   (dumped information when handling function foo goes here)

For example::

   class TestPass(gcc.GimplePass):
       def execute(self, fun):
           # Dumping of strings:
           gcc.dump('hello world')

           # Dumping of other objects:
           gcc.dump(42)

   ps = TestPass(name='test-pass')
   ps.register_after('cfg')
   ps.dump_enabled = True

would have a dump file like this::

   ;; Function bar (bar)

   hello world42
   ;; Function foo (foo)

   hello world42

Alternatively, it can be simpler to create your own logging system, given that
one can simply open a file and write to it.

.. py:function:: gcc.get_dump_base_name()

   Get the base file path and name prefix for GCC's dump files.

   You can use this when creating non-standard logfiles and other output.

   For example, the libcpychecker code can write HTML reports on
   reference-counting errors within a function, writing the output to a file
   named::

      filename = '%s.%s-refcount-errors.html' % (gcc.get_dump_base_name(),
                                                 fun.decl.name)

   given `fun`, a :py:class:`gcc.Function`.

   By default, this is the name of the input file, but within the output
   file's directory.  (It can be overridden using the `-dumpbase` command-line
   option).
