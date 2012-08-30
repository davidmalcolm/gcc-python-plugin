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

# Verify that we can lookup passes by name:
print("gcc.Pass.get_by_name('*build_cgraph_edges'): %r"
      % gcc.Pass.get_by_name('*build_cgraph_edges'))

# Verify that we can create new gcc.Pass subclasses

# Verify various forms of "gate" behavior:
class GimplePassWithoutGate(gcc.GimplePass):
    def execute(*args):
        print('within %s.execute%r' % (args[0].__class__.__name__, args))
ps = GimplePassWithoutGate(name='gimple-pass-without-gate')
print('registering: %r' % ps)
ps.register_after('cfg')


class GimplePassWithFalseGate(gcc.GimplePass):
    def gate(*args):
        print('within %s.gate%r' % (args[0].__class__.__name__, args))
        return False

    def execute(*args):
        # This shouldn't get called, since the gate returns False
        print('within %s.execute%r' % (args[0].__class__.__name__, args))

ps = GimplePassWithFalseGate(name='gimple-pass-with-false-gate')
print('registering: %r' % ps)
ps.register_after('cfg')


class GimplePassWithTrueGate(gcc.GimplePass):
    def gate(*args):
        print('within %s.gate%r' % (args[0].__class__.__name__, args))
        return True

    def execute(*args):
        print('within %s.execute%r' % (args[0].__class__.__name__, args))

ps = GimplePassWithTrueGate(name='gimple-pass-with-true-gate')
print('registering: %r' % ps)
ps.register_after('cfg')


class GimplePassWithErrorInGate(gcc.GimplePass):
    def gate(*args):
        print('within %s.gate%r' % (args[0].__class__.__name__, args))
        raise ValueError('example of a gate method raising an exception')

    def execute(*args):
        print('within %s.execute%r' % (args[0].__class__.__name__, args))

ps = GimplePassWithErrorInGate(name='gimple-pass-with-error-in-gate')
print('registering: %r' % ps)
ps.register_after('cfg')

# Verify "execute" behavior:

class GimplePassWithErrorInExecute(gcc.GimplePass):
    def execute(*args):
        print('within %s.execute%r' % (args[0].__class__.__name__, args))
        raise ValueError('example of an execute method raising an exception')

ps = GimplePassWithErrorInExecute(name='gimple-pass-with-error-in-exception')
print('registering: %r' % ps)
ps.register_after('cfg')


class GimplePassWithBadReturnFromExecute(gcc.GimplePass):
    def execute(*args):
        print('within %s.execute%r' % (args[0].__class__.__name__, args))
        return('hello world')

ps = GimplePassWithBadReturnFromExecute(name='gimple-pass-with-bad-return-from-execute')
print('registering: %r' % ps)
ps.register_after('cfg')


# Verify that we can create new subclasses of the other subclasses of gcc.Pass:
class MyRtlPass(gcc.RtlPass):
    def execute(*args):
        print('within MyRtlPass.execute%r' % (args, ))

ps = MyRtlPass(name='my-rtl-pass')
print('registering: %r' % ps)
ps.register_after('expand')


class MySimpleIpaPass(gcc.SimpleIpaPass):
    def execute(*args):
        print('within MySimpleIpaPass.execute%r' % (args, ))

ps = MySimpleIpaPass(name='my-simple-ipa-pass')
print('registering: %r' % ps)
ps.register_before('early_local_cleanups') # looks like we can only register within the top-level


class MyIpaPass(gcc.IpaPass):
    def execute(*args):
        print('within MyIpaPass.execute%r' % (args, ))

ps = MyIpaPass(name='my-ipa-pass')
print('registering: %r' % ps)
ps.replace('ipa-profile')


class GimplePassSettingLocation(gcc.GimplePass):
    def execute(*args):
        print('within %s.execute%r' % (args[0].__class__.__name__, args))
        gcc.set_location(args[1].end)
        raise ValueError('this should be at the end of the function')

ps = GimplePassSettingLocation(name='gimple-pass-setting-location')
print('registering: %r' % ps)
ps.register_after('cfg')

# Verify that the plugin doesn't crash when constructing a pass with
# an unrecognized kwarg:
class TestBogusKwargs(gcc.GimplePass):
    def __init__(self):
        gcc.GimplePass.__init__(self, 'test-bogus-kwargs')

try:
    ps = TestBogusKwargs(this_is_not_a_valid_kwarg=42)
except:
    pass
