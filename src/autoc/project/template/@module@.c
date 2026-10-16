#include <stdio.h>
#include "@module@_auto.h"


int main(int argc, char** argv) {
  char* s = StringNew("@project@");
  printf("Hello, %s!\n", s);
  StringFree(s);
  return 0;
}
