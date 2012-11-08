#include <stdlib.h>

void test(void)
{
    void *ptr = malloc(512);
    free(ptr);
    /* BUG: this is a double-free: */
    free(ptr);
}
