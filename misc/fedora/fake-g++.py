#!/usr/bin/env python
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

# Harness for forcibly invoking GCC with the cpychecker Python code within the python
# plugin
# 
# This code assumes that it is /usr/bin/g++ and that the real GCC has been
# moved to /usr/bin/the-real-g++
# 
# (This code runs under the regular Python interpreter, not within gcc)

import subprocess
import sys

# Enable the refcount-checker when running via this script
#
# We would use the regular keyword argument syntax:
#   verify_refcounting=True
# but unfortunately gcc's option parser seems to not be able to cope with '='
# within an option's value.  So we do it using dictionary syntax instead:
cmd = 'from libcpychecker import main; main(**{"verify_refcounting":True})'

args = ['the-real-g++',
        '-fplugin=python2',
	'-fplugin-arg-python2-command=%s' % cmd]
args += sys.argv[1:] # (the args we didn't consume)

# Beware of quoting: if the command is quoted within the Popen call, then
# Python interprets it as a string literal, and does nothing.
#
# But if invoking from a shell, you need quotes aroung the command
#
# To add to the fun, "gcc -v" emits it in unquoted form,
# which will need quotes added

if 0:
    print(' '.join(args))
p = subprocess.Popen(args)

try:
    r = p.wait()
except KeyboardInterrupt:
    r = 1
sys.exit(r)
