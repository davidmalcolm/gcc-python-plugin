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
from libcpychecker.formatstrings import check_pyargs
from libcpychecker.utils import log
from libcpychecker.refcounts import check_refcounts, get_traces
from libcpychecker.attributes import register_our_attributes
from libcpychecker.initializers import check_initializers

class CpyCheckerGimplePass(gcc.GimplePass):
    """
    The custom pass that implements the per-function part of
    our extra compile-time checks
    """
    def __init__(self,
                 dump_traces=False,
                 show_traces=False,
                 verify_pyargs=True,
                 verify_refcounting=False,
                 show_possible_null_derefs=False):
        gcc.GimplePass.__init__(self, 'cpychecker-gimple')
        self.dump_traces = dump_traces
        self.show_traces = show_traces
        self.verify_pyargs = verify_pyargs
        self.verify_refcounting = verify_refcounting
        self.show_possible_null_derefs = show_possible_null_derefs

    def execute(self, fun):
        if fun:
            log('%s', fun)
            if self.verify_pyargs:
                check_pyargs(fun)

            # The refcount code is too buggy for now to be on by default:
            if self.verify_refcounting:
                check_refcounts(fun, self.dump_traces, self.show_traces,
                                self.show_possible_null_derefs)

class CpyCheckerIpaPass(gcc.SimpleIpaPass):
    """
    The custom pass that implements the whole-program part of
    our extra compile-time checks
    """
    def __init__(self):
        gcc.SimpleIpaPass.__init__(self, 'cpychecker-ipa')

    def execute(self):
        check_initializers()

def main(**kwargs):
    # Register our custom attributes:
    gcc.register_callback(gcc.PLUGIN_ATTRIBUTES,
                          register_our_attributes)

    # Register our GCC passes:
    gimple_ps = CpyCheckerGimplePass(**kwargs)
    if 1:
        # non-SSA version:
        gimple_ps.register_before('*warn_function_return')
    else:
        # SSA version:
        gimple_ps.register_after('ssa')

    ipa_ps = CpyCheckerIpaPass()
    ipa_ps.register_before('*free_lang_data')
