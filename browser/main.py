#   Copyright 2013 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2013 Red Hat, Inc.
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

import re
import sys
sys.argv = []

from gi.repository import GtkClutter
GtkClutter.init(sys.argv)
from gi.repository import Clutter, GObject, Gtk, Gdk, Cogl

#print(dir(Clutter))
#print(dir(GtkClutter))

import gcc
from gccutils import get_src_for_loc, cfg_to_dot, invoke_dot

DEBUG_LAYOUT = 1

def random_color():
    from random import randint
    r = randint(64, 255)
    g = randint(64, 255)
    b = randint(64, 255)
    a = 255
    return Clutter.Color().new(r, g, b, a)

def make_text(txt):
    #print(txt)
    actor = Clutter.Text.new()
    actor.set_text(txt)
    actor.set_font_name('monospace')
    #actor.set_size(50, 50)
    #print(actor.get_position())
    #print('text size: %s' % (actor.get_size(),))
    if 0: # DEBUG_LAYOUT:
        actor.set_background_color(random_color())
    return actor

def make_grid(parent, width, height):
    color = Clutter.Color().new(0, 0, 0, 16)
    for x in range(0, width, 100):
        for y in range(0, height, 100):
            a = make_text('(%i, %i)' % (x, y))
            a.set_background_color(color)
            a.set_position(x, y)
            parent.add_actor(a)

#def get_layout(graph):

# Graphviz expresses width/height in inches, whereas we have pixels:
#INCHES_PER_PIXEL = 1/256.
#INCHES_PER_PIXEL = 1
INCHES_PER_PIXEL = 1/72.

def split_attrs(attrs):
    attrvals = {}
    for clause in attrs.split(', '):
        m = re.match('(\S+)=(.+)', clause)
        attrname, value = m.groups()
        attrvals[attrname] = value
    return attrvals

def iter_node_attrs(dot):
    """
    Yield a sequence of (nodename, attrdict) pairs
    """
    for line in dot.splitlines():
        # e.g.
        #     n1 [width="0.17361", height="0.069444", fixedsize=true, pos="206,3"];
        # print line
        m = re.match('\s*(n[0-9]+) \[(.*)\];', line)
        if m:
            #print m.groups()
            nodename, attrs = m.groups()
            attrvals = split_attrs(attrs)
            yield nodename, split_attrs(attrs)
        else:
            # print 'unmatched'
            pass

def iter_edge_attrs(dot):
    """
    Yield a sequence of (edgename, attrdict) pairs
    """
    for line in dot.splitlines():
        # e.g.
        #     n2 -> n3 [pos="e,241.6,387.23 396.72,521.99 380,511.51 361.13,498.86 345,486 308.97,457.28 271.58,419.24 248.55,394.69"];
        print line
        m = re.match('\s*(n[0-9]+) -> (n[0-9]+) \[(.*)\];', line)
        if m:
            print m.groups()
            srcnodename, dstnodename, attrs = m.groups()
            yield srcnodename, dstnodename, split_attrs(attrs)
        else:
            # print 'unmatched'
            pass

class GraphView(GtkClutter.Embed):
    def __init__(self, fun, graph):
        GtkClutter.Embed.__init__(self)

        self.fun = fun
        self.graph = graph

        stage = self.get_stage()

        if DEBUG_LAYOUT:
            make_grid(stage, 1024, 768)

            test = Clutter.Text.new()
            test.set_text('hello world')
            stage.add_actor(test)
            test.set_position(200, 5)

        """
        transition = Clutter.PropertyTransition.new('opacity')
        transition.set_duration(1000)
        transition.set_repeat_count(-1) # forever
        transition.set_auto_reverse(True)
        transition.set_loop(True)
        #transition.set_from(255)
        #transition.set_to(0)
        #print(dir(transition))
        # from/to don't do anything
        test.add_transition("animate-opacity", transition)
        transition.start()
        """

        self.stage = stage
        self.actor_for_node = {}
        self.actor_for_edge = {}
        self.edge_by_node_pair = {}

        self.nodes_by_id = {}

        self.selected_nodes = set()

        for node in graph.nodes:
            self.nodes_by_id[id(node)] = node
            bbactor = self._make_actor_for_node(fun, node)
            self.actor_for_node[node] = bbactor
            stage.add_actor(bbactor)

            for outedge in node.succs:
                self.edge_by_node_pair[(outedge.srcnode,
                                        outedge.dstnode)] = outedge
                edgeactor = EdgeActor(self, outedge)
                stage.add_actor(edgeactor)
                self.actor_for_edge[outedge] = edgeactor

        self._generate_layout()

        stage.set_scale(100, 5)
        # ^^ doesn't seem to do anything

    def _make_actor_for_node(self, fun, node):
        raise NotImplementedError

    def _make_dot(self):
        result = 'digraph %s {\n' % 'test'
        result += '  node [shape=box];\n'
        for node, actor in self.actor_for_node.iteritems():
            w, h = actor.get_size()
            # Express width and height in graphviz "inches", which we'll 
            result += ('  n%i [width=%f, height=%f, fixedsize=true];\n'
                       % (id(node), w * INCHES_PER_PIXEL, h * INCHES_PER_PIXEL))
            for outedge in node.succs:
                result += ('  n%i -> n%i;\n'
                           % (id(outedge.srcnode), id(outedge.dstnode)))
        #result += self._edges_to_dot(ctxt)
        result += '}\n'
        return result

    def _generate_layout(self):
        dot = self._make_dot()
        print(dot)
        from gccutils import invoke_dot
        #invoke_dot(dot)

        from subprocess import Popen, PIPE
        p = Popen(['dot', '-Tdot'],
                  stdin=PIPE, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate(dot.encode('ascii'))
        print(out)

        # Locate bounding box
        bb_w = None
        bb_h = None
        for line in out.splitlines():
            # e.g.
            #    graph [bb="0,0,1328,630"];
            m = re.match('\s+graph \[bb="([0-9]+),([0-9]+),([0-9]+),([0-9]+)"\];', line)
            if m:
                print m.groups()
                bb_w = int(m.group(3))
                bb_h = int(m.group(4))
        assert bb_w
        assert bb_h

        self.stage.set_size(bb_w, bb_h)

        for nodename, attrdict in iter_node_attrs(out):
            print(nodename, attrdict)
            assert nodename.startswith('n')
            node_id = int(nodename[1:])
            # http://www.graphviz.org/doc/info/attrs.html#a:pos
            # "pos" is the center of the node, in points
            pos = attrdict['pos'][1:-1] # strip off quotes
            x, y = pos.split(',')
            x, y = float(x), float(y)
            # These are in graphviz points, which are 1/72th of an inch
            POINTS_TO_INCH = 72
            POINTS_TO_PIXELS = POINTS_TO_INCH * INCHES_PER_PIXEL
            SCALE = POINTS_TO_PIXELS# * 2
            SCALE = 1
            x, y = x * SCALE, y * SCALE

            # Flip y axis:
            y = bb_h - y

            node = self.nodes_by_id[node_id]
            actor = self.actor_for_node[node]

            # Clutter uses top-left for position
            # Adjust from center to TL:
            w, h = actor.get_size()
            x = x - (w / 2.)
            y = y - (h / 2.)

            if not DEBUG_LAYOUT:
                # Directly set the position:
                actor.set_position(x, y)
            else:
                # Animate to it, with a bounce: see
                # https://clutter-and-mx-under-python3.readthedocs.org/en/latest/clutter_animation.html
                actor.set_position(x, 0)
                _actor_anim = actor.animatev(
                    Clutter.AnimationMode.EASE_OUT_BOUNCE,
                    1500,
                    ["x", "y"],
                    [x, y] )

        for srcnodename, destnodename, attrdict in iter_edge_attrs(out):
            print(srcnodename, destnodename, attrdict)

            assert srcnodename.startswith('n')
            src_node_id = int(srcnodename[1:])

            assert destnodename.startswith('n')
            dst_node_id = int(destnodename[1:])

            srcnode = self.nodes_by_id[src_node_id]
            dstnode = self.nodes_by_id[dst_node_id]

            edge = self.edge_by_node_pair[(srcnode, dstnode)]
            edgeactor = self.actor_for_edge[edge]

            if 'pos' in attrdict:
                posstr = attrdict['pos'][1:-1] # remove quotes
                result = []
                for coord in posstr.split(' '):
                    coordvals = coord.split(',')
                    if len(coordvals) == 3:
                        assert coordvals[0] == 'e'
                        x, y = coordvals[1:3]
                    else:
                        x, y = coordvals[0:2]
                    x = float(x)
                    y = bb_h - float(y)
                    result.append( (x, y) )
                #print(result)
                edgeactor.set_coords(result)

    def select_one_node(self, node):
        print('select_one_node(%r)' % node)
        # Deselect all:
        for oldnode in self.selected_nodes:
            actor = self.actor_for_node[oldnode]
            actor.is_selected = False
            actor.set_background_color(self.NORMAL)
        self.selected_nodes = set()

        # Select this node:
        self.selected_nodes.add(node)
        actor = self.actor_for_node[node]
        actor.is_selected = True
        actor.set_background_color(self.SELECTED)

    def toggle_node_selection(self, node):
        print('toggle_node_selection(%r)' % node)
        actor = self.actor_for_node[node]
        if actor.is_selected:
            self.selected_nodes.remove(node)
            actor.is_selected = False
            actor.set_background_color(self.NORMAL)
        else:
            self.selected_nodes.add(node)
            actor.is_selected = True
            actor.set_background_color(self.SELECTED)

    def add_node_to_selection(self, node):
        print('add_node_to_selection(%r)' % node)
        actor = self.actor_for_node[node]
        self.selected_nodes.add(node)
        actor.is_selected = True
        actor.set_background_color(self.SELECTED)

class NodeActor(Clutter.Actor):
    def __init__(self, gv, node):
        Clutter.Actor.__init__(self)
        self.gv = gv
        self.node = node
        self.is_selected = False

############################################################################
# Graph-viewing subclasses specific to CFG
############################################################################

class CFGView(GraphView):
    def _make_actor_for_node(self, fun, node):
        return BBActor(self, fun, node)

class BBActor(NodeActor):
    def __init__(self, gv, fun, bb):
        NodeActor.__init__(self, gv, bb)
        self.fun = fun

        #print(dir(Clutter))
        #self.add_actor(
        layout = Clutter.TableLayout()
        self.set_layout_manager(layout)

        if bb.index == 0:
            label = 'ENTRY'
        elif bb.index == 1:
            label = 'EXIT'
        else:
            label = 'bb: %i' % bb.index

        layout.pack(make_text(label),
                    column=0, row=0)

        if DEBUG_LAYOUT:
            self.set_background_color(random_color())

        # TODO: phi nodes
        if  bb.gimple:
            row = 1
            cursrcline = None
            for stmtidx, stmt in enumerate(bb.gimple):
                if stmt.loc is not None:
                    if cursrcline != stmt.loc.line:
                        cursrcline = stmt.loc.line
                        code = get_src_for_loc(stmt.loc).rstrip()
                        srctext = make_text('%4i %s' % (cursrcline, code))
                        layout.pack(srctext, column=0, row=row)

                text = make_text(str(stmt))
                layout.pack(text, column=1, row=row)
                row += 1
            """
            text = make_text('more stuff')
            layout.pack(text, column=1, row=row)
            row += 1
            text = make_text('yet more stuff')
            layout.pack(text, column=1, row=row)
            row += 1
            """

        action = Clutter.ClickAction.new()
        self.add_action(action)
        def foo(*args):
            print('clicked on %s, args: %s' % (self.node, args))
            event = Clutter.get_current_event()
            state = event.get_state()
            if state & Clutter.ModifierType.CONTROL_MASK:
                self.gv.toggle_node_selection(self.node)
                return
            if state & Clutter.ModifierType.SHIFT_MASK:
                self.gv.add_node_to_selection(self.node)
                return
            self.gv.select_one_node(self.node)
            #self.set_background_color(random_color())
        action.connect('clicked', foo)
        self.set_reactive(True)

        #rect = Clutter.Rectangle.new()
        #rect.size = (20, 20)
        #rect.position = (10, 30)
        #rect.color = Clutter.Color()
        #self.add_actor(rect)

        #self.set_size(50, 50)
        #print('self.get_size(): %s' % (self.get_size(), ))
        #print('self.allocation: %s' % (self.allocation, ))

    def get_top_middle(self):
        x, y = self.get_position()
        w, h = self.get_size()
        return (x + w/2., y)

    def get_bottom_middle(self):
        x, y = self.get_position()
        w, h = self.get_size()
        return (x + w/2., y + h)

class EdgeActor(Clutter.Actor):
    def __init__(self, gv, edge):
        Clutter.Actor.__init__(self)
        self.gv = gv
        self.edge = edge
        self._coords = None

    def do_paint(self):
        #print('do_paint: %s' % self.edge)
        # Get edge locations
        actor_for_src = self.gv.actor_for_node[self.edge.srcnode]
        actor_for_dest = self.gv.actor_for_node[self.edge.dstnode]

        #Cogl.Color.set()
        Cogl.path_new()
        if 0:
            print(self._coords)
            Cogl.path_move_to(*self._coords[0])
            for coord in self._coords[1:]:
                Cogl.path_line_to(*coord)
            Cogl.path_stroke()
        else:
            Cogl.path_move_to(*actor_for_src.get_bottom_middle())
            Cogl.path_line_to(*actor_for_dest.get_top_middle())
            Cogl.path_stroke()

    def set_coords(self, coords):
        self._coords = coords

############################################################################

class MainWindow(Gtk.Window):
    def __init__(self, fun):
        Gtk.Window.__init__(self)

        self.connect('destroy', lambda w: Gtk.main_quit())
        self.set_default_size(1024, 768)
        self.set_title(fun.decl.name)

        display = Gdk.Display.get_default()
        screen = display.get_default_screen()
        #css_provider = Gtk.CssProvider()
        #print(dir(css_provider))
        #props = css_provider.get_style(None)
        #print(dir(props))

        from gccutils.graph.cfg import CFG
        graph = CFG(fun)

        gv = CFGView(fun, graph)
        self.add(gv)

        def RGBA_to_clutter(rgba):
            return Clutter.Color().new(rgba.red * 255,
                                       rgba.green * 255,
                                       rgba.blue * 255,
                                       rgba.alpha * 255)

        sctxt = self.get_style_context()# Gtk.StyleContext()
        print(sctxt)
        #print(dir(sctxt))
        print(sctxt.get_color(Gtk.StateFlags.NORMAL))
        gv.NORMAL = RGBA_to_clutter(sctxt.get_color(Gtk.StateFlags.NORMAL))

        print(sctxt.get_color(Gtk.StateFlags.BACKDROP))
        gv.BACKDROP = sctxt.get_color(Gtk.StateFlags.BACKDROP)
        print(dir(gv.BACKDROP))
        gv.stage.set_background_color(RGBA_to_clutter(gv.BACKDROP))

        print(sctxt.get_color(Gtk.StateFlags.PRELIGHT))
        gv.PRELIGHT = sctxt.get_color(Gtk.StateFlags.PRELIGHT)

        print(sctxt.get_color(Gtk.StateFlags.NORMAL | Gtk.StateFlags.SELECTED))
        gv.SELECTED = RGBA_to_clutter(sctxt.get_color(Gtk.StateFlags.SELECTED))

        print(sctxt.get_color(Gtk.StateFlags.FOCUSED))
        gv.FOCUSED = sctxt.get_color(Gtk.StateFlags.FOCUSED)

        print(sctxt.get_color(Gtk.StateFlags.INSENSITIVE))
        gv.INSENSITIVE = sctxt.get_color(Gtk.StateFlags.INSENSITIVE)


        self.show_all()


# We'll implement this as a custom pass, to be called directly after the
# builtin "cfg" pass, which generates the CFG:

class ShowGimple(gcc.GimplePass):
    def execute(self, fun):
        # (the CFG should be set up by this point, and the GIMPLE is not yet
        # in SSA form)
        if fun and fun.cfg:
            mw = MainWindow(fun)
            print(dir(Gtk.StyleProvider))
            Gtk.main()

#print(dir(Gtk.StateFlags))

ps = ShowGimple(name='show-gimple')
ps.register_after('cfg')
