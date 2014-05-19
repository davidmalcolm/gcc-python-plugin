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
import math

HEADING_HEIGHT = 20
TREE_X_INDENT = 24
PASS_HEIGHT = 12
PASS_LEADING = 4
PHASE_SPACING = 50

propdata = [
    ('PROP_gimple_any', (1, 0, 0)),
    ('PROP_gimple_lcf', (0, 1, 0)),
    ('PROP_gimple_leh', (0, 0, 1)),
    ('PROP_cfg', (0, 1, 1)),
    ('PROP_referenced_vars', (1, 1, 0)),
    ('PROP_ssa', (0.5, 0.5, 1)),
    ('PROP_no_crit_edges', (0, 0, 0)),
    ('PROP_rtl', (0.5, 0.5, 0.5)),
    ('PROP_gimple_lomp', (0.75, 1, 0)),
    ('PROP_cfglayout', (0, 1, 0.75)),
    ('PROP_gimple_lcx', (0.25, 0.25, 0.25)),
]

# PROP_referenced_vars went away in GCC 4.8 (in r190067)
if not hasattr(gcc, 'PROP_referenced_vars'):
    propdata = [(flag, color) for (flag, color) in propdata
                if flag != 'PROP_referenced_vars']

def show_text_x_centered(ctx, text, x, y):
    ctx.set_source_rgb(0, 0, 0)
    te = ctx.text_extents(text)
    ctx.move_to(x - te[2]/2, y)
    ctx.show_text(text)

def show_text_y_centered(ctx, text, x, y):
    ctx.set_source_rgb(0, 0, 0)
    te = ctx.text_extents(text)
    ctx.move_to(x, y + te[3]/2)
    ctx.show_text(text)

class Property:
    def __init__(self, flagname, color, x):
        assert flagname.startswith('PROP_')
        self.name = flagname[5:]
        self.color = color
        self.flag = getattr(gcc, flagname)
        self.provided_by = None
        self.destroyed_by = None
        self.x = x

    def render(self, ctx):
        # Draw a line showing the lifetime of the property:
        if self.provided_by:
            start_y = self.provided_by.y
        else:
            start_y = 0

        if self.destroyed_by:
            end_y = self.destroyed_by.y
        else:
            end_y = 4000

        ctx.set_source_rgb(*self.color)
        ctx.move_to(self.x, start_y)
        ctx.line_to(self.x, end_y)
        ctx.stroke()

        # Draw termini:
        if self.provided_by:
            # ctx.arc(self.x, self.provided_by.y, 10, 0, 2 * math.pi)
            ctx.set_source_rgb(*self.color)
            ctx.move_to(self.x - 5, start_y)
            ctx.line_to(self.x + 5, start_y)
            ctx.stroke()
            show_text_x_centered(ctx, self.name, self.x, start_y - 5)
        else:
            show_text_x_centered(ctx, self.name, self.x, PASS_HEIGHT)

        if self.destroyed_by:
            # ctx.arc(self.x, self.destroyed_by.y, 10, 0, 2 * math.pi)
            ctx.set_source_rgb(*self.color)
            ctx.move_to(self.x - 5, end_y)
            ctx.line_to(self.x + 5, end_y)
            ctx.stroke()

properties = [Property(propname, col, 250 + (i*20))
              for i, (propname, col) in enumerate(propdata)]

class PassInfo:
    def __init__(self, d, ps, parent):
        self.d = d
        self.ps = ps

        for prop in properties:
            if self.ps.properties_provided & prop.flag:
                prop.provided_by = self

            if self.ps.properties_destroyed & prop.flag:
                prop.destroyed_by = self

    def render(self, ctx):
        show_text_y_centered(ctx, self.ps.name, self.x, self.y)

        for i, prop in enumerate(properties):
            if self.ps.properties_required & prop.flag:
                ctx.set_source_rgb(*prop.color)
                ctx.move_to(prop.x, self.y)
                ctx.line_to(prop.x - 5, self.y)
                ctx.stroke()



class Phase:
    def __init__(self, rootname, base_y):
        self.passinfo = {} # gcc.Pass ->PassInfo
        self.rootname = rootname
        self.base_y = base_y
        self.height = base_y + HEADING_HEIGHT + PASS_LEADING

    def add_pass(self, ps, parent):
        # print ps.name
        pi = PassInfo(self, ps, parent)
        if parent:
            ppi = self.passinfo[parent]
            pi.x = ppi.x + TREE_X_INDENT
        else:
            pi.x = 0
        pi.y = self.height
        if self.passinfo == {}:
            self.height += PASS_LEADING + PASS_HEIGHT
        else:
            self.height += PASS_HEIGHT
        self.passinfo[ps] = pi

        if ps.sub:
            self.add_pass(ps.sub, ps)
        if ps.next:
            self.add_pass(ps.next, parent)

    def render(self, ctx):
        ctx.move_to(0, self.base_y)
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_font_size(HEADING_HEIGHT)
        ctx.show_text(self.rootname)

        ctx.set_font_size(PASS_HEIGHT)
        for k in self.passinfo:
            pi = self.passinfo[k]
            pi.render(ctx)

phases = {}
base_y = HEADING_HEIGHT
for i, (rootname, reflabel, ps) in enumerate(
    zip(('The lowering passes',
         'The "small IPA" passes',
         'The "regular IPA" passes',
         'Passes generating Link-Time Optimization data',
         'The "all other passes" catch-all'),
        ('all_lowering_passes',
         'all_small_ipa_passes',
         'all_regular_ipa_passes',
         'all_lto_gen_passes',
         'all_passes'),
        gcc.Pass.get_roots())):
    # print rootname, reflabel, ps
    phases[i] = Phase(rootname, base_y)
    phases[i].add_pass(ps, None)
    base_y = phases[i].height + PHASE_SPACING

import cairo
surf = cairo.SVGSurface('docs/passes.svg', 550, base_y)
ctx = cairo.Context(surf)

# Fill with white:
ctx.set_source_rgb(1, 1, 1)
ctx.paint()

for prop in properties:
    prop.render(ctx)

for i in range(5):
    phases[i].render(ctx)

surf.finish()
