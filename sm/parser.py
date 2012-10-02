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

# Query language for the heap

# Uses "ply", so we'll need python-ply on Fedora

# Split into tokenizer, then grammar, then external interface

from sm.checker import Checker, Sm, Var, StateClause, PatternRule, \
    SpecialPattern, \
    AssignmentFromLiteral, \
    ResultOfFnCall, ArgOfFnCall, Comparison, VarDereference, VarUsage, \
    TransitionTo, BooleanOutcome, PythonOutcome

############################################################################
# Tokenizer:
############################################################################
import ply.lex as lex

reserved = ['DECL', 'SM', 'STATE', 'TRUE', 'FALSE',
            'ANY_POINTER']
tokens = [
    'ID','LITERAL_NUMBER', 'LITERAL_STRING',
    'ACTION',
    'LBRACE','RBRACE', 'LPAREN', 'RPAREN',
    'COMMA', 'DOT',
    'COLON', 'SEMICOLON',
    'ASSIGNMENT', 'STAR', 'PIPE', 'PERCENT',
    'COMPARISON',
    'DOLLARPATTERN',
    ] + reserved

t_ACTION     = r'=>'
t_LPAREN     = r'\('
t_RPAREN     = r'\)'
t_LBRACE     = r'{'
t_RBRACE     = r'}'
t_COMMA      = r','
t_DOT        = r'\.'
t_COLON      = r':'
t_SEMICOLON  = r';'
t_ASSIGNMENT = r'='
t_STAR       = r'\*'
t_PIPE       = r'\|'
t_PERCENT    = r'%'


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    # Check for reserved words (case insensitive):
    if t.value.upper() in reserved:
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
t_ignore = " \t"

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

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
    'sm : SM ID LBRACE var stateclauses RBRACE'
    p[0] = Sm(name=p[2], varclauses=p[4], stateclauses=p[5])

def p_var(p):
    'var : STATE DECL ANY_POINTER ID SEMICOLON'
    # e.g. "state decl any_pointer ptr;"
    # FIXME: "state" is optional, and ANY_POINTER needs to change
    p[0] = Var(p[4])

def p_stateclauses(p):
    '''stateclauses : stateclause
                    | stateclauses stateclause'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_stateclause(p):
    'stateclause : statelist COLON patternrulelist SEMICOLON'
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

def p_patternrule(p):
    '''
    patternrule : LBRACE pattern RBRACE ACTION outcomes
                | DOLLARPATTERN ACTION outcomes
    '''
    # e.g. "{ ptr = malloc() } =>  ptr.unknown"
    # e.g. "$leaked$ => ptr.leaked"
    if p[1] == '{':
        p[0] = PatternRule(pattern=p[2], outcomes=p[5])
    else:
        p[0] = PatternRule(pattern=SpecialPattern.make(p[1]), outcomes=p[3])

# Various kinds of "pattern":
def p_pattern_assignment_from_literal(p):
    '''
    pattern : ID ASSIGNMENT LITERAL_STRING
            | ID ASSIGNMENT LITERAL_NUMBER
    '''
    # e.g. "q = 0"
    p[0] = AssignmentFromLiteral(lhs=p[1], rhs=p[3])

def p_pattern_result_of_fn_call(p):
    'pattern : ID ASSIGNMENT ID LPAREN RPAREN'
    # e.g. "ptr = malloc()"
    p[0] = ResultOfFnCall(lhs=p[1], func=p[3])

def p_pattern_arg_of_fn_call(p):
    'pattern : ID LPAREN ID RPAREN'
    # e.g. "free(ptr)"
    p[0] = ArgOfFnCall(func=p[1], arg=p[3])

def p_pattern_comparison(p):
    'pattern : ID COMPARISON LITERAL_NUMBER'
    # e.g. "ptr == 0"
    p[0] = Comparison(lhs=p[1], op=p[2], rhs=p[3])

def p_pattern_dereference(p):
    'pattern : STAR ID'
    # e.g. "*ptr"
    p[0] = VarDereference(var=p[2])

def p_pattern_usage(p):
    'pattern : ID'
    # e.g. "ptr"
    p[0] = VarUsage(var=p[1])

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
    'outcome : LBRACE python RBRACE'
    # e.g. "{ error('use of possibly-NULL pointer %s' % ptr)}"
    p[0] = PythonOutcome(src=p[2])

def p_python(p):
    'python : ID LPAREN LITERAL_STRING PERCENT ID RPAREN'
    # e.g. "error('use-after-free of %s' % ptr)"
    # (for now)
    p[0] = (p[1], p[2], p[3], p[4], p[5], p[6])

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

    def __str__(self):
        result = ('%s at "%s":\n%s\n%s'
                  % (self.msg, self.value,
                     self.errline,
                     ' '*self.errpos + '^'*len(str(self.value))))
        if self.filename:
            result = '%s: %s' % (self.filename, result)
        return result

def p_error(p):
    raise ParserError.from_token(p)

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
    return parser.parse(s)#, debug=1)

def parse_file(filename):
    parser = yacc.yacc(debug=0, write_tables=0)
    with open(filename) as f:
        s = f.read()
    try:
        return parser.parse(s)#, debug=1)
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

