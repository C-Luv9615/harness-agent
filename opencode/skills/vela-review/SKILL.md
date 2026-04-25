---
name: vela-review
description: "Vela/NuttX 嵌入式代码审查。基于 git diff 执行多维度审查，发现问题分级处理（自动修复/等确认/记待办）。commit 前使用。触发词：review, 审查, 代码审查, code review, 检查代码。"
---

# Vela Code Review — 嵌入式代码审查

基于 git diff 对 Vela/NuttX 代码执行多维度审查，发现问题分级处理。

## 输入

```bash
git diff HEAD
```

如果没有未提交的 diff，提示用户"没有待审查的代码变更"并退出。

## 审查流程

### Stage 1: 获取 diff 和意图

1. 执行 `git diff HEAD` 获取完整 diff
2. 统计变更：文件数、新增行数、删除行数
3. 从 `.harness/PROGRESS.md` 读取当前 task 描述，理解变更意图

### Stage 2: Always-on 审查（每次必做）

逐一检查以下 4 个维度，每个维度独立输出发现：

**correctness（正确性）：**
- 逻辑错误：条件判断是否正确、循环边界是否对
- 边界条件：NULL 指针、数组越界、整数溢出
- 状态管理：状态转换是否完整、是否有遗漏的状态
- 错误传播：函数返回值是否检查、错误码是否正确传递
- 意图匹配：实现是否符合 task 描述的目标

**testing（测试）：**
- 新增代码是否有对应的 cmocka 测试
- 断言是否充分（不只是 assert_int_equal(ret, 0)）
- 边界用例是否覆盖（NULL、0、MAX）
- 错误路径是否有测试（mock 依赖返回错误）

**maintainability（可维护性）：**
- 是否有死代码（未使用的变量、不可达的分支）
- 函数是否过长（超过 50 行建议拆分）
- 模块间是否有不必要的耦合
- 命名是否清晰（变量名、函数名能否自解释）

**project-standards（项目规范）：**
- nxstyle 代码风格（2 空格缩进、大括号独占一行）
- Apache 2.0 license header
- NuttX section ordering（Included Files → Pre-processor → Private Types → ...）
- FAR/CODE 指针修饰符

### Stage 3: Conditional 审查（按 diff 内容触发）

检查 diff 涉及的内容，触发对应维度：

| 触发条件 | 维度 | 检查内容 |
|---------|------|---------|
| diff 涉及 `malloc`/`zalloc`/`open`/`fopen` 或指针操作 | **resource-safety** | 每个 malloc 是否有对应 free；每个 open 是否有对应 close；error path 是否释放已分配资源；指针使用前是否检查 NULL |
| diff 涉及 `for`/`while` 循环、中断处理、DMA | **performance** | 循环内是否有不必要的内存分配；是否有可以提到循环外的计算；中断处理是否足够短；是否有不必要的数据拷贝 |
| diff 涉及跨目录的 `#include`、新增头文件 | **architecture** | 是否违反分层（上层不应依赖下层实现细节）；是否引入反向依赖；是否使用全局变量而非参数传递 |
| diff 涉及 `spin_lock`/`mutex`/`sem`/中断处理 | **reliability** | 锁的使用是否正确（参考 nuttx-coding skill 的决策表）；spin_lock 内是否调用了调度 API；是否有竞态条件；错误恢复路径是否完整 |
| diff 变更行数 ≥ 50 | **adversarial** | 主动构造失败场景：如果输入是 NULL 会怎样？如果中途断电会怎样？如果并发调用会怎样？如果内存不足会怎样？ |

未触发的维度跳过，不输出。

### Stage 4: 分级处理

对每个发现的问题，分配级别：

| 级别 | 判断标准 | 处理方式 |
|------|---------|---------|
| **safe_auto** | 修复方式唯一确定，不改变行为（格式、license header、明显的 nxstyle 违规） | 自动修复，告知用户 |
| **gated_auto** | 有明确修复方案，但涉及行为变更（加 NULL 检查、加 error path、加 close/free） | 展示方案 + 代码位置，等用户确认 |
| **manual** | 需要更大范围讨论或设计决策（架构调整、接口重设计、策略变更） | 追加到 `.harness/PROGRESS.md` 的 `## 待办` 区域 |

### Stage 5: 输出审查报告

```
📋 Vela Code Review 完成
  变更：{N} 个文件，+{add} -{del} 行
  审查维度：{已执行的维度列表}

  ✅ safe_auto: {N} 项已自动修复
    - {file}:{line} — {描述}

  ⚠️ gated_auto: {N} 项待确认
    - {file}:{line} — {描述}
      修复方案：{具体代码改动}

  📝 manual: {N} 项已记录待办
    - {描述}

  ✅ 无问题的维度：{列表}

是否确认 gated_auto 修复？[y/n]
```

如果所有维度都无问题：
```
📋 Vela Code Review 完成 — 无问题
  变更：{N} 个文件，+{add} -{del} 行
  审查维度：{已执行的维度列表}
  ✅ 全部通过
```

## 关键规则

1. **只审查 diff 中的代码** — 不审查 diff 之外的已有代码（除非 diff 引入了对已有代码的依赖）
2. **每个发现必须有具体位置** — file:line，不能只说"建议改进错误处理"
3. **safe_auto 必须是确定性修复** — 如果修复方式有多种选择，就不是 safe_auto
4. **不阻塞提交** — manual 级问题记待办，不阻止 commit
5. **gated_auto 用户拒绝则降级为 manual** — 记待办，继续
