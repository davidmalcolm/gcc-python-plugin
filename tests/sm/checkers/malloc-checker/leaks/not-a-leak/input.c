#include <stdlib.h>
#include <string.h>

struct foo
{
  void *q;
};

struct foo f;

void test(void)
{
  void *p;

  p = malloc(1024);

  /* Store p somewhere, thus it is not a leak when p goes out of scope */
  f.q = p;
}

/* FIXME: we shouldn't need a caller of test() for the checker to work;
   currently we do */
void test2(void)
{
  test();
}

