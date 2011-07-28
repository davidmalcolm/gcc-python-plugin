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

Register Transfer Language (RTL)
================================

.. py:class:: gcc.Rtl

  A wrapper around GCC's `struct rtx_def` type: an expression within GCC's
  Register Transfer Language

  .. py:attribute:: loc

     The :py:class:`gcc.Location` of this expression, or None

  .. py:attribute:: operands

     The operands of this expression, as a tuple.  The precise type of the
     operands will vary by subclass.

There are numerous subclasses.  However, this part of the API is much less
polished than the rest of the plugin.

  .. Here's a dump of the class hierarchy, from help(gcc):
  ..          Rtl
  ..              RtxAutoinc
  ..                  RtlPostDec
  ..                  RtlPostInc
  ..                  RtlPostModify
  ..                  RtlPreDec
  ..                  RtlPreInc
  ..                  RtlPreModify
  ..              RtxBinArith
  ..                  RtlAshift
  ..                  RtlAshiftrt
  ..                  RtlCompare
  ..                  RtlDiv
  ..                  RtlLshiftrt
  ..                  RtlMinus
  ..                  RtlMod
  ..                  RtlRotate
  ..                  RtlRotatert
  ..                  RtlSsAshift
  ..                  RtlSsDiv
  ..                  RtlSsMinus
  ..                  RtlUdiv
  ..                  RtlUmod
  ..                  RtlUsAshift
  ..                  RtlUsDiv
  ..                  RtlUsMinus
  ..                  RtlVecConcat
  ..                  RtlVecSelect
  ..              RtxBitfieldOps
  ..                  RtlSignExtract
  ..                  RtlZeroExtract
  ..              RtxCommArith
  ..                  RtlAnd
  ..                  RtlIor
  ..                  RtlMult
  ..                  RtlPlus
  ..                  RtlSmax
  ..                  RtlSmin
  ..                  RtlSsMult
  ..                  RtlSsPlus
  ..                  RtlUmax
  ..                  RtlUmin
  ..                  RtlUsMult
  ..                  RtlUsPlus
  ..                  RtlXor
  ..              RtxCommCompare
  ..                  RtlEq
  ..                  RtlLtgt
  ..                  RtlNe
  ..                  RtlOrdered
  ..                  RtlUneq
  ..                  RtlUnordered
  ..              RtxCompare
  ..                  RtlGe
  ..                  RtlGeu
  ..                  RtlGt
  ..                  RtlGtu
  ..                  RtlLe
  ..                  RtlLeu
  ..                  RtlLt
  ..                  RtlLtu
  ..                  RtlUnge
  ..                  RtlUngt
  ..                  RtlUnle
  ..                  RtlUnlt
  ..              RtxConstObj
  ..                  RtlConst
  ..                  RtlConstDouble
  ..                  RtlConstFixed
  ..                  RtlConstInt
  ..                  RtlConstVector
  ..                  RtlHigh
  ..                  RtlLabelRef
  ..                  RtlSymbolRef
  ..              RtxExtra
  ..                  RtlAddrDiffVec
  ..                  RtlAddrVec
  ..                  RtlAsmInput
  ..                  RtlAsmOperands
  ..                  RtlBarrier
  ..                  RtlCall
  ..                  RtlClobber
  ..                  RtlCodeLabel
  ..                  RtlCondExec
  ..                  RtlEhReturn
  ..                  RtlExprList
  ..                  RtlInsnList
  ..                  RtlNote
  ..                  RtlParallel
  ..                  RtlPrefetch
  ..                  RtlReturn
  ..                  RtlSequence
  ..                  RtlSet
  ..                  RtlStrictLowPart
  ..                  RtlSubreg
  ..                  RtlTrapIf
  ..                  RtlUnknown
  ..                  RtlUnspec
  ..                  RtlUnspecVolatile
  ..                  RtlUse
  ..                  RtlVarLocation
  ..              RtxInsn
  ..                  RtlCallInsn
  ..                  RtlDebugInsn
  ..                  RtlInsn
  ..                  RtlJumpInsn
  ..              RtxMatch
  ..                  RtlAddress
  ..              RtxObj
  ..                  RtlCc0
  ..                  RtlConcat
  ..                  RtlConcatn
  ..                  RtlConstString
  ..                  RtlDebugExpr
  ..                  RtlDebugImplicitPtr
  ..                  RtlLoSum
  ..                  RtlMem
  ..                  RtlPc
  ..                  RtlReg
  ..                  RtlScratch
  ..                  RtlValue
  ..              RtxTernary
  ..                  RtlFma
  ..                  RtlIfThenElse
  ..                  RtlVecMerge
  ..              RtxUnary
  ..                  RtlAbs
  ..                  RtlBswap
  ..                  RtlClz
  ..                  RtlCtz
  ..                  RtlFfs
  ..                  RtlFix
  ..                  RtlFloat
  ..                  RtlFloatExtend
  ..                  RtlFloatTruncate
  ..                  RtlFractConvert
  ..                  RtlNeg
  ..                  RtlNot
  ..                  RtlParity
  ..                  RtlPopcount
  ..                  RtlSatFract
  ..                  RtlSignExtend
  ..                  RtlSqrt
  ..                  RtlSsAbs
  ..                  RtlSsNeg
  ..                  RtlSsTruncate
  ..                  RtlTruncate
  ..                  RtlUnsignedFix
  ..                  RtlUnsignedFloat
  ..                  RtlUnsignedFractConvert
  ..                  RtlUnsignedSatFract
  ..                  RtlUsNeg
  ..                  RtlUsTruncate
  ..                  RtlVecDuplicate
  ..                  RtlZeroExtend
