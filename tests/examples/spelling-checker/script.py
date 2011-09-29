# -*- coding: utf-8 -*-
#   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011 Red Hat, Inc.
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

import gcc

# Use the Python bindings to the "enchant" spellchecker:
import enchant
spellingdict = enchant.Dict("en_US")

class SpellcheckingPass(gcc.GimplePass):
    def execute(self, fun):
        # This is called per-function during compilation:
        for bb in fun.cfg.basic_blocks:
            if bb.gimple:
                for stmt in bb.gimple:
                    stmt.walk_tree(self.spellcheck_node, stmt.loc)

    def spellcheck_node(self, node, loc):
        # Spellcheck any textual constants found within the node:
        if isinstance(node, gcc.StringCst):
            words = node.constant.split()
            for word in words:
                if not spellingdict.check(word):
                    # Warn about the spelling error (controlling the warning
                    # with the -Wall command-line option):
                    if gcc.warning(loc,
                                   gcc.Option('-Wall'),
                                   'Possibly misspelt word in string constant: %r' % word):
                        # and, if the warning was not suppressed at the command line, emit
                        # suggested respellings:
                        suggestions = spellingdict.suggest(word)
                        if suggestions:
                            gcc.inform(loc, 'Suggested respellings: %r' % ', '.join(suggestions))

ps = SpellcheckingPass(name='spellchecker')
ps.register_after('cfg')
