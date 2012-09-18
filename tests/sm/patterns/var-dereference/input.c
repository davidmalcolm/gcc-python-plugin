int test1(int *p)
{
  return *p;
}

struct foo {
  int i;
};

int test2(struct foo *f)
{
  return f->i;
}
