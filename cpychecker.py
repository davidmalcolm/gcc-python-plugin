try:
    import gcc
except ImportError:
    # Support being imported outside of gcc, by the unit tests
    pass

import sys

def log(msg):
    if 1:
        sys.stderr.write('%s\n' % msg)

def get_src_for_loc(loc):
    # Given a gcc.Location, get the source line as a string
    import linecache
    return linecache.getline(loc.file, loc.line).rstrip()


class CExtensionError(Exception):
    # Base class for errors discovered by static analysis in C extension code
    def __init__(self, location):
        self.location = location

    def __str__(self):
        return '%s:%s:%s:%s' % (self.location.file, 
                                self.location.line,
                                self.location.current_element,
                                self._get_desc())

    def _get_desc(self):
        # Hook for additional descriptive text about the error
        raise NotImplementedError

class FormatStringError(CExtensionError):
    def __init__(self, location, format_string):
        CExtensionError.__init__(self, location)
        self.format_string = format_string

class UnknownFormatChar(FormatStringError):
    def __init__(self, location, format_string, ch):
        FormatStringError.__init__(self, location, format_string)
        self.ch = ch

    def _get_desc(self):
        return "unknown format char in \"%s\": '%s'" % (self.format_string, self.ch)

class UnhandledCode(UnknownFormatChar):
    def _get_desc(self):
        return "unhandled format code in \"%s\": '%s' (FIXME)" % (self.format_string, self.ch)


def get_types(location, strfmt):
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
                raise UnhandledCode(location, strfmt, c + next) # FIXME
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
            raise UnknownFormatChar(location, strfmt, c)
    return result
                              

class WrongNumberOfVars(FormatStringError):
    def __init__(self, location, format_string, exp_types, num_args):
        FormatStringError.__init__(self, location, format_string)
        self.exp_types = exp_types
        self.num_args = num_args

class NotEnoughVars(WrongNumberOfVars):
    def _get_desc(self):
        return 'Not enough arguments in "%s" : expected %i (%s), but got %i' % (
            self.format_string,
            len(self.exp_types),
            self.exp_types,
            self.num_args)

class TooManyVars(WrongNumberOfVars):
    def _get_desc(self):
        return 'Too many arguments in "%s": expected %i (%s), but got %i' % (
            self.format_string,
            len(self.exp_types),
            self.exp_types,
            self.num_args)

class MismatchingType(FormatStringError):
    def __init__(self, location, format_string, arg_num, exp_type, actual_type):
        super(self.__class__, self).__init__(location, format_string)
        self.arg_num = arg_num
        self.exp_type = exp_type
        self.actual_type = actual_type

    def _get_desc(self):
        return 'Mismatching type of argument %i in "%s": expected "%s" but got "%s"' % (
            self.arg_num,
            self.format_string,
            self.exp_type,
            self.actual_type)

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
        log('stmt: %r %s' % (stmt, stmt))
        log('args: %r' % stmt.args)
        for arg in stmt.args:
            log('  arg: %s %r' % (arg, arg))

        # We expect the following args:
        #   args[0]: PyObject *input_tuple
        #   args[1]: char * format
        #   args[2...]: output pointers

        if len(stmt.args) > 1:
            fmt_string = get_format_string(stmt)
            if fmt_string:
                log('fmt_string: %r' % fmt_string)
                types = get_types(stmt.loc, fmt_string)
                log('types: %r' % types)
    
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
