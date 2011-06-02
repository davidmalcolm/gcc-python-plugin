Gimple statements
=================

.. py:currentmodule:: gcc

TODO

.. py:class:: gcc.Gimple

   .. py:attribute:: loc

      Source code location of this statement, as a :py:class:`gcc.Location` (or None)

   .. py:attribute:: block

      The lexical block holding this statement, as a gcc.Tree

   .. py:attribute:: exprtype

      The type of the main expression computed by this statement, as a gcc.Tree (which might be gcc.VoidType)

.. py:class:: gcc.GimpleAssign

   Subclass of :py:class:`gcc.Gimple`: an assignment of an expression to an l-value

   .. py:attribute:: lhs

      Left-hand-side of the assignment, as a gcc.Tree

   .. py:attribute:: rhs

      The operands on the right-hand-side of the expression, as a list of
      gcc.Tree instances

   .. py:attribute:: exprcode

      The kind of the expression, as an gcc.Tree subclass (the type itself, not
      an instance)

.. py:class:: gcc.GimpleCall

   Subclass of gcc.Gimple: an invocation of a function, assigning the result to an l-value

   .. py:attribute:: lhs

      Left-hand-side of the assignment, as a gcc.Tree

   .. py:attribute:: rhs

      The operands on the right-hand-side of the expression, as a list of
      gcc.Tree instances

   .. py:attribute:: fn

      The function being called, as a gcc.Tree

   .. py:attribute:: fndecl

      The  declaration of the function being called (if any), as a gcc.Tree

   .. py:attribute:: args

      The arguments for the call, as a list of gcc.Tree

.. py:class:: gcc.GimpleReturn

   Subclass of gcc.Gimple: a "return" statement, signifying the end of a `gcc.BasicBlock`

   .. py:attribute:: retval

   The return value, as a gcc.Tree

.. py:class:: gcc.GimpleCond

   Subclass of gcc.Gimple: an "if" statement, signifying the end of a `gcc.BasicBlock`

   .. py:attribute:: lhs

      Left-hand-side of the assignment, as a gcc.Tree

   .. py:attribute:: rhs

      The operands on the right-hand-side of the expression, as a list of
      gcc.Tree instances

   .. py:attribute:: exprcode

      The kind of the expression, as an gcc.Tree subclass (the type itself, not
      an instance)

.. py:class:: gcc.GimplePhi

   Subclass of gcc.Gimple used in the SSA passes: a "PHI" or "phoney" function,
   for merging the various possible values a variable can have based on the edge
   that we entered this :py:class:`gcc.BasicBlock` on.

   .. py:attribute:: lhs

      Left-hand-side of the assignment, as a gcc.Tree (generally a gcc.SsaName,
      I believe)

   .. py:attribute:: args

      A list of (:py:class:`gcc.Tree`, :py:class:`gcc.Edge`) pairs representing the possible (expr, edge) inputs

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
