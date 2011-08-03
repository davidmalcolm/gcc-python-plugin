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

# Logging

import gcc

logfile = None

def log(msg, indent=0):
    if 0:
        global logfile
        if not logfile:
            logfile = open(gcc.get_dump_base_name() + '.cpychecker-log.txt', 'w')
        logfile.write('%s%s\n' % ('  ' * indent, msg))
    if 0:
        sys.stderr.write('%s%s\n' % ('  ' * indent, msg))
