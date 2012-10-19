#   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012 Red Hat, Inc.
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

# parser for ".sm" files

# Uses "ply", so we'll need python-ply on Fedora

from sm.checker import Checker, Sm, Decl, NamedPattern, StateClause, \
    PatternRule, \
    NamedPatternReference, SpecialPattern, OrPattern, \
    AssignmentFromLiteral, \
    ResultOfFnCall, ArgsOfFnCall, Comparison, VarDereference, ArrayLookup, \
    VarUsage, \
    TransitionTo, BooleanOutcome, PythonOutcome

############################################################################
# Tokenizer:
############################################################################
import ply.lex as lex

reserved = ['decl', 'sm', 'state', 'true', 'false',
            'any_pointer', 'any_expr', 'pat']
tokens = [
    'ID','LITERAL_NUMBER', 'LITERAL_STRING',
    'ACTION',
    'LBRACE','RBRACE', 'LPAREN', 'RPAREN', 'LSQUARE', 'RSQUARE',
    'COMMA', 'DOT',
    'COLON', 'SEMICOLON',
    'ASSIGNMENT', 'STAR', 'PIPE',
    'COMPARISON',
    'DOLLARPATTERN',
    'PYTHON',
    ] + [r.upper() for r in reserved]

def t_PYTHON(t):
    r'\{\{(.|\n)*?\}\}'
    # matched double-braces, with arbitrary text (and whitespace) inside:
    # Drop the double-braces:
    t.value = t.value[2:-2]
    return t

t_ACTION     = r'=>'
t_LPAREN     = r'\('
t_RPAREN     = r'\)'
t_LBRACE     = r'{'
t_RBRACE     = r'}'
t_LSQUARE     = r'\['
t_RSQUARE     = r'\]'
t_COMMA      = r','
t_DOT        = r'\.'
t_COLON      = r':'
t_SEMICOLON  = r';'
t_ASSIGNMENT = r'='
t_STAR       = r'\*'
t_PIPE       = r'\|'

def t_COMMENT(t):
    r'/\*(.|\n)*?\*/'
    # C-style comments
    # print('skipping comment: %r' % t)
    pass

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    # Check for reserved words:
    if t.value in reserved:
        t.type = t.value.upper()
    else:
        t.type = 'ID'
    return t

def t_COMPARISON(t):
    r'<=|<|==|!=|>=|>'
    return t

def t_LITERAL_NUMBER(t):
    r'(0x[0-9a-fA-F]+|\d+)'
    try:
        if t.value.startswith('0x'):
            t.value = long(t.value, 16)
        else:
            t.value = long(t.value)
    except ValueError:
        raise ParserError(t.value)
    return t

def t_LITERAL_STRING(t):
    r'"([^"]*)"|\'([^\']*)\''
    # Drop the quotes:
    t.value = t.value[1:-1]
    return t

def t_DOLLARPATTERN(t):
    r'\$[a-zA-Z_][a-zA-Z_0-9]*\$'
    # Drop the dollars:
    t.value = t.value[1:-1]
    return t

# Ignored characters
t_ignore = " \t\n"

def t_error(t):
    raise ParserError.from_token(t, "Illegal character '%s'" % t.value[0])

lexer = lex.lex()


############################################################################
# Grammar:
############################################################################
import ply.yacc as yacc

"""
precedence = (
    ('left', 'AND', 'OR'),
    ('left', 'NOT'),
    ('left', 'COMPARISON'),
)
"""

def p_checker(p):
    '''checker : sm
               | sm checker
    '''
    # top-level rule, covering the whole file: one or more sm clauses
    if len(p) == 2:
        p[0] = Checker([p[1]])
    else:
        p[0] = Checker([p[1]] + p[2].sms)

def p_sm(p):
    'sm : SM ID LBRACE smclauses RBRACE'
    p[0] = Sm(name=p[2], clauses=p[4])

def p_smclauses(p):
    '''smclauses : smclause
                    | smclauses smclause'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_empty(p):
    'empty :'
    pass

def p_optional_state(p):
    '''
    optional_state : STATE
                   | empty
    '''
    p[0] = p[1]

def p_declkind(p):
    '''
    declkind : ANY_POINTER
             | ANY_EXPR
    '''
    p[0] = p[1]

def p_smclause_decl(p):
    '''
    smclause : optional_state DECL declkind ID SEMICOLON
    '''
    # e.g. "state decl any_pointer ptr;"
    # e.g. "decl any_expr x;"
    has_state = (p[1] == 'state')
    declkind = p[3]
    name = p[4]
    p[0] = Decl.make(has_state, declkind, name)

def p_smclause_namedpatterndefinition(p):
    '''
    smclause : PAT ID pattern SEMICOLON
    '''
    p[0] = NamedPattern(name=p[2],
                        pattern=p[3])

def p_smclause_stateclause(p):
    'smclause : statelist COLON patternrulelist SEMICOLON'
    # e.g.
    #   ptr.unknown, ptr.null, ptr.nonnull:
    #      { ptr == 0 } => true=ptr.null, false=ptr.nonnull
    #    | { ptr != 0 } => true=ptr.nonnull, false=ptr.null
    #    ;
    #
    p[0] = StateClause(statelist=p[1], patternrulelist=p[3])

def p_statelist(p):
    '''statelist : statename
                 | statename COMMA statelist
    '''
    # e.g.
    #   ptr.unknown, ptr.null, ptr.nonnull
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[3]

def p_patternrulelist(p):
    '''patternrulelist : patternrule
                   | patternrule PIPE patternrulelist
    '''
    # e.g.
    #      { ptr == 0 } => true=ptr.null, false=ptr.nonnull
    #    | { ptr != 0 } => true=ptr.nonnull, false=ptr.null
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[3]

def p_statename(p):
    '''statename : ID DOT ID
                 | ID
    '''
    if len(p) == 4:
        p[0] = '%s.%s' % (p[1], p[3]) # FIXME
    else:
        p[0] = p[1]

# Various kinds of pattern:
def p_pattern_cpattern(p):
    '''
    pattern : LBRACE cpattern RBRACE
    '''
    # e.g.
    #   { ptr = malloc() }
    p[0] = p[2]

def p_pattern_namedpatternreference(p):
    '''
    pattern : ID
    '''
    # e.g.
    #   checked_against_0
    p[0] = NamedPatternReference(p[1])

def p_pattern_dollarpattern(p):
    '''
    pattern : DOLLARPATTERN
    '''
    # e.g.
    #   $leaked$
    p[0] = SpecialPattern.make(p[1])

def p_pattern_or(p):
    '''
    pattern : pattern PIPE pattern
    '''
    # e.g.
    #   $leaked$ | { x == 0 }
    p[0] = OrPattern(p[1], p[3])

def p_patternrule(p):
    '''
    patternrule : pattern ACTION outcomes
    '''
    # e.g. "{ ptr = malloc() } =>  ptr.unknown"
    # e.g. "$leaked$ => ptr.leaked"
    p[0] = PatternRule(pattern=p[1], outcomes=p[3])

# Various kinds of "cpattern":
def p_cpattern_assignment_from_literal(p):
    '''
    cpattern : ID ASSIGNMENT LITERAL_STRING
             | ID ASSIGNMENT LITERAL_NUMBER
    '''
    # e.g. "q = 0"
    p[0] = AssignmentFromLiteral(lhs=p[1], rhs=p[3])

def p_cpattern_result_of_fn_call(p):
    'cpattern : ID ASSIGNMENT ID LPAREN fncall_args RPAREN'
    # e.g. "ptr = malloc()"
    p[0] = ResultOfFnCall(lhs=p[1], fnname=p[3], args=p[5])

def p_fncall_arg(p):
    '''
    fncall_arg : ID
               | LITERAL_STRING
               | LITERAL_NUMBER
    '''
    p[0] = p[1]

def p_nonempty_fncall_args(p):
    '''
    nonempty_fncall_args : fncall_arg
                         | fncall_args COMMA fncall_arg
    '''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]

def p_fncall_args_from_nonempty(p):
    '''
    fncall_args : nonempty_fncall_args
    '''
    p[0] = p[1]

def p_fncall_args_from_empty(p):
    '''
    fncall_args : empty
    '''
    p[0] = []

def p_cpattern_arg_of_fn_call(p):
    'cpattern : ID LPAREN fncall_args RPAREN'
    # e.g. "free(ptr)"
    p[0] = ArgsOfFnCall(fnname=p[1], args=p[3])

def p_cpattern_comparison(p):
    '''
    cpattern : ID COMPARISON LITERAL_NUMBER
             | ID COMPARISON ID
    '''
    # e.g. "ptr == 0"
    p[0] = Comparison(lhs=p[1], op=p[2], rhs=p[3])

def p_cpattern_dereference(p):
    'cpattern : STAR ID'
    # e.g. "*ptr"
    p[0] = VarDereference(var=p[2])

def p_cpattern_arraylookup(p):
    'cpattern : ID LSQUARE ID RSQUARE'
    # e.g. "arr[x]"
    p[0] = ArrayLookup(array=p[1], index=p[3])

def p_cpattern_usage(p):
    'cpattern : ID'
    # e.g. "ptr"
    p[0] = VarUsage(var=p[1])

# The various outcomes when a pattern matches

def p_outcomes(p):
    '''outcomes : outcome
                | outcome COMMA outcomes'''
    # e.g. "ptr.unknown"
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[3]

def p_outcome_newstate(p):
    'outcome : statename'
    # e.g. "ptr.unknown"
    p[0] = TransitionTo(state=p[1])

def p_outcome_boolean_outcome(p):
    '''outcome : TRUE ASSIGNMENT outcome
               | FALSE ASSIGNMENT outcome'''
    # e.g. "true=ptr.null"
    p[0] = BooleanOutcome(guard=True if p[1] == 'true' else False,
                          outcome=p[3])

def p_outcome_python(p):
    'outcome : PYTHON'
    # e.g. "{ error('use of possibly-NULL pointer %s' % ptr)}"
    p[0] = PythonOutcome(src=p[1])

class ParserError(Exception):
    @classmethod
    def from_production(cls, p, val, msg):
        return ParserError(p.lexer.lexdata,
                           p.lexer.lexpos - len(val),
                           val,
                           msg)

    @classmethod
    def from_token(cls, t, msg="Parse error"):
        return ParserError(t.lexer.lexdata,
                           t.lexer.lexpos - len(str(t.value)),
                           t.value,
                           msg)

    def __init__(self, input_, pos, value, msg):
        self.input_ = input_
        self.filename = None
        self.pos = pos
        self.value = value
        self.msg = msg

        # Locate the line with the error:
        startidx = pos
        endidx = pos + len(str(value))
        while startidx >= 1 and input_[startidx - 1] != '\n':
            startidx -= 1
        while endidx < (len(input_) - 1) and input_[endidx + 1] != '\n':
            endidx += 1
        self.errline = input_[startidx:endidx]
        self.errpos = pos - startidx
        self.lineno = input_[:startidx].count('\n')

    def __str__(self):
        result = ('%s at "%s":\n%s\n%s'
                  % (self.msg, self.value,
                     self.errline,
                     ' '*self.errpos + '^'*len(str(self.value))))
        if self.filename:
            result = ('\n%s:%i:%i: %s'
                      % (self.filename,
                         self.lineno + 1, self.errpos + 1,
                         result))
        return result

def p_error(p):
    raise ParserError.from_production(p, p.value, 'Parser error')

############################################################################
# Interface:
############################################################################
# Entry points:
def parse_string(s):
    if 0:
        test_lexer(s)
    if 0:
        print(s)
    parser = yacc.yacc(debug=0, write_tables=0)
    ch = parser.parse(s)#, debug=1)
    ch.filename = None
    return ch

def parse_file(filename):
    parser = yacc.yacc(debug=0, write_tables=0)
    with open(filename) as f:
        s = f.read()
    try:
        ch = parser.parse(s)#, debug=1)
        ch.filename = filename
        return ch
    except ParserError, err:
        err.filename = filename
        raise err

def test_lexer(s):
    print(s)
    lexer.input(s)
    while True:
        tok = lexer.token()
        if not tok: break
        print tok

