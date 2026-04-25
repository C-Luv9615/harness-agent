````skill
---
name: experience-summarize
description: "Distill bug-solving processes into standardized experience documents. Collects information from chat context, local files, git history, and JIRA, then generates a structured experience doc. Triggered when user says 'summarize experience', 'generate experience', 'distill knowledge', '总结经验', '生成经验', '沉淀知识'."
---

# experience-summarize

Distill bug-solving processes into standardized, reusable experience documents for the team knowledge base.

## Input

Optional parameter: **JIRA ID** (e.g. `PROJECT-12345`). If not provided, AI infers the topic from chat context. If unable to infer, ask the user.

## Information Sources

Collect from ALL available sources in parallel, merge and deduplicate:

| Priority | Source | When to use |
|----------|--------|-------------|
| 1 | Chat context | Always — review the current conversation for analysis process, conclusions, code snippets |
| 2 | Local files | If JIRA ID provided and `.vela_bug/{JIRA_ID}/` exists — read `jira_info.md`, `analysis.md`, `*.patch`, `*.diff` (skip `crash/` subdirectory) |
| 3 | Git history | `git log --all --oneline --grep="{JIRA_ID}"` or `--grep="{topic keyword}"` |
| 4 | JIRA | If JIRA ID provided and JIRA tools available — fetch issue summary, description, comments |

**No single source is required.** If chat context alone has enough information, that's sufficient. If all sources are thin, note gaps honestly — never fabricate content.

## Output

### File path

- With JIRA ID: `skills/experiences/{JIRA_ID}.md`
- Without JIRA ID: `skills/experiences/{YYYY-MM-DD}-{topic-slug}.md`

### Problem type classification

The `type` field in YAML header classifies the problem by fault type. Use hierarchical categories:

- `crash/use-after-free`
- `crash/null-pointer`
- `crash/stack-overflow`
- `crash/assert-failure`
- `deadlock`
- `memory-leak`
- `logic-error`
- `performance`
- `config-error`
- `other`

AI selects the most specific matching type. If uncertain, ask the user.

### Template

```markdown
---
type: {fault-type}
jira: {JIRA_ID or empty}
reviewed: false
created: {YYYY-MM-DD}
---

# Problem Description
(Bug symptoms, trigger conditions, impact scope)

# Root Cause Analysis
(Key log/stack clues, core source code analysis, why it happened)

# Fix Approach
(Which files/functions were modified, fix rationale, regression verification method)

# Key Code Examples
(Before/after code comparison snippets — keep minimal)

# Reusable Debugging Insights
(Investigation approach for similar issues, key signals for quick identification, common fix patterns, coding principles to prevent recurrence)
```

## Workflow

### Step 1: Collect information

1. **Review chat context** — scan the current conversation for:
   - Problem description and symptoms
   - Analysis reasoning and conclusions
   - Code snippets, stack traces, log excerpts
   - Fix approach discussed or implemented

2. **Check local files** (if JIRA ID provided):
   - If `.vela_bug/{JIRA_ID}/` exists, read available `.md`, `.patch`, `.diff` files
   - Skip `crash/` subdirectory

3. **Search git history**:
   ```bash
   git log --all --oneline --grep="{JIRA_ID or keyword}"
   ```
   If commits found, extract key diffs with `git show {hash}`.

4. **Query JIRA** (if JIRA ID provided and tools available):
   - Fetch issue info for additional context

### Step 2: Classify and generate

Based on collected information, AI:

1. Determines the `type` classification — ask user if uncertain
2. Fills each template section, following these rules:
   - **Problem Description** — concise summary of what happened and when
   - **Root Cause Analysis** — the core "why", with supporting evidence (stack traces, code references)
   - **Fix Approach** — what was changed and why this approach was chosen
   - **Key Code Examples** — minimal before/after snippets, only the most critical changes
   - **Reusable Debugging Insights** — this is the most valuable section: generalized investigation patterns, not bug-specific details

3. Each section stays concise. Total document: 300-600 words. Leave sections empty with a note if information is insufficient.

### Step 3: Write file

1. Create `skills/experiences/` directory if it doesn't exist
2. Write the file
3. If file already exists:
   - Backup as `{filename}.bak`
   - Add `updated: {YYYY-MM-DD}` to YAML header
4. Display the generated content for user review

### Step 4: Prompt

```
✅ Experience doc generated: skills/experiences/{filename}.md
⚠️ Marked as reviewed: false — needs code review before merging into team knowledge base.
```

## Key Rules

- Generated docs **must** have `reviewed: false`
- Code snippets stay minimal — only show critical changes
- **Reusable Debugging Insights** focuses on generalizable patterns, not bug-specific details
- If information is insufficient for a section, leave it empty with a note — never fabricate
- Do NOT read coredump or binary files from `crash/` directories
````
