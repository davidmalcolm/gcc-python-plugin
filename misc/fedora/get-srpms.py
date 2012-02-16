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
import re
from subprocess import Popen, PIPE
import urllib2

def get_srpms_for_installed_rpms():
    p = Popen(['rpm',
               '-q',
               '--qf=%{sourcerpm}\n',
               '--whatrequires',
               'libpython2.7.so.1.0()(64bit)'],
              stdout=PIPE)
    out, err = p.communicate()
    return sorted(set(out.splitlines()))

from lxml import etree
class ElementWrapper:
    def __init__(self, node):
        self._node = node

    # print(etree.tostring(doc, pretty_print=True))

    def __str__(self):
        return str(self._node)

def mktag_ns(raw):
    return '{http://linux.duke.edu/metadata/common}%s' % raw

def mktag_rpm(raw):
    return '{http://linux.duke.edu/metadata/rpm}%s' % raw

class RpmEntry(ElementWrapper):
    def get_name(self):
        return self._node.get('name')

class Package(ElementWrapper):
    def get_name(self):
        return self._node.find(mktag_ns('name')).text

    def get_location(self):
        return self._node.find(mktag_ns('location')).get('href')

    def get_format_node(self):
        return self._node.find(mktag_ns('format'))
    
    def get_requires(self):
        # Get a list of RpmEntry
        fmt_node = self.get_format_node()
        requires_node = fmt_node.find(mktag_rpm('requires'))
        if requires_node is None:
            return []
        return [RpmEntry(node)
                for node in requires_node.iterchildren(tag=mktag_rpm('entry'))]

    def has_requirement_by_name(self, pkgname):
        for req in self.get_requires():
            if pkgname == req.get_name():
                return True

    def get_source_rpm(self):
        fmt_node = self.get_format_node()
        return fmt_node.find(mktag_rpm('sourcerpm')).text

class DocWrapper:
    def __init__(self, doc):
        self._doc = doc

class YumPrimary(DocWrapper):
    @classmethod
    def from_file(cls, f):
        doc = etree.parse(f)
        return cls(doc)

    def get_metadata(self):
        return ElementWrapper(self._doc.getroot())

    def get_packages(self):
        for packagenode in self._doc.getroot():
            yield Package(packagenode)

def get_src_rpms():
    RPMS_FILENAME='SRPMS/9af2863661ee18b2fc70d804aabc8b316a8fc7bf8828d1e1d9a728d27da88939-primary.xml.gz'
    # downloaded from:
    #   http://download.fedora.devel.redhat.com/pub/fedora/linux/development/17/x86_64/os/repodata/9af2863661ee18b2fc70d804aabc8b316a8fc7bf8828d1e1d9a728d27da88939-primary.xml.gz
    result = set()
    yp = YumPrimary.from_file(RPMS_FILENAME)
    for pkg in yp.get_packages():
        if pkg.has_requirement_by_name('libpython2.7.so.1.0()(64bit)'):
            # print '%s is linked against python' % pkg.get_name()
            result.add(pkg.get_source_rpm())
    return sorted(result)


src_rpms = get_src_rpms()

from pprint import pprint
pprint(src_rpms)
print(len(src_rpms))

srpmnames = []
for src_rpm in src_rpms:
    m = re.match('(\S+)-(\S+)-(\S+).src.rpm', src_rpm)
    assert m
    n, v, r = m.groups()
    srpmnames.append(n)

pprint(srpmnames)

SRPMS_FILENAME='SRPMS/2473adda4950c13396b0f9e1424a6310ad96ffc34368b53f50617eab7627ae8a-primary.xml.gz'
# downloaded from:
#   http://download.fedora.devel.redhat.com/pub/fedora/linux/development/17/source/SRPMS/repodata/2473adda4950c13396b0f9e1424a6310ad96ffc34368b53f50617eab7627ae8a-primary.xml.gz

BASEURL='http://download.fedora.devel.redhat.com/pub/fedora/linux/development/17/source/SRPMS/'

yp = YumPrimary.from_file(SRPMS_FILENAME)
for pkg in sorted(yp.get_packages(),
                  lambda x, y: cmp(x.get_name(), y.get_name())):
    if pkg.get_name() in srpmnames:
        url = BASEURL + pkg.get_location()
        print url
        downloadpath = os.path.join('SRPMS', os.path.basename(url))
        if not os.path.exists(downloadpath):
            print downloadpath
            p = Popen(['wget', url, '-O', downloadpath])
            p.communicate()
