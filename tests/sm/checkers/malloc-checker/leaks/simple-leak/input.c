#include <stdlib.h>
#include <string.h>

void test(void)
{
  void *p;

  p = malloc(1024);

  /* BUG: p is leaked on function exit */
}

/* FIXME: we shouldn't need a caller of test() for the checker to work;
   currently we do */
void test2(void)
{
  test();
}
