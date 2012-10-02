#include <stdlib.h>
#include <string.h>

void test(void)
{
  malloc(1024);
  /* BUG: result of malloc is never stored */
  /* FIXME: this isn't reported, though arguably this kind of error is
     rare */
}

void test2(void)
{
  test();
}
