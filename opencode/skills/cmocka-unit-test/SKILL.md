---
name: cmocka-unit-test
description: >
  Generate cmocka unit tests for Vela/NuttX embedded C code. Use when the user asks to
  "generate unit tests", "create cmocka tests", "write test cases for C functions",
  "generate tests for NuttX", "create Vela tests", or any request involving cmocka test
  generation for C source files. Handles test code generation, mock functions, build files
  (Makefile, CMakeLists.txt, Make.defs, Kconfig), and directory structure following nxstyle
  conventions.
---

# cmocka Unit Test Generator for Vela/NuttX

Generate cmocka unit tests for C functions in Vela/NuttX embedded systems.

## Naming Definitions

Throughout this document, the following placeholders are used. **Strictly distinguish** between them:

| Placeholder | Scope | Derivation Rule | Example |
|-------------|-------|-----------------|---------|
| `[module]` | Directory-level module name, represents the entire test module | Derived from source file path: take the parent directory name of the source files, joining the last two path components with `_`. E.g., source files under `nuttx/sched/timer/` → `sched_timer` | `sched_timer`, `mm_heap`, `task` |
| `[source]` | Source file name (without `.c` extension) | The basename of the source `.c` file being tested | `timer_create`, `timer_delete`, `mm_malloc` |
| `[func]` | Individual function name being tested | The actual function name from the source code (lowercase) | `timer_create`, `timer_settime`, `mm_malloc` |
| `[MODULE_UPPER]` | Uppercase form of `[module]` | `[module]` converted to uppercase | `SCHED_TIMER`, `MM_HEAP`, `TASK` |
| `[module]_tests` | Entry 文件中 CMUnitTest 数组名 | `[module]` + `_tests` 后缀，用于 cmocka 日志区分模块 | `sched_timer_tests`, `mm_heap_tests` |

Key rules:
- **One module can contain tests for multiple source files**. Each source file gets its own test file (`src/test_[source].c`) and header file (`include/cm_[source].h`). A single source file may contain multiple functions; all functions from the same source file share one test file and one header.
- **Build files and entry file use `[module]`**: `cm_[module]_entry.c`, `Makefile`, `CMakeLists.txt`, `Make.defs`, `Kconfig`.
- **Test source files and header files use `[source]`**: `src/test_[source].c`, `include/cm_[source].h`.
- **Test function names use `[func]`** (the actual function name from source code): `test_[func]_[scenario]` (e.g., `test_timer_create_normal`).
- **Setup/teardown use `[source]`**: `test_[source]_setup`, `test_[source]_teardown` — shared by all functions in the same source file.
- In many cases `[source]` and `[func]` are the same (e.g., `timer_create.c` contains `timer_create()`). They differ when a source file contains multiple functions or when the function name doesn't match the file name.

## References

- [cmocka official docs](https://cmocka.org/)
- [cmocka API reference](https://api.cmocka.org/)
- For detailed requirements and examples, read [references/requirements.md](references/requirements.md)
- For code templates, read [references/templates.md](references/templates.md)

## Workflow

### Step 1: Collect Parameters and Confirm

When the user provides a source file path, first read the source file to:
1. Auto-detect the module name and derive the default output path (`tests/velatest/[module]/`).
2. List all functions found in the source file, clearly separating non-static and static functions.

**MUST display the function list in the following format:**

```
检测到以下函数：

非静态函数（默认测试目标）：
  - function_name_1(param_type1 param1, param_type2 param2) -> return_type
  - function_name_2(void) -> void

静态函数（需确认是否测试）：
  - static_func_1(param_type1 param1) -> return_type
  - static_func_2(void) -> int

（如果源文件包含 main 函数或宏替换的 main，需标注"已排除 main 函数"）
```

Then **MUST present the following 4 questions to the user and wait for explicit confirmation before proceeding**:

1. **是否需要测试静态函数？**（默认：否。）
2. **是否有额外需要 mock 的函数？**（默认：否。用户可以指定需要 mock 的函数名，并说明 mock 行为，例如："mock fopen，成功时返回有效指针，失败时返回 NULL"、"mock malloc，返回 NULL 模拟内存不足"）
3. **输出路径 `tests/velatest/[module]/` 是否可以？**（默认：是。根据源文件路径自动推导，显示具体路径）
4. **是否需要调整测试范围？**（默认：测试上方列出的所有目标函数——即所有非静态函数，以及问题 1 中确认要测试的静态函数。用户可以指定只测试某些函数，或排除某些函数不测试。例如："只测试 func_a 和 func_b"、"不测试 func_c"）

**BLOCKING**: 必须等待用户明确回复确认后，才能继续执行 Step 2。禁止跳过确认直接生成代码。

### Step 2: Analyze Source Code

Read the source file and extract for each target function:
- Function signature (name, return type, parameters)
- Whether it is `static`
- Internal function calls (to determine mock needs)
- Branching complexity (if/else/switch for test scenario planning)

**过滤规则**：如果源文件中包含 `main` 函数（包括直接定义的 `int main(...)` 或通过宏替换的 main，如 NuttX 中常见的 `#define main xxx_main`），则 `main` 函数必须从测试目标中排除。如果源文件中除 `main` 外没有其他可测试的非 static 函数，应提示用户该文件不适合生成单元测试并终止流程。

### Step 3: Determine Mock Functions

**如果用户在 Step 1 中对"是否有额外需要 mock 的函数？"回答了"否"，则跳过本步骤，不生成任何 mock 函数。**

仅当用户明确回答"是"并指定了需要 mock 的函数时，才执行mock逻辑。

### Step 4: Generate Test Scenarios

For each function, generate these test types:

| Scenario | Naming | Description |
|----------|--------|-------------|
| Normal path | `test_[func]_normal` | Valid inputs, verify correct return |
| NULL params | `test_[func]_null_param` | NULL for each pointer param |
| Invalid input | `test_[func]_invalid_input` | Out-of-range values, bad enums |
| Boundary | `test_[func]_boundary` | Max/min values, empty strings |
| Error handling | `test_[func]_error_handling` | Mock dependencies return errors |

Minimum 3 scenarios per function. All function names must be **lowercase**.

### Step 5: Determine Generation Mode

Check whether the output directory already exists and contains build files (Makefile, CMakeLists.txt, Make.defs, Kconfig) and entry file.

**Full mode** (directory does not exist or is empty):
- Generate all files: build files, entry file, header, test source

**Incremental mode** (directory already exists with build files and entry file):
- Only create new test source file: `src/test_[source].c`
- Create new header file: `include/cm_[source].h`
- Modify existing files:
  - `cm_[module]_entry.c` — add `#include "cm_[source].h"` and append new test registrations to the `tests[]` array
  - `Makefile` — append new `CSRCS += src/test_[source].c` line (if not already present)
- Do NOT regenerate: Makefile (from scratch), CMakeLists.txt, Make.defs, Kconfig, entry file

### Step 5a: Generate Files (Full Mode)

Generate the following directory structure:

```
tests/velatest/[module]/
├── CMakeLists.txt
├── include/
│   └── cm_[source].h
├── Kconfig
├── Make.defs
├── Makefile
├── src/
│   └── test_[source].c
└── cm_[module]_entry.c
```

### Step 5b: Generate Files (Incremental Mode)

Only create and modify:

| Action | File | Description |
|--------|------|-------------|
| Create | `src/test_[source].c` | New test source with setup/teardown and test cases |
| Create | `include/cm_[source].h` | New header declaring setup/teardown and test function prototypes |
| Modify | `cm_[module]_entry.c` | Add `#include "cm_[source].h"` and append new `cmocka_unit_test_setup_teardown` entries to `[module]_tests[]` |
| Modify | `Makefile` | Append `CSRCS += src/test_[source].c` if not present |

#### Code Conventions (MUST follow)

**Header order** (strict):
```c
#include <nuttx/config.h>    // MUST be first
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <setjmp.h>
#include <cmocka.h>
// other headers...
```

**Test function signature** — named after the actual function being tested:
```c
void test_[func]_[scenario](FAR void **state)
```

**Setup/teardown** — named after the source file, MUST NOT be `static` (entry file references them), and MUST be declared in the header file:
```c
int test_[source]_setup(FAR void **state)
{
    return 0;
}

int test_[source]_teardown(FAR void **state)
{
    return 0;
}
```

**Mock functions** — use `__wrap_` prefix with `--wrap` linker flag:
```c
FILE *__wrap_fopen(const char *filename, const char *mode)
{
    check_expected_ptr(filename);
    check_expected_ptr(mode);
    return (FILE *)mock();
}
```

**Static function testing** — include source with relative path:
```c
#include "../../src/module.c"  // relative path REQUIRED
```

**Test array naming** — entry 文件中的 `CMUnitTest` 数组必须使用 `[module]_tests` 命名（例如 `sched_timer_tests`），禁止使用通用名 `tests`。`cmocka_run_group_tests` 的第一个参数同步使用该数组名。cmocka 框架会将数组名输出到日志中（如 `[==========] sched_timer_tests: Running 11 test(s).`），使用模块名可以在日志中区分不同模块的测试结果。

**License header** — Apache 2.0 on ALL generated files.

**Comment style** — use `#` for build files, `/* */` for C files.

**Section comment labels** — setup/teardown 函数是被 entry 文件引用的 public 函数，注释标签必须使用 `Public Functions - Setup/Teardown`，禁止使用 `Private Functions - Setup/Teardown`。

**Type safety** — NuttX 中部分 typedef 类型（如 `timer_t`、`pid_t`）底层是整数类型而非指针，初始化和比较时必须使用 `0` 而非 `NULL`，断言使用 `assert_int_equal`/`assert_int_not_equal` 而非 `assert_non_null`。只有真正的指针类型才能使用 `NULL`。

**Include completeness** — 使用 `memset`/`memcpy` 等函数时必须包含 `<string.h>`，不要依赖隐式声明。

**`*state` lifecycle** — cmocka 的 `*state` 指针在 setup → test → teardown 之间共享。使用规则：
- 禁止将栈上局部变量的地址存入 `*state`，函数返回后指针悬空。
- 如需在 setup 中分配资源供 test/teardown 使用，必须使用 `test_malloc`/`test_calloc`（cmocka 提供的内存分配），并在 teardown 中用 `test_free` 释放。
- 如果测试函数内部自行创建和销毁资源（如 `timer_create` + `timer_delete`），应在同一函数内完成清理，不要依赖 teardown，也不要写入 `*state`。
- 简单场景下 setup/teardown 保持空实现（`return 0;`）即可。

#### cmocka API Quick Reference
Full API: https://api.cmocka.org/

### Step 6: Output Summary

After generation, display:
- List of generated files
- Number of test functions per file
- Mock functions used
- Build instructions

### Step 7: Update defconfig and Build

**BLOCKING — 禁止在 Step 7 输出总结后停止。必须立即读取并执行 [references/build.md](references/build.md) 中的全部步骤，直到构建完成为止。**
