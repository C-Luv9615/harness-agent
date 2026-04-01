---
name: tdd-workflow
description: >
  TDD workflow for C/NuttX embedded development. Enforces test-driven development with
  cmocka: write tests first, implement minimal code, refactor. Use when writing new features,
  fixing bugs, or refactoring C code. Works with cmocka-unit-test skill for test generation.
  Triggers: "tdd", "test driven", "写测试", "测试驱动", "红绿重构".
---

# TDD Workflow for C/NuttX

Test-driven development workflow for embedded C projects using cmocka.

## Core Loop

```
Red → Green → Refactor → Commit
```

1. **Red** — Write a failing test first
2. **Green** — Write minimal code to make it pass
3. **Refactor** — Clean up while keeping tests green
4. **Commit** — One logical change per commit

## When to Activate

- Writing new features or modules
- Fixing bugs (write a test that reproduces the bug first)
- Refactoring existing code (ensure tests exist before changing)
- Adding new API functions

## Workflow Steps

### Step 1: Define Interface

Write the header file first. This is the contract.

```c
/* include/module.h — the contract */
int module_init(struct module_config *cfg);
int module_process(struct module_ctx *ctx, const void *input, size_t len);
void module_deinit(struct module_ctx *ctx);
```

### Step 2: Write Tests (Red)

Use `cmocka-unit-test` skill to generate test scaffolding, then add test cases:

```
→ Trigger: "generate cmocka tests for <source_file>"
```

Write tests covering:
- Normal path — valid inputs, expected outputs
- NULL/invalid params — defensive checks
- Boundary conditions — zero, max, overflow
- Error paths — dependency failures (via mock)

### Step 3: Verify Tests Fail

Build and run. All new tests should fail (red).

```bash
# Build tests
make -C tests/velatest/<module>

# Run
./<module>_test
```

If tests pass before implementation → tests are not testing anything useful. Fix them.

### Step 4: Implement (Green)

Write the minimum code to make tests pass. No more.

Rules:
- Only implement what a failing test demands
- Don't add "nice to have" code without a test
- If you need a helper function, write a test for it first (or keep it trivially simple)

### Step 5: Refactor

With all tests green, improve code quality:
- Extract common patterns into helper functions
- Improve naming
- Remove duplication
- Simplify control flow

Run tests after each refactoring step. If any test breaks → revert and try again.

### Step 6: Commit

Use `git-commit` skill. One logical change per commit.

```
→ Trigger: "commit" or "提交"
```

### Step 7: Next Cycle

Pick the next test case or task from the spec. Repeat from Step 2.

## TDD Strategy by Code Type

| Code Type | Strategy | Mock Needs |
|-----------|----------|------------|
| Pure functions (parse, validate, compute) | Direct input→output testing | None |
| Functions with syscall deps (ioctl, open) | `__wrap_` mock syscalls | Mock HAL/OS layer |
| State machines / event-driven | Mock event source, test each transition | Mock HAL + event injection |

### Pure Functions — Easiest

No mocks needed. Test input→output directly.

```c
/* Test: parameter validation */
static void test_parse_config_null(void **state)
{
  assert_int_equal(module_parse_config(NULL), -EINVAL);
}

/* Test: boundary */
static void test_parse_config_max_value(void **state)
{
  struct config cfg = { .timeout = INT32_MAX };
  assert_int_equal(module_parse_config(&cfg), 0);
}
```

### With Dependencies — Mock the Boundary

Use `__wrap_` prefix + `--wrap` linker flag to mock syscalls/HAL.

```c
int __wrap_ioctl(int fd, int cmd, ...)
{
  check_expected(cmd);
  return mock_type(int);
}

static void test_read_sensor_ioctl_fail(void **state)
{
  expect_value(__wrap_ioctl, cmd, SENSOR_READ);
  will_return(__wrap_ioctl, -EIO);
  assert_int_equal(read_sensor(&ctx, &val), -EIO);
}
```

### State Machines — Test Each Transition

Each state transition is one test case. Mock HAL layer, inject events, verify state change.

```c
static void test_event_X_in_state_A_goes_to_B(void **state)
{
  struct ctx ctx = { .state = STATE_A };
  event_t ev = { .type = EVENT_X };
  /* mock HAL calls... */
  assert_int_equal(state_machine_run(&ctx, &ev), 0);
  assert_int_equal(ctx.state, STATE_B);
}
```

## Integration with Other Skills

| Phase | Skill | Trigger |
|-------|-------|---------|
| Design + task breakdown | `spec-design` | "写设计文档", "spec design" |
| Generate test scaffolding | `cmocka-unit-test` | "generate cmocka tests" |
| Build | `vela-build` | "build", "编译" |
| Commit | `git-commit` | "commit", "提交" |

## What Must Be Tested

| Category | Required |
|----------|----------|
| All public API functions | ✅ |
| NULL/invalid parameter handling | ✅ |
| Every error code branch | ✅ |
| Boundary values (0, max, overflow) | ✅ |
| State machine transitions (if any) | ✅ |
| Internal helpers | Only if complex |

## Anti-Patterns

- ❌ Writing implementation before tests
- ❌ Writing all tests at once then all implementation at once
- ❌ Tests that pass without implementation (testing nothing)
- ❌ Skipping refactor step
- ❌ Testing implementation details instead of behavior
- ❌ Large commits mixing multiple features

## Project-Level Customization

Projects should provide a steering file (e.g., `steering/tdd.md`) with:
- Project-specific module design principles and code examples
- Concrete mock patterns for the project's HAL/driver layer
- AI code review checklist tailored to the project
- File organization conventions

The steering file supplements this workflow with project-specific constraints.
