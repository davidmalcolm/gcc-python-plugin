gcc.Tree and its subclasses
===========================

The various language front-ends for GCC emit "tree" structures (which I believe
are actually graphs), used throughout the rest of the internal representation of
the code passing through GCC.

.. py:class:: gcc.Tree

   A ``gcc.Tree`` is a wrapper around GCC's `tree` type

   .. py:attribute:: debug()

      Dump the tree to stderr, using GCC's own diagnostic routines

   .. py:attribute:: type

      Instance of :py:class:`gcc.Tree` giving the type of the node

   .. py:attribute:: addr

     (long) The address of the underlying GCC object in memory

There are numerous subclasses of gcc.Tree, each typically named after either
one of the `enum tree_code_class` or `enum tree_code` values, with the names
converted to Camel Case.

For example a :py:class:`gcc.Binary` is a wrapper around a `tree` of type
`tcc_binary`, and  a :py:class:`gcc.PlusExpr` is a wrapper around a `tree` of
type `PLUS_EXPR`.

Notable subclasses:

Blocks
------

.. py:class:: gcc.Block

   A symbol binding block, such as the global symbols within a compilation unit.

   .. py:attribute:: vars

      The list of :py:class:`gcc.Tree` for the declarations and labels in this
      block

Declarations
------------

.. py:class:: gcc.Declaration

   A subclass of `gcc.Tree` indicating a declaration

   Corresponds to the `tcc_declaration` value of `enum tree_code_class` within
   GCC's own C sources.

   .. py:attribute:: name

      (string) the name of this declaration


   .. py:attribute:: location

      The :py:class:`gcc.Location` for this declaration

Types
-----

.. py:class:: gcc.Type

   A subclass of `gcc.Tree` indicating a type

   Corresponds to the `tcc_type` value of `enum tree_code_class` within
   GCC's own C sources.

   .. py:attribute:: name

      (gcc.Type or None) the name of the type

   .. py:attribute:: pointer

      The :py:class:`gcc.PointerType` representing the `(this_type *)` type


   The standard C types are accessible via class methods of gcc.Type.
   They are only created by GCC after plugins are loaded, and so they're
   only visible during callbacks, not during the initial run of the code.
   (yes, having them as class methods is slightly clumsy).

   Each of the following returns a `gcc.Type` instance representing the given
   type (or None at startup before any passes, when the types don't yet exist)

      =============================  =====================
      Class method                   C Type
      =============================  =====================
      gcc.Type.void()                `void`
      gcc.Type.size_t()              `size_t`
      gcc.Type.char()                `char`
      gcc.Type.signed_char()         `signed char`
      gcc.Type.unsigned_char()       `unsigned char`
      gcc.Type.double()              `double`
      gcc.Type.float()               `float`
      gcc.Type.short()               `short`
      gcc.Type.unsigned_short()      `unsigned short`
      gcc.Type.int()                 `int`
      gcc.Type.unsigned_int()        `unsigned int`
      gcc.Type.long()                `long`
      gcc.Type.unsigned_long()       `unsigned long`
      gcc.Type.long_double()         `long double`
      gcc.Type.long_long()           `long long`
      gcc.Type.unsigned_long_long()  `unsigned long long`
      gcc.Type.int128()              `int128`
      gcc.Type.unsigned_int128()     `unsigned int128`
      gcc.Type.uint32()              `uint32`
      gcc.Type.uint64()              `uint64`
      =============================  =====================

.. py:class:: gcc.IntegerType

   Subclass of gcc.Type, adding a few properties:

   .. py:attribute:: unsigned

      (Boolean) True for 'unsigned', False for 'signed'

   .. py:attribute:: precision

      (int) The precision of this type in bits, as an int (e.g. 32)

   .. py:attribute:: signed_equivalent

      The gcc.IntegerType for the signed version of this type

   .. py:attribute:: unsigned_equivalent

      The gcc.IntegerType for the unsigned version of this type

.. py:class:: gcc.PointerType
.. py:class:: gcc.ArrayType
.. py:class:: gcc.VectorType

   .. py:attribute:: dereference

      The gcc.Type that this type points to

Additional attributes for various gcc.Type subclasses:

   .. py:attribute:: const

      (Boolean) Does this type have the `const` modifier?

   .. py:attribute:: const_equivalent

      The gcc.Type for the `const` version of this type

   .. py:attribute:: volatile

      (Boolean) Does this type have the `volatile` modifier?

   .. py:attribute:: volatile_equivalent

      The gcc.Type for the `volatile` version of this type

   .. py:attribute:: restrict

      (Boolean) Does this type have the `restrict` modifier?

   .. py:attribute:: restrict_equivalent

      The gcc.Type for the `restrict` version of this type

Constants
---------

.. py:class:: gcc.Constant

   A subclass of `gcc.Tree` indicating a constant value.

   Corresponds to the `tcc_constant` value of `enum tree_code_class` within
   GCC's own C sources.

   .. py:attribute:: constant

      The actual value of this constant, as the appropriate Python type:

      ==============================  ===============
      Subclass                        Python type
      ==============================  ===============
      .. py:class:: ComplexCst
      .. py:class:: FixedCst
      .. py:class:: IntegerCst        `int` or `long`
      .. py:class:: PtrmemCst
      .. py:class:: RealCst
      .. py:class:: StringCst         `str`
      .. py:class:: VectorCst
      ==============================  ===============


Binary Expressions
------------------

.. py:class:: gcc.Binary

   A subclass of `gcc.Tree` indicating a binary expression.

   Corresponds to the `tcc_binary` value of `enum tree_code_class` within
   GCC's own C sources.

   Has subclasses for the various kinds of binary expression.  These
   include:

   .. These tables correspond to GCC's "tree.def"

   Simple arithmetic:

      ============================    ======================  ==============
      Subclass                        C/C++ operators         enum tree_code
      ============================    ======================  ==============
      .. py:class:: gcc.PlusExpr      `+`                     PLUS_EXPR
      .. py:class:: gcc.MinusExpr     `-`                     MINUS_EXPR
      .. py:class:: gcc.MultExpr      `*`                     MULT_EXPR
      ============================    ======================  ==============

   Pointer addition:

      =================================    =================  =================
      Subclass                             C/C++ operators    enum tree_code
      =================================    =================  =================
      .. py:class:: gcc.PointerPlusExpr                       POINTER_PLUS_EXPR
      =================================    =================  =================

   Various division operations:

      ==============================  ===============
      Subclass                        C/C++ operators
      ==============================  ===============
      .. py:class:: gcc.TruncDivExr
      .. py:class:: gcc.CeilDivExpr
      .. py:class:: gcc.FloorDivExpr
      .. py:class:: gcc.RoundDivExpr
      ==============================  ===============

   The remainder counterparts of the above division operators:

      ==============================  ===============
      Subclass                        C/C++ operators
      ==============================  ===============
      .. py:class:: gcc.TruncModExpr
      .. py:class:: gcc.CeilModExpr
      .. py:class:: gcc.FloorModExpr
      .. py:class:: gcc.RoundModExpr
      ==============================  ===============

   Division for reals:

      ===================================  ======================
      Subclass                             C/C++ operators
      ===================================  ======================
      .. py:class:: gcc.RdivExpr
      ===================================  ======================

   Division that does not need rounding (e.g. for pointer subtraction in C):

      ===================================  ======================
      Subclass                             C/C++ operators
      ===================================  ======================
      .. py:class:: gcc.ExactDivExpr
      ===================================  ======================

   Max and min:

      ===================================  ======================
      Subclass                             C/C++ operators
      ===================================  ======================
      .. py:class:: gcc.MaxExpr
      .. py:class:: gcc.MinExpr
      ===================================  ======================

    Shift and rotate operations:

      ===================================  ======================
      Subclass                             C/C++ operators
      ===================================  ======================
      .. py:class:: gcc.LrotateExpr
      .. py:class:: gcc.LshiftExpr
      .. py:class:: gcc.RrotateExpr
      .. py:class:: gcc.RshiftExpr
      ===================================  ======================

   Bitwise binary expressions:

      ===================================  =========================
      Subclass                             C/C++ operators
      ===================================  =========================
      .. py:class:: gcc.BitAndExpr         `&`, `&=` (bitwise "and")
      .. py:class:: gcc.BitIorExpr         `|`, `|=` (bitwise "or")
      .. py:class:: gcc.BitXorExpr         `^`, `^=` (bitwise "xor")
      ===================================  =========================

  Other gcc.Binary subclasses:

      ========================================  ==================================
      Subclass                                  Usage
      ========================================  ==================================
      .. py:class:: gcc.CompareExpr
      .. py:class:: gcc.CompareGExpr
      .. py:class:: gcc.CompareLExpr
      .. py:class:: gcc.ComplexExpr
      .. py:class:: gcc.MinusNomodExpr
      .. py:class:: gcc.PlusNomodExpr
      .. py:class:: gcc.RangeExpr
      .. py:class:: gcc.UrshiftExpr
      .. py:class:: gcc.VecExtractevenExpr
      .. py:class:: gcc.VecExtractoddExpr
      .. py:class:: gcc.VecInterleavehighExpr
      .. py:class:: gcc.VecInterleavelowExpr
      .. py:class:: gcc.VecLshiftExpr
      .. py:class:: gcc.VecPackFixTruncExpr
      .. py:class:: gcc.VecPackSatExpr
      .. py:class:: gcc.VecPackTruncExpr
      .. py:class:: gcc.VecRshiftExpr
      .. py:class:: gcc.WidenMultExpr
      .. py:class:: gcc.WidenMultHiExpr
      .. py:class:: gcc.WidenMultLoExpr
      .. py:class:: gcc.WidenSumExpr
      ========================================  ==================================
 

Unary Expressions
-----------------


.. py:class:: gcc.Unary

   A subclass of `gcc.Tree` indicating a unary expression (i.e. taking a
   single argument).

   Corresponds to the `tcc_unary` value of `enum tree_code_class` within
   GCC's own C sources.

      ======================================  ==================================================
      Subclass                                Meaning; C/C++ operators
      ======================================  ==================================================
      .. py:class:: gcc.AbsExpr               Absolute value
      .. py:class:: gcc.AddrSpaceConvertExpr  Conversion of pointers between address spaces
      .. py:class:: gcc.BitNotExpr            `~` (bitwise "not")
      .. py:class:: gcc.CastExpr
      .. py:class:: gcc.ConjExpr              For complex types: complex conjugate
      .. py:class:: gcc.ConstCastExpr
      .. py:class:: gcc.ConvertExpr
      .. py:class:: gcc.DynamicCastExpr
      .. py:class:: gcc.FixTruncExpr          Convert real to fixed-point, via truncation
      .. py:class:: gcc.FixedConvertExpr
      .. py:class:: gcc.FloatExpr             Convert integer to real
      .. py:class:: gcc.NegateExpr            Unary negation
      .. py:class:: gcc.NoexceptExpr
      .. py:class:: gcc.NonLvalueExpr
      .. py:class:: gcc.NopExpr
      .. py:class:: gcc.ParenExpr
      .. py:class:: gcc.ReducMaxExpr
      .. py:class:: gcc.ReducMinExpr
      .. py:class:: gcc.ReducPlusExpr
      .. py:class:: gcc.ReinterpretCastExpr
      .. py:class:: gcc.StaticCastExpr
      .. py:class:: gcc.UnaryPlusExpr
      ======================================  ==================================================


Other expression subclasses
---------------------------

.. py:class:: gcc.Expression

   A subclass of `gcc.Tree` indicating an expression.

   Corresponds to the `tcc_expression` value of `enum tree_code_class` within
   GCC's own C sources.

   Subclasses include:

      =====================================  ======================
      Subclass                               C/C++ operators
      =====================================  ======================
      .. py:class:: gcc.AddrExpr
      .. py:class:: gcc.AlignofExpr
      .. py:class:: gcc.ArrowExpr
      .. py:class:: gcc.AssertExpr
      .. py:class:: gcc.AtEncodeExpr
      .. py:class:: gcc.BindExpr
      .. py:class:: gcc.CMaybeConstExpr
      .. py:class:: gcc.ClassReferenceExpr
      .. py:class:: gcc.CleanupPointExpr
      .. py:class:: gcc.CompoundExpr
      .. py:class:: gcc.CompoundLiteralExpr
      .. py:class:: gcc.CondExpr
      .. py:class:: gcc.CtorInitializer
      .. py:class:: gcc.DlExpr
      .. py:class:: gcc.DotProdExpr
      .. py:class:: gcc.DotstarExpr
      .. py:class:: gcc.EmptyClassExpr
      .. py:class:: gcc.ExcessPrecisionExpr
      .. py:class:: gcc.ExprPackExpansion
      .. py:class:: gcc.ExprStmt
      .. py:class:: gcc.FdescExpr
      .. py:class:: gcc.FmaExpr
      .. py:class:: gcc.InitExpr
      .. py:class:: gcc.MessageSendExpr
      .. py:class:: gcc.ModifyExpr
      .. py:class:: gcc.ModopExpr
      .. py:class:: gcc.MustNotThrowExpr
      .. py:class:: gcc.NonDependentExpr
      .. py:class:: gcc.NontypeArgumentPack
      .. py:class:: gcc.NullExpr
      .. py:class:: gcc.NwExpr
      .. py:class:: gcc.ObjTypeRef
      .. py:class:: gcc.OffsetofExpr
      .. py:class:: gcc.PolynomialChrec
      .. py:class:: gcc.PostdecrementExpr
      .. py:class:: gcc.PostincrementExpr
      .. py:class:: gcc.PredecrementExpr
      .. py:class:: gcc.PredictExpr
      .. py:class:: gcc.PreincrementExpr
      .. py:class:: gcc.PropertyRef
      .. py:class:: gcc.PseudoDtorExpr
      .. py:class:: gcc.RealignLoad
      .. py:class:: gcc.SaveExpr
      .. py:class:: gcc.ScevKnown
      .. py:class:: gcc.ScevNotKnown
      .. py:class:: gcc.SizeofExpr
      .. py:class:: gcc.StmtExpr
      .. py:class:: gcc.TagDefn
      .. py:class:: gcc.TargetExpr
      .. py:class:: gcc.TemplateIdExpr
      .. py:class:: gcc.ThrowExpr
      .. py:class:: gcc.TruthAndExpr
      .. py:class:: gcc.TruthAndifExpr
      .. py:class:: gcc.TruthNotExpr
      .. py:class:: gcc.TruthOrExpr
      .. py:class:: gcc.TruthOrifExpr
      .. py:class:: gcc.TruthXorExpr
      .. py:class:: gcc.TypeExpr
      .. py:class:: gcc.TypeidExpr
      .. py:class:: gcc.VaArgExpr
      .. py:class:: gcc.VecCondExpr
      .. py:class:: gcc.VecDlExpr
      .. py:class:: gcc.VecInitExpr
      .. py:class:: gcc.VecNwExpr
      .. py:class:: gcc.WidenMultMinusExpr
      .. py:class:: gcc.WidenMultPlusExpr
      .. py:class:: gcc.WithCleanupExpr
      .. py:class:: gcc.WithSizeExpr
      =====================================  ======================

TODO

  .. Here's a dump of the class hierarchy, from help(gcc):
  ..    Tree
  ..        ArgumentPackSelect
  ..        Baselink
  ..        Binary
  ..            BitAndExpr
  ..            BitIorExpr
  ..            BitXorExpr
  ..            CeilDivExpr
  ..            CeilModExpr
  ..            CompareExpr
  ..            CompareGExpr
  ..            CompareLExpr
  ..            ComplexExpr
  ..            ExactDivExpr
  ..            FloorDivExpr
  ..            FloorModExpr
  ..            LrotateExpr
  ..            LshiftExpr
  ..            MaxExpr
  ..            MinExpr
  ..            MinusExpr
  ..            MinusNomodExpr
  ..            MultExpr
  ..            PlusExpr
  ..            PlusNomodExpr
  ..            PointerPlusExpr
  ..            RangeExpr
  ..            RdivExpr
  ..            RoundDivExpr
  ..            RoundModExpr
  ..            RrotateExpr
  ..            RshiftExpr
  ..            TruncDivExpr
  ..            TruncModExpr
  ..            UrshiftExpr
  ..            VecExtractevenExpr
  ..            VecExtractoddExpr
  ..            VecInterleavehighExpr
  ..            VecInterleavelowExpr
  ..            VecLshiftExpr
  ..            VecPackFixTruncExpr
  ..            VecPackSatExpr
  ..            VecPackTruncExpr
  ..            VecRshiftExpr
  ..            WidenMultExpr
  ..            WidenMultHiExpr
  ..            WidenMultLoExpr
  ..            WidenSumExpr
  ..        Block
  ..        Comparison
  ..            EqExpr
  ..            GeExpr
  ..            GtExpr
  ..            LeExpr
  ..            LtExpr
  ..            LtgtExpr
  ..            NeExpr
  ..            OrderedExpr
  ..            UneqExpr
  ..            UngeExpr
  ..            UngtExpr
  ..            UnleExpr
  ..            UnltExpr
  ..            UnorderedExpr
  ..        Constant
  ..            ComplexCst
  ..            FixedCst
  ..            IntegerCst
  ..            PtrmemCst
  ..            RealCst
  ..            StringCst
  ..            VectorCst
  ..        Constructor
  ..        Declaration
  ..            ClassMethodDecl
  ..            ConstDecl
  ..            DebugExprDecl
  ..            FieldDecl
  ..            FunctionDecl
  ..            ImportedDecl
  ..            InstanceMethodDecl
  ..            KeywordDecl
  ..            LabelDecl
  ..            NamespaceDecl
  ..            ParmDecl
  ..            PropertyDecl
  ..            ResultDecl
  ..            TemplateDecl
  ..            TranslationUnitDecl
  ..            TypeDecl
  ..            UsingDecl
  ..            VarDecl
  ..        DefaultArg
  ..        ErrorMark
  ..        Expression
  ..            AddrExpr
  ..            AlignofExpr
  ..            ArrowExpr
  ..            AssertExpr
  ..            AtEncodeExpr
  ..            BindExpr
  ..            CMaybeConstExpr
  ..            ClassReferenceExpr
  ..            CleanupPointExpr
  ..            CompoundExpr
  ..            CompoundLiteralExpr
  ..            CondExpr
  ..            CtorInitializer
  ..            DlExpr
  ..            DotProdExpr
  ..            DotstarExpr
  ..            EmptyClassExpr
  ..            ExcessPrecisionExpr
  ..            ExprPackExpansion
  ..            ExprStmt
  ..            FdescExpr
  ..            FmaExpr
  ..            InitExpr
  ..            MessageSendExpr
  ..            ModifyExpr
  ..            ModopExpr
  ..            MustNotThrowExpr
  ..            NonDependentExpr
  ..            NontypeArgumentPack
  ..            NullExpr
  ..            NwExpr
  ..            ObjTypeRef
  ..            OffsetofExpr
  ..            PolynomialChrec
  ..            PostdecrementExpr
  ..            PostincrementExpr
  ..            PredecrementExpr
  ..            PredictExpr
  ..            PreincrementExpr
  ..            PropertyRef
  ..            PseudoDtorExpr
  ..            RealignLoad
  ..            SaveExpr
  ..            ScevKnown
  ..            ScevNotKnown
  ..            SizeofExpr
  ..            StmtExpr
  ..            TagDefn
  ..            TargetExpr
  ..            TemplateIdExpr
  ..            ThrowExpr
  ..            TruthAndExpr
  ..            TruthAndifExpr
  ..            TruthNotExpr
  ..            TruthOrExpr
  ..            TruthOrifExpr
  ..            TruthXorExpr
  ..            TypeExpr
  ..            TypeidExpr
  ..            VaArgExpr
  ..            VecCondExpr
  ..            VecDlExpr
  ..            VecInitExpr
  ..            VecNwExpr
  ..            WidenMultMinusExpr
  ..            WidenMultPlusExpr
  ..            WithCleanupExpr
  ..            WithSizeExpr
  ..        IdentifierNode
  ..        LambdaExpr
  ..        OmpClause
  ..        OptimizationNode
  ..        Overload
  ..        PlaceholderExpr
  ..        Reference
  ..            ArrayRangeRef
  ..            ArrayRef
  ..            AttrAddrExpr
  ..            BitFieldRef
  ..            ComponentRef
  ..            ImagpartExpr
  ..            IndirectRef
  ..            MemRef
  ..            MemberRef
  ..            OffsetRef
  ..            RealpartExpr
  ..            ScopeRef
  ..            TargetMemRef
  ..            UnconstrainedArrayRef
  ..            ViewConvertExpr
  ..        SsaName
  ..        Statement
  ..            AsmExpr
  ..            BreakStmt
  ..            CaseLabelExpr
  ..            CatchExpr
  ..            CleanupStmt
  ..            ContinueStmt
  ..            DeclExpr
  ..            DoStmt
  ..            EhFilterExpr
  ..            EhSpecBlock
  ..            ExitExpr
  ..            ExitStmt
  ..            ForStmt
  ..            GotoExpr
  ..            Handler
  ..            IfStmt
  ..            LabelExpr
  ..            LoopExpr
  ..            LoopStmt
  ..            OmpAtomic
  ..            OmpCritical
  ..            OmpFor
  ..            OmpMaster
  ..            OmpOrdered
  ..            OmpParallel
  ..            OmpSection
  ..            OmpSections
  ..            OmpSingle
  ..            OmpTask
  ..            RangeForStmt
  ..            ReturnExpr
  ..            StmtStmt
  ..            SwitchExpr
  ..            SwitchStmt
  ..            TryBlock
  ..            TryCatchExpr
  ..            TryFinally
  ..            UsingDirective
  ..            WhileStmt
  ..        StatementList
  ..        StaticAssert
  ..        TargetOptionNode
  ..        TemplateInfo
  ..        TemplateParmIndex
  ..        TraitExpr
  ..        TreeBinfo
  ..        TreeList
  ..        TreeVec
  ..        Type
  ..            ArrayType
  ..            BooleanType
  ..            BoundTemplateTemplateParm
  ..            CategoryImplementationType
  ..            CategoryInterfaceType
  ..            ClassImplementationType
  ..            ClassInterfaceType
  ..            ComplexType
  ..            DecltypeType
  ..            EnumeralType
  ..            FixedPointType
  ..            FunctionType
  ..            IntegerType
  ..            LangType
  ..            MethodType
  ..            NullptrType
  ..            OffsetType
  ..            PointerType
  ..            ProtocolInterfaceType
  ..            QualUnionType
  ..            RealType
  ..            RecordType
  ..            ReferenceType
  ..            TemplateTemplateParm
  ..            TemplateTypeParm
  ..            TypeArgumentPack
  ..            TypePackExpansion
  ..            TypenameType
  ..            TypeofType
  ..            UnboundClassTemplate
  ..            UnconstrainedArrayType
  ..            UnionType
  ..            VectorType
  ..            VoidType
  ..        Unary
  ..            AbsExpr
  ..            AddrSpaceConvertExpr
  ..            BitNotExpr
  ..            CastExpr
  ..            ConjExpr
  ..            ConstCastExpr
  ..            ConvertExpr
  ..            DynamicCastExpr
  ..            FixTruncExpr
  ..            FixedConvertExpr
  ..            FloatExpr
  ..            NegateExpr
  ..            NoexceptExpr
  ..            NonLvalueExpr
  ..            NopExpr
  ..            ParenExpr
  ..            ReducMaxExpr
  ..            ReducMinExpr
  ..            ReducPlusExpr
  ..            ReinterpretCastExpr
  ..            StaticCastExpr
  ..            UnaryPlusExpr
  ..            VecUnpackFloatHiExpr
  ..            VecUnpackFloatLoExpr
  ..            VecUnpackHiExpr
  ..            VecUnpackLoExpr
  ..        VlExp
  ..            AggrInitExpr
  ..            CallExpr

