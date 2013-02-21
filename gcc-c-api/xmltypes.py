# Autogenerate a header file from a .h description
import sys
import unittest
import xml.etree.ElementTree as ET

class TypeNotFound(Exception):
    def __init__(self, xmlname):
        self.xmlname = xmlname
    def __str__(self):
        return 'type named %r not found' % self.xmlname

class ApiRegistry:
    def __init__(self):
        self.apis = []

    def load(self, filename):
        api = Api(self, filename)

    def iter_types(self):
        for api in self.apis:
            for type_ in api.iter_types():
                yield type_

    def lookup_type(self, xmlname):
        for api in self.apis:
            type_ = api.lookup_type(xmlname)
            if type_:
                return type_
        raise TypeNotFound(xmlname)

class XmlWrapper:
    def __init__(self, api, node):
        self.api = api
        self.node = node

    def __eq__(self, other):
        if not isinstance(other, XmlWrapper):
            return False
        return self.node == other.node

class HasDocsMixin:
    def get_doc(self):
        xml_doc = self.node.find('doc')
        if xml_doc is not None:
            return Doc(self.api, xml_doc)
        else:
            return None

class Type(XmlWrapper, HasDocsMixin):
    def get_xml_name(self):
        return self.node.get('name')

    def get_c_name(self):
        return 'gcc_%s' % self.get_xml_name()

    def get_c_prefix(self):
        return 'gcc_%s' % self.get_xml_name()

    def get_base(self):
        basename = self.node.get('base')
        if basename:
            return self.api.registry.lookup_type(basename)

    def get_bases(self):
        basename = self.node.get('base')
        if basename:
            base = self.api.registry.lookup_type(basename)
            yield base
            for base in base.get_bases():
                yield base

    def get_subclasses(self, recursive=False):
        # brute force linear search for now:
        for type_ in self.api.registry.iter_types():
            base = type_.get_base()
            if base == self:
                yield type_
                if recursive:
                    for type_ in type_.get_subclasses(recursive):
                        yield type_

    def get_varname(self):
        varname = self.node.get('varname')
        if varname:
            return varname
        base = self.get_base()
        return base.get_varname()

    def get_inner_type(self):
        inner = self.node.get('inner')
        if inner:
            return inner
        base = self.get_base()
        if base:
            return base.get_inner_type()
        else:
            class NoInnerType(Exception):
                def __init__(self, type_):
                    self.type_ = type_
                def __str__(self):
                    return ('%s has no inheritable "inner" attribute'
                            % self.type_.get_xml_name())
            raise NoInnerType(self)

    def iter_attrs(self):
        for node in self.node.iter(tag='attribute'):
            yield Attribute(self.api, node)

    def iter_iters(self):
        for node in self.node.iter(tag='iterator'):
            yield Iterator(self.api, node)

class Attribute(XmlWrapper, HasDocsMixin):
    def get_xml_name(self):
        return self.node.get('name')

    def get_c_name(self):
        return self.get_xml_name()

    def get_xml_kind(self):
        return self.node.get('kind')

    def get_c_type(self):
        xml_kind = self.get_xml_kind()
        if xml_kind in ('int', 'bool'):
            return xml_kind
        if xml_kind == 'string':
            return 'const char*'
        return 'gcc_%s' % xml_kind

    def get_varname(self):
        xml_kind = self.get_xml_kind()
        if xml_kind == 'int':
            return 'i'
        if xml_kind == 'bool':
            return 'flag'
        if xml_kind == 'string':
            return 'str'
        return self.api.registry.lookup_type(xml_kind).get_varname()

    def get_access(self):
        access = self.node.get('access')
        if access:
            return access
        else:
            return 'r' # default to readonly

    def is_writable(self):
        access = self.get_access()
        return 'w' in access

    def is_readable(self):
        access = self.get_access()
        return 'r' in access

class Iterator(XmlWrapper, HasDocsMixin):
    def get_xml_name(self):
        return self.node.get('name')

    def get_c_name(self):
        return self.get_xml_name()

    def get_type(self):
        xmlkind = self.node.get('kind')
        return self.api.registry.lookup_type(xmlkind)

class Doc(XmlWrapper):
    def as_text(self):
        return self.node.text
    
class Api:
    def __init__(self, registry, filename):
        self.registry = registry
        self.filename = filename
        tree = ET.parse(filename)
        self.registry.apis.append(self)
        self.api = tree.getroot()

    def get_xml_name(self):
        return self.api.get('name')

    def get_header_filename(self):
        return 'gcc-%s.h' % self.get_xml_name()

    def get_doc(self):
        xml_doc = self.api.find('doc')
        if xml_doc is not None:
            return Doc(self, xml_doc)
        else:
            return None

    def iter_types(self):
        for node in self.api.iter(tag='type'):
            yield Type(self, node)

    def lookup_type(self, xmlname):
        for type_ in self.iter_types():
            if xmlname == type_.get_xml_name():
                return type_

    def iter_attrs(self):
        for node in self.api.findall('attribute'):
            yield Attribute(self, node)

    def iter_iters(self):
        for node in self.api.findall('iterator'):
            yield Iterator(self, node)

class Tests(unittest.TestCase):
    def test_loading_all(self):
        r = ApiRegistry()
        for filename in ('cfg.xml', 'gimple.xml', 'rtl.xml'):
            gimpleapi = r.load(filename)

    def test_types(self):
        r = ApiRegistry()
        gimpleapi = r.load('gimple.xml')
        gimple = r.lookup_type('gimple')
        self.assertEqual(gimple.get_xml_name(), 'gimple')
        self.assertEqual(gimple.get_c_name(), 'gcc_gimple')
        self.assertEqual(gimple.get_varname(), 'stmt')

    def test_subclassing(self):
        r = ApiRegistry()
        gimpleapi = r.load('gimple.xml')
        gimple = r.lookup_type('gimple')
        gimple_phi = r.lookup_type('gimple_phi')
        self.assertEqual(gimple_phi.get_xml_name(), 'gimple_phi')
        self.assertEqual(gimple.get_base(), None)
        self.assertEqual(gimple_phi.get_base(), gimple)
        self.assertIn(gimple_phi, gimple.get_subclasses()) # python 2.7

if __name__ == '__main__':
    unittest.main()
