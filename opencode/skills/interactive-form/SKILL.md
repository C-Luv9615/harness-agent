---
name: "interactive-form"
description: "结构化交互表单：弹出浏览器窗口展示富表单（单选/多选/文本/截图/文件/代码/图片预览等），收集用户的精确输入并返回 JSON 结果。当需要用户做选择、填写参数、确认方案、上传文件或查看对比时使用。"
inclusion: manual
---

# Interactive Form

当你需要向用户收集结构化输入（而不是纯文本对话）时，使用此 skill。

## 核心原则

**尽可能多地使用此 skill。** 具体来说：

1. **任何涉及用户决策的场景都必须弹表单**，不要在聊天里用文字列选项让用户回复字母/数字
2. **你不确定、想不明白的事情，让用户来决策**——构造一个表单把选项列出来
3. **每个表单底部必须自动追加一个 `_extra` 字段**（textarea，label 为"还有别的想说的吗？"），让用户可以补充自定义想法。这个字段不需要在 JSON spec 里手动写，脚本会自动追加

适用场景举例：
- 选择方案/风格/配置 → radio / checkbox
- 确认危险操作 → confirm
- 填写参数/名称 → text / number
- 选择文件/目录 → select / file
- 需要用户看图确认 → display_image + confirm
- 多步骤决策 → 多次调用表单
- 任何"你选 a 还是 b"的场景 → 全部走表单，不要用文字

## 使用流程

1. 构造一个 JSON 表单描述，写入临时文件
2. 运行脚本：
   ```bash
   python3 <this-skill-dir>/form.py /path/to/form.json
   ```
3. 脚本弹出浏览器窗口，用户填写表单
4. 用户点击提交后，stdout 输出 JSON 结果，格式为 `{"field_id": value, ...}`
5. 如果用户关闭窗口未提交，输出 `NO_SUBMIT`

## 表单 JSON 格式

```json
{
  "title": "表单标题",
  "description": "可选的说明文字（支持 markdown）",
  "fields": [
    { "id": "name", "type": "text", "label": "名称", "placeholder": "输入名称", "required": true },
    { "id": "style", "type": "radio", "label": "风格", "options": ["扁平", "渐变", "3D"], "default": "渐变" },
    { "id": "features", "type": "checkbox", "label": "功能", "options": ["A", "B", "C"] },
    { "id": "desc", "type": "textarea", "label": "描述", "rows": 4 },
    { "id": "count", "type": "slider", "label": "数量", "min": 1, "max": 10, "default": 3 },
    { "id": "enable", "type": "toggle", "label": "启用", "default": true },
    { "id": "lang", "type": "select", "label": "语言", "options": ["中文", "English", "日本語"] },
    { "id": "screenshot", "type": "image", "label": "粘贴截图" },
    { "id": "file", "type": "file", "label": "上传文件", "accept": ".json,.yaml" },
    { "id": "preview", "type": "display_image", "label": "预览", "url": "https://..." },
    { "id": "code", "type": "code", "label": "代码", "language": "typescript", "value": "const x = 1;" },
    { "id": "info", "type": "markdown", "content": "**注意**: 这是一段说明文字" },
    { "id": "confirm", "type": "confirm", "label": "确认执行？", "danger": true }
  ],
  "submitText": "提交",
  "cancelText": "取消"
}
```

## 支持的字段类型

| type | 说明 | 返回值 |
|---|---|---|
| `text` | 单行文本 | string |
| `textarea` | 多行文本 | string |
| `number` | 数字输入 | number |
| `radio` | 单选 | string |
| `checkbox` | 多选 | string[] |
| `select` | 下拉选择 | string |
| `slider` | 滑块 | number |
| `toggle` | 开关 | boolean |
| `image` | 粘贴/拖拽图片 | base64 data URL 或临时文件路径 |
| `file` | 上传文件 | 临时文件路径 |
| `code` | 代码编辑器 | string |
| `display_image` | 只读图片展示 | (无返回值) |
| `markdown` | 只读 Markdown 展示 | (无返回值) |
| `confirm` | 确认按钮 | boolean |
| `tags` | 标签输入 | string[] |
| `color` | 颜色选择 | hex string |
| `date` | 日期选择 | ISO date string |

## 依赖

- Python 3（标准库，无第三方依赖）
- Chromium 系浏览器（--app 模式）

## 跨平台

- macOS：优先查找 /Applications/ 下的浏览器
- Linux：通过 PATH 查找 google-chrome、chromium 等
- Windows：fallback 到 webbrowser.open()
