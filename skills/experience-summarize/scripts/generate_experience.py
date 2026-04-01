#!/usr/bin/env python3
"""Generate experience summary from bug analysis artifacts.

Usage:
    python3 generate_experience.py <jira_id> [project_root]

Example:
    python3 generate_experience.py PROJECT-12345
    python3 generate_experience.py PROJECT-12345 /path/to/project
"""

import datetime
import glob
import os
import shutil
import subprocess
import sys


def read_file_safe(path: str, max_bytes: int = 50000) -> str:
    """Read file content, return empty string on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(max_bytes)
    except Exception:
        return ""


def collect_local_artifacts(bug_dir: str) -> dict:
    """Collect analysis artifacts from .vela_bug/{jira_id}/ directory.

    Returns dict with keys: jira_info, notes, logs, patches
    """
    artifacts = {"jira_info": "", "notes": [], "logs": [], "patches": []}

    # 1. jira_info.md (required)
    jira_info_path = os.path.join(bug_dir, "jira_info.md")
    if not os.path.isfile(jira_info_path):
        return None
    artifacts["jira_info"] = read_file_safe(jira_info_path)

    # 2. Scan other files
    for root, _dirs, files in os.walk(bug_dir):
        for fname in files:
            if fname == "jira_info.md":
                continue
            fpath = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1].lower()

            if ext in (".md", ".txt"):
                artifacts["notes"].append(
                    {"name": fname, "content": read_file_safe(fpath, 20000)}
                )
            elif ext in (".log",):
                # Only read tail of log files
                artifacts["logs"].append(
                    {"name": fname, "content": read_file_safe(fpath, 10000)}
                )
            elif ext in (".diff", ".patch"):
                artifacts["patches"].append(
                    {"name": fname, "content": read_file_safe(fpath, 20000)}
                )

    return artifacts


def collect_git_info(jira_id: str, project_root: str) -> dict:
    """Collect git commits and diffs related to the JIRA ID.

    Returns dict with keys: commits (list of {hash, subject, diff})
    """
    result = {"commits": []}

    try:
        log_output = subprocess.check_output(
            ["git", "log", "--all", "--oneline", "--grep", jira_id],
            cwd=project_root,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=15,
        ).strip()
    except Exception:
        return result

    if not log_output:
        return result

    for line in log_output.splitlines()[:5]:  # Limit to 5 commits
        parts = line.split(None, 1)
        if not parts:
            continue
        commit_hash = parts[0]
        subject = parts[1] if len(parts) > 1 else ""

        # Get diff (truncated)
        try:
            diff = subprocess.check_output(
                ["git", "show", "--stat", "--patch", "--no-color", commit_hash],
                cwd=project_root,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=15,
            )
            # Truncate long diffs
            if len(diff) > 15000:
                diff = diff[:15000] + "\n... (truncated)"
        except Exception:
            diff = ""

        result["commits"].append(
            {"hash": commit_hash, "subject": subject, "diff": diff}
        )

    return result


def generate_markdown(jira_id: str, artifacts: dict, git_info: dict) -> str:
    """Build the experience markdown from collected data.

    This produces a skeleton with all collected raw material organized
    into the template sections. The LLM caller (the Agent) will use
    this raw material to fill in polished prose.
    """
    today = datetime.date.today().isoformat()

    sections = []

    # --- YAML front-matter ---
    sections.append(f"---\njira: {jira_id}\nreviewed: false\ncreated: {today}\n---\n")

    # --- 问题描述 ---
    sections.append("# 问题描述\n")
    # Extract summary from jira_info
    jira_text = artifacts.get("jira_info", "")
    summary_line = ""
    desc_block = ""
    in_desc = False
    for line in jira_text.splitlines():
        if line.startswith("# ") and not summary_line:
            summary_line = line.lstrip("# ").strip()
        if line.strip() == "## 问题描述":
            in_desc = True
            continue
        if in_desc:
            if line.startswith("## "):
                in_desc = False
                continue
            desc_block += line + "\n"

    if summary_line:
        sections.append(f"**{summary_line}**\n")
    if desc_block.strip():
        sections.append(desc_block.strip() + "\n")
    elif not summary_line:
        sections.append("（从 jira_info.md 中未能提取到问题描述，请手动补充）\n")

    # --- 根因分析 ---
    sections.append("\n# 根因分析\n")
    # Pull analysis from notes and comments
    analysis_parts = []
    for note in artifacts.get("notes", []):
        if note["content"].strip():
            analysis_parts.append(f"**{note['name']}:**\n{note['content'][:3000]}\n")

    # Extract AI analysis conclusion from jira_info comments
    in_comment = False
    ai_conclusion = []
    for line in jira_text.splitlines():
        if "AI 辅助分析结论" in line or "根因" in line.lower():
            in_comment = True
        if in_comment:
            ai_conclusion.append(line)
            if len(ai_conclusion) > 20:
                break

    if ai_conclusion:
        analysis_parts.append("\n".join(ai_conclusion) + "\n")

    if analysis_parts:
        sections.append("\n".join(analysis_parts))
    else:
        sections.append("（未找到分析记录，请根据解题过程补充）\n")

    # --- 修复方案 ---
    sections.append("\n# 修复方案\n")
    if git_info["commits"]:
        for c in git_info["commits"]:
            sections.append(f"**Commit `{c['hash']}`**: {c['subject']}\n")
            # Extract --stat part
            stat_lines = []
            for dline in c["diff"].splitlines():
                if dline.startswith(" ") and "|" in dline:
                    stat_lines.append(dline)
                if "files changed" in dline or "file changed" in dline:
                    stat_lines.append(dline)
                    break
            if stat_lines:
                sections.append("```\n" + "\n".join(stat_lines) + "\n```\n")
    elif artifacts.get("patches"):
        for p in artifacts["patches"]:
            sections.append(f"**{p['name']}:**\n```diff\n{p['content'][:5000]}\n```\n")
    else:
        sections.append("（暂无关联提交或 patch 文件）\n")

    # --- 关键代码示例 ---
    sections.append("\n# 关键代码示例\n")
    if git_info["commits"]:
        # Extract the actual diff hunks (first commit, most relevant)
        diff_text = git_info["commits"][0].get("diff", "")
        hunks = extract_diff_hunks(diff_text, max_hunks=3)
        if hunks:
            for hunk in hunks:
                sections.append(f"```diff\n{hunk}\n```\n")
        else:
            sections.append("（未能从 diff 中提取代码片段）\n")
    else:
        sections.append("（暂无关联代码变更）\n")

    # --- 经验与教训 ---
    sections.append("\n# 经验与教训\n")
    sections.append("（请根据本次解题过程，提炼可复用的团队知识和建议）\n")

    return "\n".join(sections)


def extract_diff_hunks(diff_text: str, max_hunks: int = 3) -> list:
    """Extract up to max_hunks diff hunks from a git show output."""
    hunks = []
    current_hunk = []
    in_hunk = False

    for line in diff_text.splitlines():
        if line.startswith("@@"):
            if current_hunk and in_hunk:
                hunks.append("\n".join(current_hunk))
                if len(hunks) >= max_hunks:
                    break
            current_hunk = [line]
            in_hunk = True
        elif in_hunk:
            current_hunk.append(line)
            # Limit hunk size
            if len(current_hunk) > 30:
                current_hunk.append("... (truncated)")
                hunks.append("\n".join(current_hunk))
                current_hunk = []
                in_hunk = False
                if len(hunks) >= max_hunks:
                    break
        elif line.startswith("diff --git"):
            if current_hunk and in_hunk:
                hunks.append("\n".join(current_hunk))
                if len(hunks) >= max_hunks:
                    break
            current_hunk = []
            in_hunk = False

    # Last hunk
    if current_hunk and in_hunk and len(hunks) < max_hunks:
        hunks.append("\n".join(current_hunk))

    return hunks


def write_experience(output_path: str, content: str) -> str:
    """Write experience file, backing up if it already exists.

    Returns the path written.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if os.path.isfile(output_path):
        bak = output_path + ".bak"
        shutil.copy2(output_path, bak)
        print(f"  Backed up existing file to {bak}")
        # Add updated field
        today = datetime.date.today().isoformat()
        content = content.replace(
            "reviewed: false",
            f"reviewed: false\nupdated: {today}",
            1,
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <jira_id> [project_root]")
        sys.exit(1)

    jira_id = sys.argv[1]
    project_root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

    bug_dir = os.path.join(project_root, ".vela_bug", jira_id)
    output_path = os.path.join(
        project_root, "skills", "experiences", f"{jira_id}.md"
    )

    print(f"=== Experience Summarizer ===")
    print(f"JIRA ID:      {jira_id}")
    print(f"Bug dir:      {bug_dir}")
    print(f"Output:       {output_path}")
    print()

    # Step 1: Collect local artifacts
    print("[1/4] Collecting local artifacts ...")
    artifacts = collect_local_artifacts(bug_dir)
    if artifacts is None:
        print(f"❌ 未找到 {bug_dir}/jira_info.md，请先执行 bug 分析流程。")
        sys.exit(1)
    print(
        f"  Found: jira_info + {len(artifacts['notes'])} notes, "
        f"{len(artifacts['logs'])} logs, {len(artifacts['patches'])} patches"
    )

    # Step 2: Collect git info
    print("[2/4] Searching git history ...")
    git_info = collect_git_info(jira_id, project_root)
    print(f"  Found {len(git_info['commits'])} related commit(s)")

    # Step 3: Generate markdown
    print("[3/4] Generating experience document ...")
    content = generate_markdown(jira_id, artifacts, git_info)

    # Step 4: Write file
    print("[4/4] Writing output ...")
    written = write_experience(output_path, content)
    print(f"\n✅ 经验文档已生成：{written}")
    print(f"⚠️  标记为 reviewed: false，需要经过 code review 后合入。")

    # Print content for agent to review
    print("\n--- Generated Content ---")
    print(content)


if __name__ == "__main__":
    main()
