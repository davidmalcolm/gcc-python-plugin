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

Notable subclasses:

.. py:class:: gcc.Binary

   A subclass of `gcc.Tree` indicating a binary expression.

   Corresponds to the `tcc_binary` value of `enum tree_code` within
   GCC's own C sources.

   Has subclasses for the various kinds of binary expression.  These
   include:

      ============================    ==============    ======================
      Subclass                        enum tree_code    C/C++ operators
      ============================    ==============    ======================
      .. py:class:: BitAndExpr        BIT_AND_EXPR      &, &=  (bitwise "and")
      .. py:class:: BitIorExpr
      .. py:class:: BitXorExpr
      .. py:class:: CeilDivExpr
      .. py:class:: CeilModExpr
      .. py:class:: CompareExpr
      .. py:class:: CompareGExpr
      .. py:class:: CompareLExpr
      .. py:class:: ComplexExpr
      .. py:class:: ExactDivExpr
      .. py:class:: FloorDivExpr
      .. py:class:: FloorModExpr
      .. py:class:: LrotateExpr
      .. py:class:: LshiftExpr
      .. py:class:: MaxExpr
      .. py:class:: MinExpr
      .. py:class:: MinusExpr
      .. py:class:: MinusNomodExpr
      .. py:class:: MultExpr
      .. py:class:: PlusExpr
      ============================    ==============    ======================



.. py:class:: gcc.Unary

   A subclass of `gcc.Tree` indicating a unary expression (i.e. taking a
   single argument).

   Corresponds to the `tcc_unary` value of `enum tree_code` within
   GCC's own C sources.

      ==================================    ========================    ========================
      Subclass                              enum tree_code              C/C++ operators
      ==================================    ========================    ========================
      .. py:class:: AbsExpr                 ABS_EXPR
      .. py:class:: AddrSpaceConvertExpr    ADDR_SPACE_CONVERT_EXPR
      .. py:class:: BitNotExpr              BIT_NOT_EXPR                ~ (bitwise "not")
      .. py:class:: CastExpr
      .. py:class:: ConjExpr
      .. py:class:: ConstCastExpr
      .. py:class:: ConvertExpr
      .. py:class:: DynamicCastExpr
      .. py:class:: FixTruncExpr
      .. py:class:: FixedConvertExpr
      .. py:class:: FloatExpr
      .. py:class:: NegateExpr
      .. py:class:: NoexceptExpr
      .. py:class:: NonLvalueExpr
      .. py:class:: NopExpr
      .. py:class:: ParenExpr
      .. py:class:: ReducMaxExpr
      .. py:class:: ReducMinExpr
      .. py:class:: ReducPlusExpr
      .. py:class:: ReinterpretCastExpr
      .. py:class:: StaticCastExpr
      .. py:class:: UnaryPlusExpr
      ==================================    ========================    ========================



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

