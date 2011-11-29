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

Gimple statements
=================

TODO

.. py:class:: gcc.Gimple

   A statement, in GCC's Gimple representation.

   The __str__ method is implemented using GCC's own pretty-printer for gimple,
   so e.g.::

      str(stmt)

   might return::

      'D.3259 = (long unsigned int) i;'

   .. py:attribute:: loc

      Source code location of this statement, as a :py:class:`gcc.Location` (or None)

   .. py:attribute:: block

      The lexical block holding this statement, as a :py:class:`gcc.Tree`

   .. py:attribute:: exprtype

      The type of the main expression computed by this statement, as a
      :py:class:`gcc.Tree` (which might be :py:class:`gcc.VoidType`)

   .. py:attribute:: str_no_uid

      A string representation of this statement, like str(), but without
      including any internal UIDs.

      This is intended for use in selftests that compare output against some
      expected value, to avoid embedding values that change into the expected
      output.

      For example, given an assignment to a
      temporary, the `str(stmt)` for the gcc.GimpleAssign might be::

         'D.3259 = (long unsigned int) i;'

      where the UID "3259" is liable to change from compile to compile, whereas
      the `stmt.str_no_uid` has value::

         'D.xxxx = (long unsigned int) i;'

      which won't arbitrarily change each time.

   .. py:method:: walk_tree(callback, *args, **kwargs)

      Visit all :py:class:`gcc.Tree` nodes associated with this
      statement, potentially more than once each.  This will visit both the
      left-hand-side and right-hand-side operands of the statement (if any),
      and recursively visit any of their child nodes.

      For each node, the callback is invoked, supplying the node, and any
      extra positional and keyword arguments passed to `walk_tree`::

         callback(node, *args, **kwargs)

      If the callback returns a true value, the traversal stops, and that
      :py:class:`gcc.Tree` is the result of the call to `walk_tree`.
      Otherwise, the traversal continues, and `walk_tree` eventually returns
      `None`.

.. py:class:: gcc.GimpleAssign

   Subclass of :py:class:`gcc.Gimple`: an assignment of an expression to an l-value

   .. py:attribute:: lhs

      Left-hand-side of the assignment, as a :py:class:`gcc.Tree`

   .. py:attribute:: rhs

      The operands on the right-hand-side of the expression, as a list of
      :py:class:`gcc.Tree` instances

   .. py:attribute:: exprcode

      The kind of the expression, as an :py:class:`gcc.Tree` subclass (the type
      itself, not an instance)

.. py:class:: gcc.GimpleCall

   Subclass of :py:class:`gcc.Gimple`: an invocation of a function, assigning
   the result to an l-value

   .. py:attribute:: lhs

      Left-hand-side of the assignment, as a :py:class:`gcc.Tree`

   .. py:attribute:: rhs

      The operands on the right-hand-side of the expression, as a list of
      :py:class:`gcc.Tree` instances

   .. py:attribute:: fn

      The function being called, as a :py:class:`gcc.Tree`

   .. py:attribute:: fndecl

      The  declaration of the function being called (if any), as a
      :py:class:`gcc.Tree`

   .. py:attribute:: args

      The arguments for the call, as a list of :py:class:`gcc.Tree`

   .. py:attribute:: noreturn

      (boolean) Has this call been marked as not returning?  (e.g. a call to
      `exit`)

.. py:class:: gcc.GimpleReturn

   Subclass of :py:class:`gcc.Gimple`: a "return" statement, signifying the end
   of a :py:class:`gcc.BasicBlock`

   .. py:attribute:: retval

   The return value, as a :py:class:`gcc.Tree`

.. py:class:: gcc.GimpleCond

   Subclass of :py:class:`gcc.Gimple`: a conditional jump, of the form::

     if (LHS EXPRCODE RHS) goto TRUE_LABEL else goto FALSE_LABEL

   .. py:attribute:: lhs

      Left-hand-side of the comparison, as a :py:class:`gcc.Tree`

   .. py:attribute:: exprcode

      The comparison predicate, as a :py:class:`gcc.Comparison` subclass (the
      type itself, not an instance).  For example, the gcc.GimpleCond statement
      for this fragment of C code::

         if (a == b)

      would have stmt.exprcode == gcc.EqExpr

   .. py:attribute:: rhs

      The right-hand-side of the comparison, as a :py:class:`gcc.Tree`

   .. py:attribute:: true_label

      The :py:class:`gcc.LabelDecl` node used as the jump target for when the
      comparison is true

   .. py:attribute:: false_label

      The :py:class:`gcc.LabelDecl` node used as the jump target for when the
      comparison is false

   Note that a C conditional of the form::

     if (some_int) {suiteA} else {suiteB}

   is implicitly expanded to::

     if (some_int != 0) {suiteA} else {suiteB}

   and this becomes a gcc.GimpleCond with `lhs` as the integer, `exprcode` as
   `<type 'gcc.NeExpr'>`, and `rhs` as `gcc.IntegerCst(0)`.

.. py:class:: gcc.GimplePhi

   Subclass of :py:class:`gcc.Gimple` used in the SSA passes: a "PHI" or
   "phoney" function, for merging the various possible values a variable can
   have based on the edge that we entered this :py:class:`gcc.BasicBlock` on.

   .. py:attribute:: lhs

      Left-hand-side of the assignment, as a :py:class:`gcc.Tree` (generally a
      :py:class:`gcc.SsaName`, I believe)

   .. py:attribute:: args

      A list of (:py:class:`gcc.Tree`, :py:class:`gcc.Edge`) pairs representing
      the possible (expr, edge) inputs

.. py:class:: gcc.GimpleSwitch

   Subclass of :py:class:`gcc.Gimple`: a switch statement, signifying the end of a
   :py:class:`gcc.BasicBlock`

   .. py:attribute:: indexvar

      The index variable used by the switch statement, as a :py:class:`gcc.Tree`

   .. py:attribute:: labels

      The labels of the switch statement, as a list of :py:class:`gcc.CaseLabelExpr`.

      The initial label in the list is always the default.

  .. Here's a dump of the class hierarchy, from help(gcc):
  ..    Gimple
  ..        GimpleAsm
  ..        GimpleAssign
  ..        GimpleBind
  ..        GimpleCall
  ..        GimpleCatch
  ..        GimpleCond
  ..        GimpleDebug
  ..        GimpleEhDispatch
  ..        GimpleEhFilter
  ..        GimpleEhMustNotThrow
  ..        GimpleErrorMark
  ..        GimpleGoto
  ..        GimpleLabel
  ..        GimpleNop
  ..        GimpleOmpAtomicLoad
  ..        GimpleOmpAtomicStore
  ..        GimpleOmpContinue
  ..        GimpleOmpCritical
  ..        GimpleOmpFor
  ..        GimpleOmpMaster
  ..        GimpleOmpOrdered
  ..        GimpleOmpParallel
  ..        GimpleOmpReturn
  ..        GimpleOmpSection
  ..        GimpleOmpSections
  ..        GimpleOmpSectionsSwitch
  ..        GimpleOmpSingle
  ..        GimpleOmpTask
  ..        GimplePhi
  ..        GimplePredict
  ..        GimpleResx
  ..        GimpleReturn
  ..        GimpleSwitch
  ..        GimpleTry
  ..        GimpleWithCleanupExpr
