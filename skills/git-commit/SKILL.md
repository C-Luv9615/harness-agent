---
name: git-commit
description: "Commit changes with NuttX checkpatch.sh validation, automatic sign-off, component-based message format, and JIRA linking. Use when user says: commit, 提交, git commit, commit diff, commit当前, commit changes, 提交代码, 提交修改, /commit, /git-commit, or any request to create a git commit."
---

# git-commit

Commit changes with automatic code format checking and optimized commit message generation.

## Parameters

- **JIRA number** (optional): e.g., `123` or `PROJECT-123`
- **Reference message** (optional): Draft message to optimize based on diff

## Workflow

### Step 1: Gather context (run in parallel)

- `git status` — if no changes staged or modified, inform user and stop
- `git diff HEAD` — get all changes (staged + unstaged)
- `git log --oneline -10` — learn existing commit message style
- Check if `tools/checkpatch.sh` exists (NuttX detection)

### Step 2: Stage files

Stage modified/new files relevant to the change. Prefer specific file names over `git add -A`. Never stage `.env`, credentials, or secrets.

### Step 3: Run Format Check (NuttX only)

```bash
git diff [HEAD or --cached] | tools/checkpatch.sh -
```

Choose `--cached` (staged only) or `HEAD` (all changes) based on context. If errors/warnings: fix the issues, re-stage, and re-run checkpatch until clean, then proceed.

### Step 4: Generate Commit Message

Analyze the staged diff. Identify affected component from file paths.

**NuttX format:**

```
<component>: <brief summary under 72 chars>

{JIRA_PROJECT}-{NUMBER}    ← only if JIRA provided (default project: YOUR_PROJECT)

<detailed description>
```

**Standard format:**

```
<brief summary>

<detailed description>
```

Guidelines: present tense, wrap at 72 chars.

### Step 5: Create Commit

Always use HEREDOC for message and `-s` flag for sign-off.

```bash
git commit -s -m "$(cat <<'EOF'
<message>
EOF
)"
```

### Step 6: Verify

Run `git status` after commit to confirm success.

## Error Handling

| Error | Action |
|-------|--------|
| No changes | Inform user and exit |
| Format check failures | Fix issues, re-stage, re-run until clean |
| Pre-commit hook failure | Fix issue, create NEW commit (never --amend) |
