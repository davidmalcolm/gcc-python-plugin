/*
  Trivial example code to be compiled, for testing purposes
 */

#include <stdio.h>

int
helper_function(void)
{
    printf("I am a helper function\n");
    return 42;
}

int
main(int argc, char **argv)
{
    int i;

    printf("argc: %i\n", argc);

    for (i = 0; i < argc; i++) {
        printf("argv[%i]: %s\n", argv[i]);
    }

    helper_function();

    return 0;
}
