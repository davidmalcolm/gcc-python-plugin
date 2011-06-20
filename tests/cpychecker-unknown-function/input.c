extern int bar(int);

int foo(int i)
{
    if (bar(i)) {
        return i;
    } else {
        return -i;
    }
}
