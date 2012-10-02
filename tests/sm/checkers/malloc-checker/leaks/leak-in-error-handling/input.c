#include <stdlib.h>
#include <string.h>

void test(void)
{
  void *p, *q;

  p = malloc(1024);
  if (!p) {
    return;
  }

  q = malloc(1024);
  if (!q) {
    /* BUG: leak of p */
    /* FIXME: the bug is reported, but we could do with a better error
       message covering *how* the leak happened */
    return;
  }

  free(p);
  free(q);
}

/* FIXME: we shouldn't need a caller of test() for the checker to work;
   currently we do */
void test2(void)
{
  test();
}

