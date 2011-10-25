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

# Verify that we can register custom attributes:

def attribute_callback_for_claims_mutex(*args):
    print('attribute_callback_for_claims_mutex called: args: %s' % (args, ))

def attribute_callback_for_releases_mutex(*args):
    print('attribute_callback_for_releases_mutex called: args: %s' % (args, ))

def register_our_attributes():
    gcc.register_attribute('claims_mutex',
                           1, 1,
                           False, False, False,
                           attribute_callback_for_claims_mutex)
    gcc.register_attribute('releases_mutex',
                           1, 1,
                           False, False, False,
                           attribute_callback_for_releases_mutex)

# Wire up our callback:
gcc.register_callback(gcc.PLUGIN_ATTRIBUTES,
                      register_our_attributes)

