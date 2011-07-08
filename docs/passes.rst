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

.. For notes on how to document Python in RST form, see e.g.:
.. http://sphinx.pocoo.org/domains.html#the-python-domain

Optimization passes
===================

GCC organizes the optimization work it does as "passes", and these form trees:
passes can have both successors and child passes.

There are actually five "roots" to this tree:

   * The gcc.Pass holding :ref:`all "lowering" passes <all_lowering_passes>`,
     invoked per function within the callgraph, to turn high-level GIMPLE into
     lower-level forms (this wraps `all_lowering_passes` within gcc/passes.c).

   * The gcc.Pass holding :ref:`all "small IPA" passes <all_small_ipa_passes>`,
     working on the whole callgraph (IPA is "Interprocedural Analysis";
     `all_small_ipa_passes` within gcc/passes.c)

   * The gcc.Pass holding :ref:`all regular IPA passes <all_regular_ipa_passes>`
     (`all_regular_ipa_passes` within gcc/passes.c)

   * The gcc.Pass holding those :ref:`passes relating to link-time-optimization
     <all_lto_gen_passes>` (`all_lto_gen_passes` within gcc/passes.c)

   * The :ref:`"all other passes" gcc.Pass catchall <all_passes>`, holding the
     majority of the passes.  These are called on each function within the call
     graph (`all_passes`  within gcc/passes.c)

.. classmethod:: gcc.Pass.get_roots()

   Returns a tuple of `gcc.Pass` instances, giving the 5 top-level passes
   within GCC's tree of passes, in the order described above.

.. py:class:: gcc.Pass

   This wraps one of GCC's `struct opt_pass *`, but the wrapper class is still
   a work-in-progress.  Hopefully we'll eventually be able to subclass this and
   allow creating custom passes written in Python.

   Beware:  "pass" is a reserved word in Python, so use e.g. `ps` as a variable
   name for an instance of gcc.Pass

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

         =========================   ============================================   =========================
         Mask                        Meaning                                        Which pass sets this up?
         =========================   ============================================   =========================
         gcc.PROP_gimple_any         Is the full GIMPLE grammar allowed?            (the frontend)
         gcc.PROP_gimple_lcf         Has control flow been lowered?                 `"lower"`
         gcc.PROP_gimple_leh         Has exception-handling been lowered?           `"eh"`
         gcc.PROP_cfg                Does the gcc.Function have a non-None "cfg"?   `"cfg"`
         gcc.PROP_referenced_vars                                                   `"\*referenced_vars"`
         gcc.PROP_ssa                Is the GIMPLE in SSA form?                     `"ssa"`
         gcc.PROP_no_crit_edges                                                     `"crited"`
         gcc.PROP_rtl                Is the function now in RTL form? (rather       `"expand"`
	                             than GIMPLE-SSA)
         gcc.PROP_gimple_lomp                                                       `"omplower"`
         gcc.PROP_cfglayout                                                         `"into_cfglayout"`
         gcc.PROP_gimple_lcx                                                        `"cplxlower"`
         =========================   ============================================   =========================


There are four subclasses of gcc.Pass:

.. py:class:: gcc.GimplePass
.. py:class:: gcc.RtlPass
.. py:class:: gcc.SimpleIpaPass
.. py:class:: gcc.IpaPass

reflecting the internal data layouts within GCC's implementation of the
classes, but these don't do anything different yet at the Python level.

