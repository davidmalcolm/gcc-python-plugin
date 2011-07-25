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

# Sample python script, to be run by our gcc plugin (see "make test")
# Show the SSA form of each function, using GraphViz
import gcc
from gccutils import get_src_for_loc, cfg_to_dot, invoke_dot

def my_pass_execution_callback(*args, **kwargs):
    #print('my_pass_execution_callback was called: args=%r  kwargs=%r' % (args, kwargs))
    #help(args[0])
    (optpass, fun) = args
    if not optpass.properties_required & (1<<5):
        return
    if fun:
        print('fun.cfg: %r' % fun.cfg)
        if fun.cfg:
            #print help(fun.cfg)
            print('fun.cfg.basic_blocks: %r' % fun.cfg.basic_blocks)
            print('fun.cfg.entry: %r' % fun.cfg.entry)
            print('fun.cfg.exit: %r' % fun.cfg.exit)
            print('fun.cfg.entry.succs: %r' % fun.cfg.entry.succs)
            print('fun.cfg.exit.preds: %r' % fun.cfg.exit.preds)
            
            dot = cfg_to_dot(fun.cfg, fun.decl.name)
            # print(dot)
            invoke_dot(dot)

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      my_pass_execution_callback)


