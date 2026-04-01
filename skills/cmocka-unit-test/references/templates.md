# cmocka Test Code Templates

## License Headers

### For C Source Files

Use this license header for all `.c` and `.h` files:

```c
/****************************************************************************
 * [filepath]
 *
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.  The
 * ASF licenses this file to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance with the
 * License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 ****************************************************************************/
```

**Placeholder**: `[LICENSE_HEADER]` in C file templates

### For Build Files (Makefile, CMakeLists.txt, Make.defs, Kconfig)

Use this license header for all build configuration files:

```makefile
############################################################################
# [filepath]
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.  The
# ASF licenses this file to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the
# License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations
# under the License.
#
############################################################################
```

**Placeholder**: `[LICENSE_HEADER]` in build file templates

## Header File Template (cm_[source].h)

**File**: `include/cm_[source].h`  
**Purpose**: Header file declaring test function prototypes for a single source file  
**Used by**: Test source files and entry file  
**Note**: Each tested source file gets its own header file. One module may have multiple header files.

```c
[LICENSE_HEADER]

#ifndef __TESTING_CMOCKA_[MODULE]_CM_[SOURCE]_H
#define __TESTING_CMOCKA_[MODULE]_CM_[SOURCE]_H

/****************************************************************************
 * Included Files
 ****************************************************************************/

#include <nuttx/config.h>

/****************************************************************************
 * Public Function Prototypes
 ****************************************************************************/

[TEST_FUNCTION_DECLARATIONS]

#endif /* __TESTING_CMOCKA_[MODULE]_CM_[SOURCE]_H */
```

**Placeholder**: `[TEST_FUNCTION_DECLARATIONS]`

Replace with forward declarations of setup/teardown and all test functions for this source file. Setup/teardown use `[source]`, test functions use `[func]` (the actual function name). Setup/teardown MUST be declared here (they are non-static, referenced by entry file).

```c
int test_[source]_setup(FAR void **state);
int test_[source]_teardown(FAR void **state);
void test_[func]_[scenario](FAR void **state);
```

**Example** (for source file `timer_create.c` in module `sched_timer`, containing function `timer_create`):
```c
int test_timer_create_setup(FAR void **state);
int test_timer_create_teardown(FAR void **state);
void test_timer_create_normal(FAR void **state);
void test_timer_create_null_param(FAR void **state);
void test_timer_create_invalid_priority(FAR void **state);
```

## Test Source Template (test_[source].c)

**File**: `src/test_[source].c`  
**Purpose**: Contains all test case implementations for functions in a single source file  
**Contains**: Mock functions, setup/teardown, and test functions

```c
[LICENSE_HEADER]

/****************************************************************************
 * Included Files
 ****************************************************************************/

#include <nuttx/config.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <setjmp.h>
#include <cmocka.h>

[ADDITIONAL_INCLUDES]

#include "cm_[source].h"

/****************************************************************************
 * Pre-processor Definitions
 ****************************************************************************/

/****************************************************************************
 * Private Types
 ****************************************************************************/

/****************************************************************************
 * Private Data
 ****************************************************************************/

/****************************************************************************
 * Private Functions - Mock
 ****************************************************************************/

[MOCK_FUNCTIONS]

/****************************************************************************
 * Public Functions - Setup/Teardown
 ****************************************************************************/

int test_[source]_setup(FAR void **state)
{
    /* Initialize test fixtures */

    return 0;
}

int test_[source]_teardown(FAR void **state)
{
    /* Clean up test fixtures */

    return 0;
}

/****************************************************************************
 * Public Functions - Test Cases
 ****************************************************************************/

[TEST_FUNCTIONS]
```

**Placeholders**:

- `[ADDITIONAL_INCLUDES]` — Extra headers needed (e.g., `#include <string.h>`, `#include <errno.h>`, `#include "../../src/module.c"` for static functions). Note: `<string.h>` is REQUIRED when using `memset`/`memcpy`.

- `[MOCK_FUNCTIONS]` — Mock function implementations using `__wrap_` prefix. Example:
  ```c
  FILE *__wrap_fopen(const char *filename, const char *mode)
  {
      check_expected_ptr(filename);
      check_expected_ptr(mode);
      return (FILE *)mock();
  }
  ```

- `[TEST_FUNCTIONS]` — All test function implementations. Named after the actual function being tested:
  ```c
  void test_[func]_[scenario](FAR void **state)
  {
      /* Test implementation */
      assert_int_equal(result, expected);
  }
  ```

## Entry File Template (cm_[module]_entry.c)

**File**: `cm_[module]_entry.c`  
**Purpose**: Main entry point that registers and runs all test cases for the entire module  
**Contains**: Test registration and cmocka runner  
**Note**: Uses `[module]` (not `[source]`) in the filename. Includes all per-source-file header files.

```c
[LICENSE_HEADER]

/****************************************************************************
 * Included Files
 ****************************************************************************/

#include <nuttx/config.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <setjmp.h>
#include <cmocka.h>

#include "cm_[source1].h"
#include "cm_[source2].h"

/****************************************************************************
 * Public Functions
 ****************************************************************************/

int main(int argc, FAR char *argv[])
{
    const struct CMUnitTest tests[] =
    {
        [TEST_REGISTRATIONS]
    };

    return cmocka_run_group_tests(tests, NULL, NULL);
}
```

**Placeholder**: `[TEST_REGISTRATIONS]`

Replace with cmocka test registrations. Each test function is registered using:

- `cmocka_unit_test_setup_teardown(test_function_name, setup_function, teardown_function)` — test with setup/teardown


## Makefile Template

**File**: `Makefile`  
**Purpose**: Traditional make-based build configuration  
**Used with**: NuttX traditional build system

```makefile
[LICENSE_HEADER]

include $(APPDIR)/Make.defs

PROGNAME  = cmocka_[module]
PRIORITY  = $(CONFIG_CM_[MODULE_UPPER]_TEST_PRIORITY)
STACKSIZE = $(CONFIG_CM_[MODULE_UPPER]_TEST_STACKSIZE)
MODULE    = $(CONFIG_CM_[MODULE_UPPER]_TEST)

MAINSRC = $(CURDIR)/cm_[module]_entry.c

CSRCS  += src/test_[source].c

CFLAGS += -I$(CURDIR)/include

include $(APPDIR)/Application.mk
```

## CMakeLists.txt Template

**File**: `CMakeLists.txt`  
**Purpose**: CMake-based build configuration  
**Used with**: NuttX CMake build system

```cmake
[LICENSE_HEADER]

if(CONFIG_CM_[MODULE_UPPER]_TEST)
  set([MODULE_UPPER]_INCDIR ${CMAKE_CURRENT_LIST_DIR}/include
                            ${CMAKE_CURRENT_LIST_DIR}/src)
  file(GLOB [MODULE_UPPER]_CSRC ${CMAKE_CURRENT_LIST_DIR}/src/*.c)
  nuttx_add_application(
    NAME
    cmocka_[module]_test
    PRIORITY
    ${CONFIG_CM_[MODULE_UPPER]_TEST_PRIORITY}
    STACKSIZE
    ${CONFIG_CM_[MODULE_UPPER]_TEST_STACKSIZE}
    MODULE
    ${CONFIG_CM_[MODULE_UPPER]_TEST}
    SRCS
    ${CMAKE_CURRENT_LIST_DIR}/cm_[module]_entry.c
    ${[MODULE_UPPER]_CSRC}
    INCLUDE_DIRECTORIES
    ${[MODULE_UPPER]_INCDIR})

endif()
```

**Placeholders**:
- `[MODULE_UPPER]` — Module name in uppercase (e.g., `SCHED_TIMER`)
- `[module]` — Module name in lowercase (e.g., `sched_timer`)
- `[source]` — Source file name in lowercase (e.g., `timer_create`). One module may have multiple `[source]` entries.

## Make.defs Template

**File**: `Make.defs`  
**Purpose**: Build system integration configuration  
**Location**: Same directory as Makefile/CMakeLists.txt

```Make.defs
[LICENSE_HEADER]

ifneq ($(CONFIG_CM_[MODULE_UPPER]_TEST),)
CONFIGURED_APPS += $(APPDIR)/tests/velatest/[module]
endif
```

## Kconfig Template

**File**: `Kconfig`  
**Purpose**: Configuration menu definition  
**Location**: Same directory as Makefile/CMakeLists.txt

```kconfig
#
# For a description of the syntax of this configuration file,
# see the file kconfig-language.txt in the NuttX tools repository.
#

config CM_[MODULE_UPPER]_TEST
	tristate "vela auto tests [module]"
	default n
	depends on TESTING_CMOCKA
	---help---
		Enable auto tests for the vela [module] module

if CM_[MODULE_UPPER]_TEST

config CM_[MODULE_UPPER]_TEST_PRIORITY
	int "Task priority"
	default 100

config CM_[MODULE_UPPER]_TEST_STACKSIZE
	int "Stack size"
	default DEFAULT_TASK_STACKSIZE

endif
```

**Placeholders**:
- `[MODULE_UPPER]` — Module name in uppercase (e.g., `SCHED_TIMER`)
- `[module]` — Module name in lowercase (e.g., `sched_timer`)


## Complete Example: sched_timer (multi-function module)

This example shows a module `sched_timer` that tests two source files: `timer_create.c` and `timer_delete.c` from `nuttx/sched/timer/`.

**Key distinction**: `[module]` = `sched_timer`, `[source]` = `timer_create` or `timer_delete`.

### Directory Structure

```
tests/velatest/sched_timer/
├── CMakeLists.txt                    ← uses [module]: sched_timer
├── include/
│   ├── cm_timer_create.h             ← uses [source]: timer_create
│   └── cm_timer_delete.h             ← uses [source]: timer_delete
├── Kconfig                           ← uses [module]: SCHED_TIMER
├── Make.defs                         ← uses [module]: sched_timer
├── Makefile                          ← uses [module]: sched_timer
├── src/
│   ├── test_timer_create.c           ← uses [source]: timer_create
│   └── test_timer_delete.c           ← uses [source]: timer_delete
└── cm_sched_timer_entry.c            ← uses [module]: sched_timer
```

### cm_timer_create.h (per-source-file header)

```c
/****************************************************************************
 * tests/velatest/sched_timer/include/cm_timer_create.h
 * ...license header...
 ****************************************************************************/

#ifndef __TESTING_CMOCKA_SCHED_TIMER_CM_TIMER_CREATE_H
#define __TESTING_CMOCKA_SCHED_TIMER_CM_TIMER_CREATE_H

#include <nuttx/config.h>

int test_timer_create_setup(FAR void **state);
int test_timer_create_teardown(FAR void **state);

void test_timer_create_normal(FAR void **state);
void test_timer_create_null_param(FAR void **state);
void test_timer_create_invalid_clockid(FAR void **state);

#endif /* __TESTING_CMOCKA_SCHED_TIMER_CM_TIMER_CREATE_H */
```

### test_timer_create.c (per-source-file test)

```c
/****************************************************************************
 * tests/velatest/sched_timer/src/test_timer_create.c
 * ...license header...
 ****************************************************************************/

#include <nuttx/config.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <setjmp.h>
#include <cmocka.h>

#include <string.h>
#include <time.h>
#include <signal.h>
#include <errno.h>

#include "cm_timer_create.h"

/****************************************************************************
 * Public Functions - Setup/Teardown
 ****************************************************************************/

int test_timer_create_setup(FAR void **state)
{
    return 0;
}

int test_timer_create_teardown(FAR void **state)
{
    return 0;
}

/****************************************************************************
 * Public Functions - Test Cases
 ****************************************************************************/

void test_timer_create_normal(FAR void **state)
{
    /* Test normal timer creation with valid parameters */

    timer_t timerid = 0;
    struct sigevent evp;
    int ret;

    memset(&evp, 0, sizeof(struct sigevent));
    evp.sigev_notify = SIGEV_SIGNAL;
    evp.sigev_signo  = SIGALRM;

    ret = timer_create(CLOCK_REALTIME, &evp, &timerid);
    assert_int_equal(ret, OK);
    assert_int_not_equal(timerid, 0);

    timer_delete(timerid);
}

void test_timer_create_null_param(FAR void **state)
{
    /* Test with NULL timerid pointer */

    struct sigevent evp;
    int ret;

    memset(&evp, 0, sizeof(struct sigevent));
    evp.sigev_notify = SIGEV_SIGNAL;
    evp.sigev_signo  = SIGALRM;

    ret = timer_create(CLOCK_REALTIME, &evp, NULL);
    assert_int_equal(ret, ERROR);
    assert_int_equal(get_errno(), EINVAL);
}

void test_timer_create_invalid_clockid(FAR void **state)
{
    /* Test with invalid clock ID */

    timer_t timerid = 0;
    struct sigevent evp;
    int ret;

    memset(&evp, 0, sizeof(struct sigevent));
    evp.sigev_notify = SIGEV_SIGNAL;
    evp.sigev_signo  = SIGALRM;

    ret = timer_create((clockid_t)-1, &evp, &timerid);
    assert_int_equal(ret, ERROR);
    assert_int_equal(get_errno(), EINVAL);
}
```

### cm_sched_timer_entry.c (module-level entry, includes ALL source-file headers)

```c
/****************************************************************************
 * tests/velatest/sched_timer/cm_sched_timer_entry.c
 * ...license header...
 ****************************************************************************/

#include <nuttx/config.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <setjmp.h>
#include <cmocka.h>

#include "cm_timer_create.h"
#include "cm_timer_delete.h"

int main(int argc, FAR char *argv[])
{
    const struct CMUnitTest tests[] =
    {
        cmocka_unit_test_setup_teardown(test_timer_create_normal, test_timer_create_setup, test_timer_create_teardown),
        cmocka_unit_test_setup_teardown(test_timer_create_null_param, test_timer_create_setup, test_timer_create_teardown),
        cmocka_unit_test_setup_teardown(test_timer_create_invalid_clockid, test_timer_create_setup, test_timer_create_teardown),
        cmocka_unit_test_setup_teardown(test_timer_delete_normal, test_timer_delete_setup, test_timer_delete_teardown),
        cmocka_unit_test_setup_teardown(test_timer_delete_invalid_timerid, test_timer_delete_setup, test_timer_delete_teardown),
    };

    return cmocka_run_group_tests(tests, NULL, NULL);
}
```

### Makefile (module-level, references all source-file tests)

```makefile
# ...license header...

include $(APPDIR)/Make.defs

PROGNAME  = cmocka_sched_timer
PRIORITY  = $(CONFIG_CM_SCHED_TIMER_TEST_PRIORITY)
STACKSIZE = $(CONFIG_CM_SCHED_TIMER_TEST_STACKSIZE)
MODULE    = $(CONFIG_CM_SCHED_TIMER_TEST)

MAINSRC = $(CURDIR)/cm_sched_timer_entry.c

CSRCS  += src/test_timer_create.c
CSRCS  += src/test_timer_delete.c

CFLAGS += -I$(CURDIR)/include

include $(APPDIR)/Application.mk
```
