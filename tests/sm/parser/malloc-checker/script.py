# -*- coding: utf-8 -*-
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

import unittest

from sm.checker import Checker, Sm, Var, StateClause, PatternRule, \
    LeakedPattern, \
    ResultOfFnCall, ArgOfFnCall, Comparison, VarDereference, VarUsage, \
    TransitionTo, BooleanOutcome, PythonOutcome
from sm.parser import parse_string

#parse('tests/sm/parser/malloc-checker.sm')

class ParserTests(unittest.TestCase):
    def test_complex_example(self):
        ch = parse_string('''
sm malloc_checker {
  state decl any_pointer ptr;

  ptr.all:
    { ptr = malloc() } =>  ptr.unknown;

  ptr.unknown, ptr.null, ptr.nonnull:
      { ptr == 0 } => true=ptr.null, false=ptr.nonnull
    | { ptr != 0 } => true=ptr.nonnull, false=ptr.null
    ;

  ptr.unknown:
    { *ptr } => { error('use of possibly-NULL pointer %s' % ptr)};

  ptr.null:
    { *ptr } => { error('use of NULL pointer %s' % ptr)};

  ptr.all, ptr.unknown, ptr.null, ptr.nonnull:
    { free(ptr) } => ptr.free;

  ptr.free:
      { free(ptr) } => { error('double-free of %s' % ptr)}
    | { ptr } => {error('use-after-free of %s' % ptr)}
    ;

  ptr.unknown, ptr.nonnull:
      $leaked$ => { error('leak of %s' % ptr)};
}
''')
        self.assert_(isinstance(ch, Checker))
        # print(ch)
        self.assertEqual(len(ch.sms), 1)
        sm = ch.sms[0]
        self.assertEqual(sm.name, 'malloc_checker')
        self.assertEqual(sm.varclauses, Var('ptr'))

        self.assertEqual(len(sm.stateclauses), 7)

        # Verify parsing of:
        #   ptr.all:
        #     { ptr = malloc() } =>  ptr.unknown;
        sc = sm.stateclauses[0]
        self.assertEqual(sc.statelist, ['ptr.all'])
        self.assertEqual(len(sc.patternrulelist), 1)
        pr = sc.patternrulelist[0]
        self.assertEqual(pr.pattern,
                         ResultOfFnCall(lhs='ptr',
                                        func='malloc'))
        self.assertEqual(pr.outcomes,
                         [TransitionTo(state='ptr.unknown')])

        # Verify parsing of:
        #   ptr.unknown, ptr.null, ptr.nonnull:
        #       { ptr == 0 } => true=ptr.null, false=ptr.nonnull
        #     | { ptr != 0 } => true=ptr.nonnull, false=ptr.null
        #     ;
        sc = sm.stateclauses[1]
        self.assertEqual(sc.statelist,
                         ['ptr.unknown', 'ptr.null', 'ptr.nonnull'])
        self.assertEqual(len(sc.patternrulelist), 2)
        pr = sc.patternrulelist[0]
        self.assertEqual(pr.pattern, Comparison(lhs='ptr', op='==', rhs=0))
        self.assertEqual(pr.outcomes,
                         [BooleanOutcome(guard=True, outcome=TransitionTo(state='ptr.null')),
                          BooleanOutcome(guard=False, outcome=TransitionTo(state='ptr.nonnull'))])
        pr = sc.patternrulelist[1]
        self.assertEqual(pr.pattern, Comparison(lhs='ptr', op='!=', rhs=0))
        self.assertEqual(pr.outcomes,
                         [BooleanOutcome(guard=True, outcome=TransitionTo(state='ptr.nonnull')),
                          BooleanOutcome(guard=False, outcome=TransitionTo(state='ptr.null'))])


        # Verify parsing of:
        #   ptr.unknown:
        #     { *ptr } => { error('use of possibly-NULL pointer %s' % ptr)};
        sc = sm.stateclauses[2]
        self.assertEqual(sc.statelist,
                         ['ptr.unknown'])
        self.assertEqual(len(sc.patternrulelist), 1)
        pr = sc.patternrulelist[0]
        self.assertEqual(pr.pattern, VarDereference(var='ptr'))
        self.assertEqual(pr.outcomes,
                         [PythonOutcome(src=('error', '(', 'use of possibly-NULL pointer %s', '%', 'ptr', ')', ))])

        # Verify parsing of:
        #   ptr.null:
        #     { *ptr } => { error('use of NULL pointer %s' % ptr)};
        sc = sm.stateclauses[3]
        self.assertEqual(sc.statelist,
                         ['ptr.null'])
        self.assertEqual(len(sc.patternrulelist), 1)
        pr = sc.patternrulelist[0]
        self.assertEqual(pr.pattern, VarDereference(var='ptr'))
        self.assertEqual(pr.outcomes,
                         [PythonOutcome(src=('error', '(', 'use of NULL pointer %s', '%', 'ptr', ')', ))])

        # Verify parsing of:
        #   ptr.all, ptr.unknown, ptr.null, ptr.nonnull:
        #     { free(ptr) } => ptr.free;
        sc = sm.stateclauses[4]
        self.assertEqual(sc.statelist,
                         ['ptr.all', 'ptr.unknown', 'ptr.null', 'ptr.nonnull'])
        self.assertEqual(len(sc.patternrulelist), 1)
        pr = sc.patternrulelist[0]
        self.assertEqual(pr.pattern, ArgOfFnCall(func='free', arg='ptr'))
        self.assertEqual(pr.outcomes,
                         [TransitionTo(state='ptr.free')])

        # Verify parsing of:
        #   ptr.free:
        #       { free(ptr) } => { error('double-free of %s' % ptr)}
        #     | { ptr } => {error('use-after-free of %s' % ptr)}
        #     ;
        sc = sm.stateclauses[5]
        self.assertEqual(sc.statelist,
                         ['ptr.free'])
        self.assertEqual(len(sc.patternrulelist), 2)
        pr = sc.patternrulelist[0]
        self.assertEqual(pr.pattern, ArgOfFnCall(func='free', arg='ptr'))
        self.assertEqual(pr.outcomes,
                         [PythonOutcome(src=('error', '(', 'double-free of %s', '%', 'ptr', ')', ))])
        pr = sc.patternrulelist[1]
        self.assertEqual(pr.pattern, VarUsage(var='ptr'))
        self.assertEqual(pr.outcomes,
                         [PythonOutcome(src=('error', '(', 'use-after-free of %s', '%', 'ptr', ')', ))])

        # Verify parsing of:
        #   ptr.unknown, ptr.nonnull:
        #       $leaked$ => { error('leak of %s' % ptr)};
        sc = sm.stateclauses[6]
        self.assertEqual(sc.statelist,
                         ['ptr.unknown', 'ptr.nonnull'])
        self.assertEqual(len(sc.patternrulelist), 1)
        pr = sc.patternrulelist[0]
        self.assertEqual(pr.pattern, LeakedPattern())
        self.assertEqual(pr.outcomes,
                         [PythonOutcome(src=('error', '(', 'leak of %s', '%', 'ptr', ')', ))])

import sys
sys.argv = ['foo', '-v']

unittest.main()
