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

.. py:class:: gcc.Binary

   A subclass of `gcc.Tree` indicating a binary expression.

   Corresponds to the `tcc_binary` value of `enum tree_code` within
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
 



.. py:class:: gcc.Unary

   A subclass of `gcc.Tree` indicating a unary expression (i.e. taking a
   single argument).

   Corresponds to the `tcc_unary` value of `enum tree_code` within
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

   Template:

      ===================================  ======================
      Subclass                             C/C++ operators
      ===================================  ======================
      ===================================  ======================

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

