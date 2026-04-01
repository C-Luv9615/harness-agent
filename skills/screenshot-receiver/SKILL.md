---
name: "screenshot-receiver"
description: "截图接收工具：启动本地 Web 服务并弹出浏览器窗口（Chrome --app 模式），用户通过 ⌘V 粘贴或拖拽图片，图片保存到临时目录供 AI 读取后自动清理。当用户说「给你截图」「贴图」「看截图」「传图片」时使用。"
inclusion: manual
---

# Screenshot Receiver

当用户需要给你传递截图或图片时，使用此 skill。

## 使用流程

1. 找到 `receive.py` 脚本的路径（与本文件同目录），运行：
   ```bash
   python3 <this-skill-dir>/receive.py
   ```

2. 脚本会启动本地 HTTP 服务并自动打开浏览器窗口（Chromium 系浏览器使用 `--app` 模式，无地址栏），用户可以：
   - **⌘V / Ctrl+V** 粘贴剪贴板中的截图
   - **拖拽** 图片文件到页面
   - **Browse** 按钮选择本地文件
   - 支持多次粘贴/拖拽
   - 点击 **Done** 关闭窗口

3. 脚本退出后，stdout 输出图片路径（每行一个），没有图片则输出 `NO_IMAGES`

4. 用你可用的图片读取工具（如文件读取、图片查看等）读取输出的路径

5. **读取完毕后，必须清理临时目录**：
   ```bash
   rm -rf /tmp/kiro-screenshot-*
   ```

## 依赖

- Python 3（标准库，无第三方依赖）
- Chromium 系浏览器（Arc / Chrome / Edge / Brave 等，用于 `--app` 模式；没有则 fallback 到默认浏览器）

## 跨平台支持

- macOS：优先查找 `/Applications/` 下的浏览器
- Linux / 其他：通过 PATH 查找 `google-chrome`、`chromium` 等命令
- Windows：fallback 到 `webbrowser.open()`
