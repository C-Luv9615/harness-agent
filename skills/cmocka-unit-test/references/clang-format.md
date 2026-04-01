# clang-format Workflow

This document describes how to apply clang-format.

## Step 1: Locate .clang-format Config

The `.clang-format` config file is located at the git repository root directory. Use it directly without searching parent directories.

## Step 2: Format Generated Files

If a `.clang-format` file is found, run `clang-format -i` on every generated `.c` and `.h` file:

```bash
clang-format -i [output_dir]/[module]/cm_[module]_entry.c
clang-format -i [output_dir]/[module]/src/test_[source].c
clang-format -i [output_dir]/[module]/include/cm_[source].h
```

## Step 3: Verify No Violations

Then verify no violations remain:

```bash
clang-format -n --Werror [output_dir]/[module]/cm_[module]_entry.c
clang-format -n --Werror [output_dir]/[module]/src/test_[source].c
clang-format -n --Werror [output_dir]/[module]/include/cm_[source].h
```

If any file still reports violations, re-run `clang-format -i` on that file and repeat the check until it passes.
