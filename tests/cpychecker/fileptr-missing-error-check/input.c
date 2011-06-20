#include <stdio.h>

void
missing_error_check(const char *filename)
{
    FILE *f = fopen(filename, "r");

    /* This code doesn't check to see if fopen succeeded */
    fclose(f);
}
