---
name: repoworktree
description: >
  Use the rwt (repoworktree) CLI to manage isolated workspaces for Google
  repo-managed multi-repo projects. Each workspace is a mix of git worktrees
  (writable, isolated) and symlinks (read-only, zero overhead). Use when the
  user asks to create/destroy/list rwt workspaces, promote or demote sub-repos
  between symlink and worktree, sync worktrees to latest source, pin repos to
  specific versions, or export patches from a workspace.
  Triggers: rwt, repoworktree, workspace create, promote repo, demote repo,
  rwt sync, rwt status.
---

# rwt — repoworktree

Install: `pip install repoworktree`

Manages isolated workspaces for `repo`-managed multi-repo projects. Each workspace overlays the source checkout with a mix of git worktrees (for repos you're actively editing) and symlinks (for everything else).

## Core Commands

```bash
# Create workspace — all repos symlinked by default
rwt create <path> [-n name] [-w repo1,repo2] [--all] [-b branch] [--checkout REF] [--pin repo=version]

# Destroy workspace (checks for dirty/unpushed changes unless --force)
rwt destroy <path|name> [-s source] [-f]

# List all workspaces for current source
rwt list [-s source] [--json]

# Show workspace status (dirty, local commits, pinned)
rwt status [path|name] [-s source] [--json]

# Promote a symlinked repo to a git worktree (in-place, inside existing workspace)
rwt promote <repo-path> [-W workspace] [-b branch] [--pin version]

# Demote a worktree back to symlink
rwt demote <repo-path> [-W workspace] [-f]

# Sync worktrees to latest source HEAD (optionally rebase local commits)
rwt sync [-W workspace] [--rebase]

# Pin/unpin a worktree to a specific commit
rwt pin <repo-path> [version] [-W workspace]
rwt unpin <repo-path> [-W workspace]

# Export local commits as patches or bundles
rwt export [-W workspace] [-o output-dir] [--format patch|bundle]
```

## Common Workflows

### Start working on a feature
```bash
# Create workspace with specific repos as worktrees
rwt create ~/ws/feature-x -w nuttx,frameworks/system/core -b feature/my-fix

# Or start all-symlink and promote as needed
rwt create ~/ws/feature-x
cd ~/ws/feature-x
rwt promote nuttx -b feature/my-fix
```

### Check workspace state
```bash
rwt status            # auto-detects workspace from CWD
rwt status feature-x  # by name from anywhere in source
```

### Sync after upstream changes
```bash
# After repo sync on source, update workspace worktrees
rwt sync             # fast-forward only
rwt sync --rebase    # rebase local commits on top
```

### Clean up
```bash
rwt destroy feature-x      # safe: blocks if dirty/unpushed
rwt destroy feature-x -f   # force: ignores uncommitted changes
```

## Key Behaviors

- `rwt create` builds atomically into a `.tmp` dir then renames — safe to interrupt
- `rwt destroy` checks for uncommitted changes AND unpushed commits before proceeding
- `rwt promote` on a deep path (e.g. `frameworks/system/core`) automatically splits parent symlinks into real dirs with symlinked siblings
- `rwt demote` collapses empty parent dirs back into symlinks when possible
- Source root is auto-detected by walking up to find `.repo/`; override with `-s/--source`
- Workspace is auto-detected from CWD by looking for `.workspace.json`
- Sub-repos that are children of a worktree (e.g. `nuttx/fs/fatfs` when `nuttx` is a worktree) are symlinked on top and hidden from git via `skip-worktree` + `.gitignore`
- `-w` accepts comma-separated repo paths matching entries in `.repo/project.list`
- `--checkout REF` sets the initial branch/tag for all worktrees at creation time without pinning them (so `rwt sync` still works); explicit `--pin` entries take precedence per-repo
