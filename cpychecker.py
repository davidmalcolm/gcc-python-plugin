try:
    import gcc
except ImportError:
    # Support being imported outside of gcc, by the unit tests
    pass

import sys

def log(msg):
    if 0:
        sys.stderr.write('%s\n' % msg)

import sys
sys.path.append('.') # FIXME
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


def get_types(richloc, strfmt):
    """
    Generate a list of C type names from a PyArg_ParseTuple format string
    Compare to Python/getargs.c:vgetargs1
    FIXME: only implements a subset of the various cases; no tuples yet etc
    """
    result = []
    i = 0
    while i < len(strfmt):
        c = strfmt[i]
        i += 1
        if i < len(strfmt):
            next = strfmt[i]
        else:
            next = None

        if c in ['(', ')']:
            continue

        if c in [':', ';']:
            break

        if c =='|':
            continue

        # From convertsimple:
        simple = {'b':'char',
                  'B':'char',
                  'h':'short',
                  'H':'short',
                  'i':'int',
                  'I':'int',
                  'n':'Py_ssize_t',
                  'l':'long',
                  'k':'unsigned long',
                  'L':'PY_LONG_LONG',
                  'K':'unsigned PY_LONG_LONG',
                  'f':'float',
                  'd':'double',
                  'D':'Py_complex',
                  'c':'char',
                  }
        if c in simple:
            result.append(simple[c] + ' *')

        elif c in ['s', 'z']: # string, possibly NULL/None
            if next == '#':
                if True: # FIXME: is PY_SSIZE_T_CLEAN defined?
                    result += ['const char * *', 'Py_ssize_t *']
                else:
                    result += ['const char * *', 'int *']
                i += 1
            elif next == '*':
                result.append('Py_buffer *')
                i += 1
            else:
                result.append('const char * *')
            # FIXME: seeing lots of (const char**) versus (char**) mismatches here
            # do we care?

        elif c == 'e':
            if next in ['s', 't']:
                result += ['const char *', 'char * *']
                i += 1
                if i < len(strfmt):
                    if strfmt[i] == '#':
                        result.append('int *')
                        i+=1
        elif c == 'S':
            result.append('PyObject * *')
        elif c == 'U':
            result.append('PyObject * *')
        elif c == 'O': # object
            if next == '!':
                result += ['PyTypeObject *', 'PyObject * *']
                i += 1
            elif next == '?':
                raise UnhandledCode(richloc, strfmt, c + next) # FIXME
            elif next == '&':
                # FIXME: can't really handle this case as is, fixing for fcntmodule.c
                result += ['int ( PyObject * object , int * target )',  # converter
                           'int *'] # FIXME, anything
                i += 1
            else:
                result.append('PyObject * *')
        elif c == 'w':
            if next == '#':
                result += ['char * *', 'Py_ssize_t *']
                i += 1
            elif next == '*':
                result.append('Py_buffer *')
                i += 1
            else:
                result.append('char * *')
        elif c == 't':
            if next == '#':
                result += ['char * *', 'int *']
                i += 1
        else:
            raise UnknownFormatChar(richloc, strfmt, c)
    return result
                              

class WrongNumberOfVars(FormatStringError):
    def __init__(self, fmt_string, exp_types, varargs):
        FormatStringError.__init__(self, fmt_string)
        self.exp_types = exp_types
        self.varargs = varargs

    def __str__(self):
        return '%s in call to %s with format string "%s" : expected %i extra arguments (%s), but got %i' % (
            self._get_desc_prefix(),
            'PyArg_ParseTuple',
            self.fmt_string,
            len(self.exp_types),
            ','.join([str(t) for t in self.exp_types]),
            len(self.varargs))

    def _get_desc_prefix(self):
        raise NotImplementedError

class NotEnoughVars(WrongNumberOfVars):
    def _get_desc_prefix(self):
        return 'Not enough arguments'

class TooManyVars(WrongNumberOfVars):
    def _get_desc_prefix(self):
        return 'Too many arguments'

class MismatchingType(FormatStringError):
    def __init__(self, fmt_string, arg_num, exp_type, vararg):
        super(self.__class__, self).__init__(fmt_string)
        self.arg_num = arg_num
        self.exp_type = exp_type
        self.vararg = vararg

    def __str__(self):
        return 'Mismatching type of argument %i in "%s": expected "%s" (pointing to %i bits) but got "%s" (pointing to %i bits)' % (
            self.arg_num,
            self.fmt_string,
            self.exp_type, self.exp_type.dereference.precision,
            self.vararg.type, self.vararg.operand.type.precision)

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
    log('vararg.operand.type.const: %r' % vararg.operand.type.const)
    log('vararg.operand.type.name: %r' % vararg.operand.type.name)
    log('vararg.operand.type.unsigned: %r' % vararg.operand.type.unsigned)
    log('vararg.operand.type.precision: %r' % vararg.operand.type.precision)
    log('dir(vararg.operand.type.name): %r' % dir(vararg.operand.type.name))
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
                    exp_types = get_types(stmt, fmt_string)
                except FormatStringError, exc:
                    error(exc)
                    return
                # log('types: %r' % exp_types)

                # ...then compare them against the actual types:
                varargs = stmt.args[2:]
                # log('varargs: %r' % varargs)
                if len(varargs) < len(exp_types):
                    gcc.permerror(loc, str(NotEnoughVars(fmt_string, exp_types, varargs)))
                    return

                if len(varargs) > len(exp_types):
                    gcc.permerror(loc, str(TooManyVars(fmt_string, exp_types, varargs)))
                    return

                for index, (exp_type, vararg) in enumerate(zip(exp_types, varargs)):
                    # FIXME: use the correct type, and it should be a ptr to it...
                    exp_type = gcc.Type.int().pointer
                    # ideally this shouldn't need calling; it should just be an attribute

                    if not type_equality(exp_type, vararg):
                        gcc.permerror(vararg.location,
                                      str(MismatchingType(fmt_string, index + 1, exp_type, vararg)))
    
    if fun.cfg:
        for bb in fun.cfg.basic_blocks:
            if isinstance(bb.gimple, list):
                for stmt in bb.gimple:
                    if isinstance(stmt, gcc.GimpleCall):
                        #log('stmt.fn: %s %r' % (stmt.fn, stmt.fn))
                        #log('stmt.fndecl: %s %r' % (stmt.fndecl, stmt.fndecl))
                        if stmt.fndecl.name == 'PyArg_ParseTuple':
                            check_callsite(stmt)

def on_pass_execution(optpass, fun):
    # Only run in one pass
    # FIXME: should we be adding our own pass for this?
    if optpass.name != '*warn_function_return':
        return

    log(fun)
    if fun:
        check_pyargs(fun)

if __name__ == '__main__':    
    gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                          on_pass_execution)
