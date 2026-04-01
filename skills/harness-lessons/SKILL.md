---
name: harness-lessons
description: "将踩坑经验沉淀到 .harness/lessons-learned.md，带 tags 和 module 标签，支持后续 grep 检索。当完成一个 task/fix 后触发，或用户说 '记录经验'、'沉淀'、'踩坑了'、'lessons' 时使用。"
---

# Harness Lessons — 经验沉淀

将开发过程中的踩坑经验结构化写入 `.harness/lessons-learned.md`。

## 触发时机

- 每个 task 完成后，harness agent 询问"这次踩坑了吗？"
- fix 路径完成后的经验检查
- 用户主动说"记录经验"、"踩坑了"、"lessons"

## 流程

### Step 1: 收集信息

从当前上下文中提取：

| 字段 | 来源 | 必填 |
|------|------|------|
| task_id | PROGRESS.md 当前 task 编号 | 是 |
| title | 一句话描述踩了什么坑 | 是 |
| tags | 关键词，用于 grep 检索（如 cmocka, timer, linker） | 是 |
| module | 涉及的模块名（如 charger, test-infra, audio） | 是 |
| content | 具体经验描述（1-3 行） | 是 |
| files | 相关源文件路径，逗号分隔（用于过期检测） | 否 |
| confidence | 置信度 1-10（10=亲手验证，5=推测，1=道听途说） | 否（默认 7） |
| jira | 关联的 JIRA ID（如有） | 否 |

如果信息不完整，向用户询问缺失字段。

### Step 2: 格式化条目

```markdown
### [{task_id}] {title}
- **tags**: {tag1}, {tag2}, {tag3}
- **module**: {module}
- **files**: {file1}, {file2}
- **confidence**: {N}
- **jira**: {jira_id}
- {content}
```

无 JIRA 时省略 jira 行。无 files 时省略 files 行。confidence 默认 7。

### Step 3: 检查重复

grep `.harness/lessons-learned.md` 搜索 title 中的关键词，如果已有高度相似的条目：
- 展示已有条目
- 询问用户：追加新条目 / 更新已有条目 / 跳过

### Step 4: 写入文件

追加到 `.harness/lessons-learned.md` 末尾。

如果文件不存在，先创建带模板头的文件：

```markdown
# Lessons Learned

经验沉淀，每条带 tags 和 module，支持 grep 检索。

---

```

### Step 5: 确认

```
✅ 经验已沉淀到 .harness/lessons-learned.md
  [{task_id}] {title}
  tags: {tags}
```

## 检索方式

其他阶段（如 implement 的经验检索）通过 grep 搜索：

```bash
grep -i "charger\|statemachine" .harness/lessons-learned.md
```

### 过期检测

检索命中后，如果条目包含 `files` 字段，检查这些文件是否仍然存在：

```bash
# 对每个 files 中的路径执行
ls {file_path} 2>/dev/null || echo "STALE: {file_path} 不存在"
```

- 所有文件都存在 → 正常使用该经验
- 部分文件不存在 → 提示"⚠️ 此经验引用的 {file_path} 已不存在，可能已过时，请谨慎参考"
- 用户可在 evolve 阶段统一清理过期条目

## 示例

输入：
```
task_id: Task-5
title: spin_lock_irqsave 内不能调用 nxsem_post
tags: spinlock, semaphore, irq, sync
module: charger
files: drivers/charger/charger_sm.c, include/nuttx/spinlock.h
confidence: 9
content: spin_lock_irqsave 持有期间禁止任何调度 API。需要 post-type 唤醒时改用 spin_lock_irqsave_nopreempt。
```

输出写入 `.harness/lessons-learned.md`：
```markdown
### [Task-5] spin_lock_irqsave 内不能调用 nxsem_post
- **tags**: spinlock, semaphore, irq, sync
- **module**: charger
- **files**: drivers/charger/charger_sm.c, include/nuttx/spinlock.h
- **confidence**: 9
- spin_lock_irqsave 持有期间禁止任何调度 API。需要 post-type 唤醒时改用 spin_lock_irqsave_nopreempt。
```
