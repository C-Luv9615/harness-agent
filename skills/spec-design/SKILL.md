---
name: spec-design
description: >
  Spec-driven development: transform requirements into structured design docs with task breakdown.
  Use when user says "写设计文档", "spec design", "需求设计", "设计方案", "feature design",
  "design doc", "技术方案", "方案设计", or provides a feature/requirement description and wants
  a structured plan before coding. Also triggers when user pastes a Feishu doc URL containing
  requirements. Outputs spec.md, plan.md, tasks.md to specs/{feature}/ — compatible with mispec.
---

# Spec-Driven Design

Transform requirements into structured design documents with actionable task breakdown.
Output three independent files compatible with mispec directory structure.

## Input

One of:
- Natural language requirement description
- Feishu document URL (fetch and extract requirements)
- Existing local file path containing requirements

Optional:
- JIRA ID for linking
- Target codebase path for context-aware design

## Output Structure

```
.specify/{feature}/
├── spec.md       ← 需求规范
├── plan.md       ← 技术方案
└── tasks.md      ← 任务列表（checkbox 格式）
```

`{feature}` 推断规则：用户指定 > JIRA ID > git 当前分支名 > 从需求描述提取关键词（kebab-case）。

此结构与 mispec 兼容——session-handoff、mispec.change-propagation 等 skill 可直接操作这些文件。

## Workflow

### Step 1: Gather Requirements

1. If user provides a Feishu URL → fetch doc content
2. If user provides a file path → read file
3. If user describes in chat → use chat context
4. If target codebase provided → read relevant source files for context

Ask clarifying questions if requirements are ambiguous. Minimum needed:
- What problem does this solve?
- What is the expected behavior?
- Any constraints (performance, compatibility, memory)?

### Step 2: Generate spec.md

```markdown
---
status: draft
jira: {JIRA_ID or empty}
created: {YYYY-MM-DD}
---

# {Feature Title}

## Background
(Problem statement, motivation, current behavior, why this change is needed)

## Requirements

### Functional Requirements
- **FR-001**: {description}
- **FR-002**: {description}

### Non-Functional Requirements (if applicable)
- **NFR-001**: {performance/memory/compatibility constraint}

### Edge Cases
- When {condition}, the system should {behavior}

## Success Criteria
- **SC-001**: {measurable outcome}
```

### Step 3: Generate plan.md

```markdown
---
spec: spec.md
created: {YYYY-MM-DD}
---

# Implementation Plan: {Feature Title}

## Summary
(High-level solution strategy from spec requirements)

## Technical Background
**Language**: {e.g., C/NuttX}
**Test Framework**: {e.g., cmocka}
**Build System**: {e.g., CMake+Ninja}

## Design

### Approach
(Key design decisions and rationale)

### Interface Changes
(New/modified APIs, function signatures, data structures)

### Internal Design
(Data flow, state management, algorithm choices)

## Impact Analysis

### Affected Modules
(List of files/modules that need changes)

### Compatibility
(Backward compatibility, migration needs)

### Risks
(Known risks, edge cases, failure modes, mitigation)

## Project Structure
(Source code layout for this feature)
```

### Step 4: Generate tasks.md

```markdown
---
spec: spec.md
plan: plan.md
created: {YYYY-MM-DD}
---

# Tasks: {Feature Title}

## Phase 1: Setup
- [ ] T001 {description} — files: `{paths}` — test: {verification}

## Phase 2: Core Implementation
- [ ] T002 {description} — files: `{paths}` — test: {verification}
- [ ] T003 [P] {description} — files: `{paths}` — test: {verification}

## Phase 3: Integration & Polish
- [ ] T004 {description} — files: `{paths}` — test: {verification}

## Dependencies
- T003 depends on T002
- [P] = can run in parallel
```

Task 格式规则：
- 每个 task 必须指定 files 和 test
- `[P]` 标记可并行的 task
- 按依赖顺序排列
- 每个 task 应可独立测试

### Step 5: Review with User

Display the three files and ask:
- 方案是否合理？需要调整哪些部分？
- 任务拆解粒度是否合适？
- 是否有遗漏的影响范围？

Iterate until user approves.

### Step 6: Write Files

1. Create `.specify/{feature}/` directory
2. Write spec.md, plan.md, tasks.md to `.specify/{feature}/`
3. If files exist, backup as `{filename}.bak` and add `updated: {YYYY-MM-DD}` to header

### Step 7: Prompt Next Steps

```
✅ Spec generated:
  .specify/{feature}/spec.md
  .specify/{feature}/plan.md
  .specify/{feature}/tasks.md
📋 {N} tasks ready for implementation.

Next steps:
  1. Start with Task 1 — write tests first (cmocka-unit-test)
  2. Implement → verify → commit (git-commit)
  3. Repeat for each task
```

## Key Rules

- Specs must have `status: draft` until user explicitly approves
- **Three independent files** — not one monolithic doc
- Output path `.specify/{feature}/` — compatible with mispec
- Task breakdown must be ordered by dependency
- Each task must specify files and test verification
- Keep each file concise: spec 200-400 words, plan 200-500 words
- Never fabricate implementation details — mark uncertain areas with `[TBD]`
