---
name: vela-harness
description: >
  Automated test harness for Vela/NuttX: build → run → test → parse results → feedback loop.
  Orchestrates vela-build, vela-run, cmocka-unit-test, and executor skills into a closed-loop
  verification pipeline. Use when user says "harness", "验证闭环", "跑测试", "run tests",
  "test loop", "自动验证", "build and test", "编译跑测试", or after code generation needs
  automated verification. Also triggers when spec-design tasks need execution with verification.
---

# Vela Harness — Automated Build-Test-Verify Loop for NuttX

Orchestrate existing skills into a closed-loop: code change → build → run → test → parse → fix/pass.

## Core Concept

```
┌─────────────┐     ┌───────────┐     ┌──────────┐     ┌─────────────┐
│ Code Change  │────▶│   Build   │────▶│   Run    │────▶│ Parse Result│
└─────────────┘     └───────────┘     └──────────┘     └──────┬──────┘
       ▲                                                       │
       │              ┌──────────┐                             │
       └──────────────│ AI Fix   │◀────────────────────────────┘
         if FAIL      └──────────┘         FAIL → feedback
                                           PASS → done
```

Human stays in the loop at two points:
1. **Before fix** — AI proposes fix, user approves
2. **After max retries** — AI reports what it tried, user decides next step

## Input

Required:
- **target**: Build target (e.g., `qemu-armv8a:nsh_smp`, `sim:cmocka`)
- **test_cmd**: Test command to run on NSH (e.g., `cmocka_test_sched_timer`)

Optional:
- **source_files**: Files being modified (for targeted rebuild)
- **max_retries**: Auto-fix retry limit (default: 3)
- **run_target**: Override run target if different from build (e.g., `simulator`)

## Skill Dependencies

| Phase | Skill Used | Purpose |
|-------|-----------|---------|
| Build | `vela-build` | Compile NuttX/Vela target |
| Run | `vela-run` + `executor` | Launch QEMU/simulator, get interactive shell |
| Test | `executor` | Send test command, capture output |
| Fix | (AI direct) | Analyze failure, propose code fix |
| Commit | `git-commit` | Commit passing changes |

## Workflow

### Step 1: Validate Environment

```bash
# Check build system exists
ls nuttx/Makefile || ls nuttx/CMakeLists.txt

# Check test binary is configured (for cmocka tests)
# User should have already run cmocka-unit-test skill to generate test code
```

If test code doesn't exist yet, prompt:
```
⚠️ 未找到测试代码。是否先用 cmocka-unit-test skill 生成测试？
```

### Step 2: Build

Use `vela-build` skill to compile.

**Build failure handling:**
1. Capture compiler error output
2. Parse error: file, line, message
3. Display to user with proposed fix
4. If user approves → apply fix → rebuild (count as 1 retry)
5. If build fails after max_retries → stop, report

**Key build commands by target type:**

```bash
# NuttX CMake (preferred)
cmake -Bbuild -GNinja -DBOARD_CONFIG={target} nuttx
ninja -C build

# Simulator (for cmocka tests)
cmake -Bbuild -GNinja -DBOARD_CONFIG=sim:cmocka nuttx
ninja -C build
```

### Step 3: Run

Launch the target using `vela-run` + `executor` skill.

**For simulator (most common for unit tests):**
```python
executor_start(command="./build/nuttx")
# Wait for NSH prompt
executor_send(text="", wait_time=1.0)  # wait for "nsh>"
```

**For QEMU:**
```python
executor_start(command="qemu-system-aarch64", args=[...])
executor_send(text="", wait_time=2.0)  # wait for boot + "nsh>"
```

**Boot detection:** Look for `nsh>` prompt in output. Timeout after 30s → report boot failure.

### Step 4: Execute Test

Send test command and capture output:

```python
executor_send(
    text="{test_cmd}",
    wait_time=5.0,    # cmocka tests usually finish in seconds
    full_buffer=true,
    tail_lines=200
)
```

### Step 5: Parse Results

Parse cmocka output format:

```
[==========] module_tests: Running N test(s).
[ RUN      ] test_func_normal
[       OK ] test_func_normal
[ RUN      ] test_func_null_param
[  FAILED  ] test_func_null_param
[==========] module_tests: N test(s) run.
[  PASSED  ] X test(s).
[  FAILED  ] Y test(s).
```

Extract:
- **total**: number of tests run
- **passed**: count of `[  PASSED  ]` or `[       OK ]`
- **failed**: count of `[  FAILED  ]`
- **failed_tests**: list of failed test names
- **failure_details**: lines between `[ RUN ]` and `[  FAILED  ]` for each failure

**Other failure modes to detect:**

| Pattern | Meaning |
|---------|---------|
| `ASSERT` / `assert` in output | NuttX assertion failure |
| `Segmentation fault` / `SIGSEGV` | Crash |
| `Timeout` (no output for 30s) | Hang/deadlock |
| `command not found` | Test binary not built/configured |
| No `nsh>` after boot | Boot failure |

### Step 6: Report & Decide

**All tests pass:**
```
✅ Harness PASS — {total} tests, all passed.
  Target: {target}
  Test: {test_cmd}
  Time: {elapsed}s

是否提交？(使用 git-commit skill)
```

**Some tests fail:**
```
❌ Harness FAIL — {passed}/{total} passed, {failed} failed.
  Failed tests:
    - test_func_null_param: expected 0, got -1
    - test_func_boundary: segfault at line 42

Retry {current}/{max_retries}. AI 分析失败原因并提出修复方案：

[AI analysis and proposed fix here]

是否应用修复？[y/n]
```

**If user approves fix → apply → go to Step 2 (rebuild)**
**If user rejects → stop, let user fix manually**
**If max_retries reached:**
```
⚠️ 已达到最大重试次数 ({max_retries})。
  尝试过的修复：
    1. [fix description]
    2. [fix description]
    3. [fix description]

建议手动检查以下文件：
  - {source_file}:{line} — {issue}
```

### Step 7: Cleanup

```python
executor_stop(process_id="{pid}")
```

Always stop the executor process, even on failure.

## Batch Mode

For running multiple test modules in sequence:

```
harness batch target=sim:cmocka tests="cmocka_test_sched_timer cmocka_test_mm_heap cmocka_test_task"
```

Workflow:
1. Build once
2. Start simulator once
3. Run each test_cmd sequentially
4. Collect all results
5. Report summary:

```
📊 Batch Results — 3 modules, 47 tests total

  ✅ cmocka_test_sched_timer: 15/15 passed
  ❌ cmocka_test_mm_heap: 12/14 passed (2 failed)
  ✅ cmocka_test_task: 18/18 passed

Overall: 45/47 passed (95.7%)
Failed: cmocka_test_mm_heap → test_mm_malloc_boundary, test_mm_free_double
```

## Integration with SDD Workflow

When used after `spec-design` skill generates a task list:

```
spec-design → tasks[] → for each task:
  1. cmocka-unit-test → generate test code
  2. vela-harness → build + run tests (expect RED)
  3. Implement code
  4. vela-harness → build + run tests (expect GREEN)
  5. git-commit → commit
```

This is the full SDD + TDD + Harness loop.

## Quick Reference

| Command | Description |
|---------|-------------|
| `harness target=sim:cmocka test=cmocka_test_xxx` | Single test module |
| `harness batch target=sim:cmocka tests="a b c"` | Multiple test modules |
| `harness target=qemu-armv8a:nsh_smp test=xxx` | Test on QEMU ARM64 |
| `harness --build-only target=sim:cmocka` | Only build, skip run |
| `harness --no-fix target=sim:cmocka test=xxx` | Run without auto-fix loop |

## Key Rules

- **Never auto-apply fixes without user approval** — always show proposed fix first
- **Always cleanup executor processes** — even on error/timeout
- **Parse output strictly** — don't guess test results, parse cmocka format
- **Preserve test code** — harness never modifies test files, only implementation files
- **One retry = one build-run cycle** — don't count parse/analysis as retry
- **Timeout is a failure** — treat hangs same as test failures
