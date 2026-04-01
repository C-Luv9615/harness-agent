# cmocka Unit Test Generator — Detailed Requirements

## Project Context

- **Project**: Vela (NuttX-based) embedded system
- **Framework**: cmocka
- **Language**: C
- **Reference**: https://cmocka.org/ , https://api.cmocka.org/

## Interaction Model

Use natural language dialog. Typical flow:

```
User: Generate tests for /path/to/source.c functions parse_config and validate_input

Agent: I will generate tests for:
  - Source: /path/to/source.c
  - Functions: parse_config, validate_input
  - Output: tests/velatest/[module]/
  Any additional mock functions needed?

User: Mock malloc and fopen

Agent: Confirmed config:
  - Source: /path/to/source.c
  - Functions: parse_config, validate_input
  - Mocks: malloc, fopen (+ auto-detected)
  - Output: tests/velatest/[module]/
  Proceed?

User: Yes

Agent: [generates files...]
```

## Mock Strategy

### Auto-detect (smart analysis)

Scan function body for calls to:
- Memory: `malloc`, `calloc`, `realloc`, `free`
- File I/O: `fopen`, `fclose`, `fread`, `fwrite`, `open`, `close`, `read`, `write`
- System: `mmap`, `munmap`, `ioctl`, `fcntl`
- String (with side effects): `strcpy`, `strncpy`, `sprintf`, `snprintf`
- Thread: `pthread_create`, `pthread_mutex_lock`, `sem_wait`

### User-specified

- User can add extra mock functions via dialog
- User can exclude auto-detected mocks

### Implementation

Use cmocka `__wrap_` mechanism with `--wrap` linker flag:

```c
// Mock declaration
TYPE __wrap_FUNCTION(PARAMS)
{
    check_expected(param1);
    return (TYPE)mock();
}

// In test function
will_return(__wrap_FUNCTION, expected_return);
expect_value(__wrap_FUNCTION, param1, expected_value);
```

## Test Scenarios

For each function, generate at minimum:

1. **Normal path** — valid inputs, correct return
2. **NULL parameters** — NULL for each pointer param
3. **Invalid input** — out-of-range, bad enums
4. **Boundary conditions** — max/min values, empty strings
5. **Error handling** — mock dependencies return errors

## Naming Conventions

- Test functions: `test_[func]_[scenario]` — `[func]` is the actual function name from source code, ALL LOWERCASE
- Setup/teardown: `test_[source]_setup`, `test_[source]_teardown` — `[source]` is the source file basename
- Header files: `cm_[source].h` (one per tested source file)
- Test source: `test_[source].c`
- Entry file: `cm_[module]_entry.c` (one per module, includes all source-file headers)
- Module directory: `tests/velatest/[module]/`
- `[module]` = directory-level grouping (e.g., `sched_timer`), `[source]` = source file basename (e.g., `timer_create`), `[func]` = actual function name (e.g., `timer_create`)
- Follow nxstyle coding standard

## Build Files

See [templates.md](templates.md) for complete build file templates:
- [Makefile Template](templates.md#makefile-template)
- [CMakeLists.txt Template](templates.md#cmakelists-template)
- [Make.defs Template](templates.md#makedefs-template)
- [Kconfig Template](templates.md#kconfig-template)

### Key Points

- Use `CM_[MODULE_UPPER]_TEST` for configuration macro names (e.g., `CM_SCHED_TIMER_TEST`)
- Include Apache 2.0 license header on all files
- Follow nxstyle coding conventions
- Makefile and CMakeLists.txt are mutually exclusive (use one or the other)
- Make.defs integrates the test module into the build system
- Kconfig enables configuration through menuconfig with priority and stack size options

## Output Path

- Default: `tests/velatest/[module]/` relative to source file
- User can specify custom absolute or relative path
- Create directories if they don't exist

## Quality Requirements

- Generated code MUST compile
- Generated tests MUST be runnable (even if assertions fail)
- All files include Apache 2.0 license header
- Code follows nxstyle conventions
