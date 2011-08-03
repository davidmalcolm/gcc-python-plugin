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


# Verify working with GCC's dump files

import gcc

pass_dumpfile = None
class TestPass(gcc.GimplePass):
    def execute(self, fun):
        global pass_dumpfile
        print('within TestPass.execute, for %r' % fun)
        pass_dumpfile = gcc.get_dump_file_name()
        if 0:
            print('pass_dumpfile: %r' % pass_dumpfile)

        # Dumping of strings:
        gcc.dump('hello world')

        # Dumping of other objects:
        gcc.dump(42)

ps = TestPass(name='test-pass')
print('registering: %r' % ps)
ps.register_after('cfg')

assert isinstance(ps.static_pass_number, int)
print('ps.dump_enabled: %r' % ps.dump_enabled)
print('Manually enabling dump for our pass:')
ps.dump_enabled = True
print('ps.dump_enabled: %r' % ps.dump_enabled)

# Now register another pass afterwards, to inspect the dumpfile
# for the previous pass:
class VerifyPass(gcc.GimplePass):
    def execute(self, fun):
        global pass_dumpfile
        print('within VerifyPass.execute, for %r' % fun)
        if 0:
            print('pass_dumpfile: %r' % pass_dumpfile)
        with open(pass_dumpfile) as f:
            content = f.read()
        print('--CONTENT OF DUMPFILE--')
        print(content)
        print('--END OF DUMPFILE--')

ps = VerifyPass(name='verify-pass')
print('registering: %r' % ps)
ps.register_after('test-pass')
