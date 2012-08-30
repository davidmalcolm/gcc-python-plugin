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

import os
import sys

from configbuilder import ConfigBuilder

class GccPythonPluginConfigBuilder(ConfigBuilder):
    def __init__(self, argv):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--gcc')
        parser.add_argument('--plugindir')
        args, argv = parser.parse_known_args(argv)
        ConfigBuilder.__init__(self, argv)
        self.gcc = args.gcc
        self.plugindir = args.plugindir

    def main(self):
        prefix = 'GCC_PYTHON_PLUGIN_CONFIG_'
        if self.plugindir:
            plugindir = self.plugindir
        else:
            plugindir = self.capture_shell_output('locating plugin directory for %s' % self.gcc,
                                            '%s --print-file-name=plugin' % self.gcc).strip()
        extraargs = ['-I%s' % os.path.join(plugindir, 'include')]
        self.test_for_mandatory_c_header('gcc-plugin.h', extraargs)
        self.test_c_compilation(initmsg='checking whether plugin.def defines PLUGIN_FINISH_DECL',
                              src='''
#include <gcc-plugin.h>

int i[PLUGIN_FINISH_DECL];
''',
                              extraargs=extraargs,
                              description='Does plugin.def define PLUGIN_FINISH_DECL?',
                              defn=prefix+'has_PLUGIN_FINISH_DECL')
        self.write_outcome()

ch = GccPythonPluginConfigBuilder(sys.argv)
ch.main()

