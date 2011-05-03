# Domain-specific warning:
#  Detecting errors in usage of the PyArg_ParseTuple API
#  
#  See http://docs.python.org/c-api/arg.html

import gcc

import sys

def log(msg):
    if 0:
        sys.stderr.write('%s\n' % msg)

from gccutils import get_src_for_loc

class CExtensionError(Exception):
    # Base class for errors discovered by static analysis in C extension code
    pass

class FormatStringError(CExtensionError):
    def __init__(self, fmt_string):
        self.fmt_string = fmt_string

class UnknownFormatChar(FormatStringError):
    def __init__(self, fmt_string, ch):
        FormatStringError.__init__(self, fmt_string)
        self.ch = ch

    def __str__(self):
        return "unknown format char in \"%s\": '%s'" % (self.fmt_string, self.ch)

class UnhandledCode(UnknownFormatChar):
    def __str__(self):
        return "unhandled format code in \"%s\": '%s' (FIXME)" % (self.fmt_string, self.ch)

        

def _type_of_simple_arg(arg):
    # Convert 1-character argument code to a gcc.Type, covering the easy cases
    #
    # Analogous to Python/getargs.c:convertsimple, this is the same order as
    # that function's "switch" statement:
    simple = {'b': gcc.Type.unsigned_char,
              'B': gcc.Type.unsigned_char,
              'h': gcc.Type.short,
              'H': gcc.Type.unsigned_short,
              'i': gcc.Type.int,
              'I': gcc.Type.unsigned_int,
              # 'n':'Py_ssize_t',
              'l': gcc.Type.long,
              'k': gcc.Type.unsigned_long,
              # 'L':'PY_LONG_LONG',
              # 'K':'unsigned PY_LONG_LONG',
              'f': gcc.Type.float,
              'd': gcc.Type.double,
              # 'D':'Py_complex',
              'c': gcc.Type.char,
              }
    if arg in simple:
        # FIXME: ideally this shouldn't need calling; it should just be an
        # attribute:
        return simple[arg]()

class PyArgParseArgument:
    """
    One fragment of the string arg to PyArg_ParseTuple and friends
    """
    def __init__(self, code, expected_types):
        self.code = code
        self.expected_types = expected_types

class PyArgParseFmt:
    """
    Python class representing the string arg to PyArg_ParseTuple and friends
    """
    def __init__(self, fmt_string):
        self.fmt_string = fmt_string
        self.args = []

    def add_argument(self, code, expected_types):
        self.args.append(PyArgParseArgument(code, expected_types))

    def num_expected(self):
        return len(list(self.iter_exp_types()))

    def iter_exp_types(self):
        """
        Yield a sequence of (PyArgParseArgument, gcc.Type) pairs, representing
        the expected types of the varargs
        """
        for arg in self.args:
            for exp_type in arg.expected_types:
                yield (arg, exp_type)

    @classmethod
    def from_string(cls, fmt_string):
        """
        Parse fmt_string, generating a PyArgParseFmt instance
        Compare to Python/getargs.c:vgetargs1
        FIXME: only implements a subset of the various cases; no tuples yet etc
        """
        result = PyArgParseFmt(fmt_string)
        i = 0
        while i < len(fmt_string):
            c = fmt_string[i]
            i += 1
            if i < len(fmt_string):
                next = fmt_string[i]
            else:
                next = None

            if c in ['(', ')']:
                continue

            if c in [':', ';']:
                break

            if c =='|':
                continue

            simple_type = _type_of_simple_arg(c)
            if simple_type:
                result.add_argument(c, [simple_type.pointer])

            elif c in ['s', 'z']: # string, possibly NULL/None
                if next == '#':
                    if True: # FIXME: is PY_SSIZE_T_CLEAN defined?
                        result.add_argument('c#', ['const char * *', 'Py_ssize_t *'])
                    else:
                        result.add_argument('c#', ['const char * *', 'int *'])
                    i += 1
                elif next == '*':
                    result.add_argument('c*', ['Py_buffer *'])
                    i += 1
                else:
                    result.add_argument('c', ['const char * *'])
                # FIXME: seeing lots of (const char**) versus (char**) mismatches here
                # do we care?

            elif c == 'e':
                if next in ['s', 't']:
                    arg = PyArgParseArgument('e' + next, ['const char *', 'char * *'])
                    i += 1
                    if i < len(fmt_string):
                        if fmt_string[i] == '#':
                            arg.code += '#'
                            arg.expected_types.append('int *')
                            i+=1
                    result.args.append(arg)
            elif c == 'S':
                result.add_argument('S', ['PyObject * *'])
            elif c == 'U':
                result.add_argument('U', ['PyObject * *'])
            elif c == 'O': # object
                if next == '!':
                    result += ['PyTypeObject *', 'PyObject * *']
                    i += 1
                elif next == '?':
                    raise UnhandledCode(richloc, fmt_string, c + next) # FIXME
                elif next == '&':
                    # FIXME: can't really handle this case as is, fixing for fcntmodule.c
                    result += ['int ( PyObject * object , int * target )',  # converter
                               'int *'] # FIXME, anything
                    i += 1
                else:
                    result.add_argument('O', ['PyObject * *'])
            elif c == 'w':
                if next == '#':
                    result += ['char * *', 'Py_ssize_t *']
                    i += 1
                elif next == '*':
                    result.add_argument('w*', ['Py_buffer *'])
                    i += 1
                else:
                    result.add_argument('w', ['char * *'])
            elif c == 't':
                if next == '#':
                    result.add_argument('t#', ['char * *', 'int *'])
                    i += 1
            else:
                raise UnknownFormatChar(fmt_string, c)
        return result

class ParsedFormatStringError(FormatStringError):
    def __init__(self, fmt):
        FormatStringError.__init__(self, fmt.fmt_string)
        self.fmt = fmt

class WrongNumberOfVars(ParsedFormatStringError):
    def __init__(self, fmt, varargs):
        ParsedFormatStringError.__init__(self, fmt)
        self.varargs = varargs

    def __str__(self):
        return '%s in call to %s with format string "%s" : expected %i extra arguments (%s), but got %i' % (
            self._get_desc_prefix(),
            'PyArg_ParseTuple',
            self.fmt.fmt_string,
            self.fmt.num_expected(),
            ','.join([str(exp_type) for (arg, exp_type) in self.fmt.iter_exp_types()]),
            len(self.varargs))

    def _get_desc_prefix(self):
        raise NotImplementedError

class NotEnoughVars(WrongNumberOfVars):
    def _get_desc_prefix(self):
        return 'Not enough arguments'

class TooManyVars(WrongNumberOfVars):
    def _get_desc_prefix(self):
        return 'Too many arguments'

class MismatchingType(ParsedFormatStringError):
    def __init__(self, fmt, arg_num, arg_fmt_string, exp_type, vararg):
        super(self.__class__, self).__init__(fmt)
        self.arg_num = arg_num
        self.arg_fmt_string = arg_fmt_string
        self.exp_type = exp_type
        self.vararg = vararg

    def __str__(self):
        def _describe_precision(t):
            if hasattr(t, 'precision'):
                return ' (pointing to %i bits)' % t.precision
            else:
                return ''

        def _describe_vararg(va):
            result = '"%s"' % va.type
            if hasattr(va, 'operand'):
                result += _describe_precision(va.operand.type)
            return result

        def _describe_exp_type(t):
            result = '"%s"' % t
            if hasattr(t, 'dereference'):
                result += _describe_precision(t.dereference)
            return result
            

        return (('Mismatching type in call to %s with format string "%s":'
                 ' argument %i ("%s") had type %s'
                 ' but was expecting %s for format code "%s"')
                % ("PyArg_ParseTuple", self.fmt.fmt_string,
                   self.arg_num, self.vararg, _describe_vararg(self.vararg),
                   _describe_exp_type(self.exp_type), self.arg_fmt_string))

def type_equality(exp_type, vararg):
    log('comparing exp_type: %s (%r) with vararg: %s (%r)' % (exp_type, exp_type, vararg, vararg))
    # FIXME:
    log(dir(vararg))
    log('vararg.type: %r' % vararg.type)
    log('vararg.operand: %r' % vararg.operand)
    # We expect a gcc.AddrExpr with operand gcc.Declaration
    log('dir(vararg.operand): %r' % dir(vararg.operand))
    log('vararg.operand.type: %r' % vararg.operand.type)
    # e.g. gcc.IntegerType
    log('vararg.operand.type: %s' % vararg.operand.type)
    log('dir(vararg.operand.type): %r' % dir(vararg.operand.type))
    if hasattr(vararg.operand.type, 'const'):
        log('vararg.operand.type.const: %r' % vararg.operand.type.const)
    log('vararg.operand.type.name: %r' % vararg.operand.type.name)
    if hasattr(vararg.operand.type, 'unsigned'):
        log('vararg.operand.type.unsigned: %r' % vararg.operand.type.unsigned)
    if hasattr(vararg.operand.type, 'precision'):
        log('vararg.operand.type.precision: %r' % vararg.operand.type.precision)
        log('dir(vararg.operand.type.name): %r' % dir(vararg.operand.type.name))
    if vararg.operand.type.name:
        log('vararg.operand.type.name.location: %r' % vararg.operand.type.name.location)

    log('exp_type: %r' % exp_type)
    log('exp_type: %s' % exp_type)
    #log('exp_type.unsigned: %r' % exp_type.unsigned)
    #log('exp_type.precision: %s' % exp_type.precision)
    log(dir(gcc.Type))

    if vararg.type != exp_type:
        return False

    # where are the builtin types? 
    # I see /usr/src/debug/gcc-4.6.0-20110321/obj-x86_64-redhat-linux/gcc/i386-builtin-types.inc
    # has e.g.:
    #   ix86_builtin_type_tab[(int)IX86_BT_INT] = integer_type_node,
    # and these seem to be set up in:  build_common_tree_nodes (bool signed_char)
    # in tree.c
    #   build_common_builtin_nodes uses:
    #       built_in_decls[code] = decl;
    #       implicit_built_in_decls[code] = decl;
    #  and many of these are just macros in tree.h, looking in here:
    #    extern GTY(()) tree integer_types[itk_none];

    return True

def check_pyargs(fun):
    def get_format_string(stmt):
        fmt_code = stmt.args[1]
        # We can only cope with the easy case, when it's a AddrExpr(StringCst())
        # i.e. a reference to a string constant, i.e. a string literal in the C
        # source:
        if isinstance(fmt_code, gcc.AddrExpr):
            operand = fmt_code.operand
            if isinstance(operand, gcc.StringCst):
                return operand.constant

    def check_callsite(stmt):
        log('got call at %s' % stmt.loc)
        log(get_src_for_loc(stmt.loc))
        # log('stmt: %r %s' % (stmt, stmt))
        # log('args: %r' % stmt.args)
        # for arg in stmt.args:
        #    # log('  arg: %s %r' % (arg, arg))
            

        # We expect the following args:
        #   args[0]: PyObject *input_tuple
        #   args[1]: char * format
        #   args[2...]: output pointers

        if len(stmt.args) > 1:
            fmt_string = get_format_string(stmt)
            if fmt_string:
                log('fmt_string: %r' % fmt_string)

                loc = stmt.loc

                # Figure out expected types, based on the format string...
                try:
                    fmt = PyArgParseFmt.from_string(fmt_string)
                except FormatStringError, exc:
                    gcc.permerror(stmt.loc, str(exc))
                    return
                log('fmt: %r' % fmt.args)

                exp_types = list(fmt.iter_exp_types())
                log('exp_types: %r' % exp_types)

                # ...then compare them against the actual types:
                varargs = stmt.args[2:]
                # log('varargs: %r' % varargs)
                if len(varargs) < len(exp_types):
                    gcc.permerror(loc, str(NotEnoughVars(fmt, varargs)))
                    return

                if len(varargs) > len(exp_types):
                    gcc.permerror(loc, str(TooManyVars(fmt, varargs)))
                    return

                for index, ((exp_arg, exp_type), vararg) in enumerate(zip(exp_types, varargs)):
                    if not type_equality(exp_type, vararg):
                        gcc.permerror(vararg.location,
                                      str(MismatchingType(fmt, index + 3, exp_arg.code, exp_type, vararg)))
    
    if fun.cfg:
        for bb in fun.cfg.basic_blocks:
            if isinstance(bb.gimple, list):
                for stmt in bb.gimple:
                    if isinstance(stmt, gcc.GimpleCall):
                        #log('stmt.fn: %s %r' % (stmt.fn, stmt.fn))
                        #log('stmt.fndecl: %s %r' % (stmt.fndecl, stmt.fndecl))
                        if stmt.fndecl.name == 'PyArg_ParseTuple':
                            check_callsite(stmt)

