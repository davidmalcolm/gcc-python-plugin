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

# Verify the things the plugin exposes within the sys module
import sys
import os

assert hasattr(sys, 'plugin_full_name')
assert os.path.exists(sys.plugin_full_name)

assert hasattr(sys, 'plugin_base_name')
assert sys.plugin_base_name == 'python' # for now

# Verify that the plugin's directory is in sys.path, as an absolute path:
plugin_dir = os.path.abspath(os.path.dirname(sys.plugin_full_name))
assert plugin_dir in sys.path
