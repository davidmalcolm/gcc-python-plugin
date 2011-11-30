/*
   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011 Red Hat, Inc.

   This is free software: you can redistribute it and/or modify it
   under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see
   <http://www.gnu.org/licenses/>.
*/

/* Examples of various aspects of C++ syntax */
namespace Example {
    struct Coord {
        int x;
        int y;
    };

    class Widget {
    protected:
        Widget() {
        }
    public:
        virtual ~Widget() {
        }

        /* Example of a pure virtual method */
        virtual int get_width() = 0;

        /* Reference: */
        void set_location(const struct Coord& coord);

    private:
        struct Coord m_location;
    };

    class Dialog : public Widget {
    public:
        Dialog(): Widget() {
        }

        ~Dialog() {}

        int get_width() { return 400; }
    };
};

/* Example of a method definition, outside of the body of the class */
void Example::Widget::set_location(const struct Coord& coord)
{
    this->m_location = coord;
}

/* Examples of overloaded functions: */
void foo()
{
}

void foo(const char *str)
{
}

void foo(const Example::Coord& coord)
{
    /* Example of a call to a non-virtual method: */
    Example::Widget *dlg = new Example::Dialog();
    dlg->set_location(coord);
    delete dlg;

}




/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
