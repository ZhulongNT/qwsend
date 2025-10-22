# Copilot 项目指南（qwsend）

本仓库是一个基于 httpx 的企业微信（WeCom）Webhook 客户端，提供同步与异步 API 以及命令行工具。下述要点将帮助 AI 代理在本仓库快速高效地工作。

## 架构与边界
- 包结构（src 布局）：`src/qwsend/`
  - `client.py`：核心同步 `WebhookClient` 与异步 `AsyncWebhookClient`，封装发送消息与上传媒体；内部工具 `_ensure_ok` 统一处理响应；常量 `DEFAULT_BASE`、`SEND_PATH`、`UPLOAD_PATH` 定义 API 入口。
  - `exceptions.py`：异常层次结构，`HTTPError`（非 200/非 ok JSON）、`RateLimit`（errcode=45009）。
  - `cli.py`：命令行入口（由 `pyproject.toml` entry_points 暴露为 `qwsend`）。
  - `version.py`：版本定义；与 `pyproject.toml` 保持同步（升级时两处同改）。
  - `__init__.py`：公共导出（`__all__`）。
- 外部协议：企业微信 Webhook（详见根目录 `webhook.md`），所有发送统一走 `https://qyapi.weixin.qq.com/cgi-bin` 下的 `/webhook/send` 与 `/webhook/upload_media`。

## 关键约定与易踩点
- User-Agent 约定：组装为 `qwsend/<version> (+https://pypi.org/project/qwsend/)`（见 `_build_user_agent`）。更改 UA 形态需同步调整测试期望。
- 统一响应处理：`_ensure_ok(resp)` 强制：HTTP 200 + 可解析 JSON + `errcode==0`；否则抛 `HTTPError`；当 `errcode==45009` 抛 `RateLimit`。
- Content-Type 处理：默认使用 `application/json`；`upload_media` 会复制默认头并删除 `Content-Type` 以便 httpx 自动设置 multipart boundary（非 wet 模式）。
- upload_media（文件/语音）双路径：
  - 当环境变量 `QWSEND_WEBHOOK_KEY` 存在（wet 模式），手工构造 multipart（含 `filelength`）并显式设置 `Content-Type`，以满足官方协议；
  - 否则（dry 模式）使用 httpx `files={"media": (...)}`，便于测试对调用参数进行断言。
- 类型约束：`upload_media(type_)` 仅允许 `"file"|"voice"`，否则抛 `ValueError`。
- 日志：`logging.basicConfig(level=INFO)`；`_ensure_ok` 会记录响应 `text`。

## 开发与测试工作流（Windows/PowerShell）
  - `pip install -e .[dev]`
## 开发与测试工作流（Windows/PowerShell）
 - 开发安装：
   - `pip install -e .[dev]`
 - 运行测试：
   - Dry（默认，无外网依赖）：`pytest`
   - Wet（真实调用）：先设置 `$env:QWSEND_WEBHOOK_KEY='<your_key>'`，再运行 `pytest`。当该环境变量存在时，测试套件会包含 wet（live webhook）测试。

## 使用示例与模式
- 同步：
  - `WebhookClient.send_text/markdown/markdown_v2/image/news/file/voice/template_card`
  - `upload_media(bytes, filename, type_="file"|"voice") -> {"media_id": ...}` 后再 `send_file/send_voice`
- 异步：接口与同步一致，方法前缀为 `await ...`；资源释放用 `aclose()`。
- CLI：
 - CLI：
   - 设置 `$env:QWSEND_WEBHOOK_KEY` 或传 `--key`；
   - 使用子命令选择消息类型（text/markdown/image/news/upload/send-file/send-voice/template-card），例如：
     - 文本：`qwsend text "hello"`
     - Markdown：`qwsend markdown "**bold**" --v2`
     - 上传并发送文件：
       - 上传：`qwsend upload -f .\\path\\to\\file.pdf --type file`
       - 发送：`qwsend send-file <media_id>`

## 变更影响与测试契约
- 发送 JSON 结构在测试中有精确断言（键名与层级），修改字段请同步更新 `tests/test_client.py`。
- 维持 `upload_media` 的双路径行为与 `filelength` 拼接逻辑，以兼容官方接口与 dry 测试。
- 若调整异常类型或文案，确保与 `_ensure_ok`/`exceptions.py` 的语义保持一致，并更新断言。

## 参考文件
- 实现：`src/qwsend/client.py`, `src/qwsend/exceptions.py`, `src/qwsend/cli.py`, `src/qwsend/version.py`
- 协议：`webhook.md`
- 用法与发布：`README.md`, `pyproject.toml`
- 测试：`tests/test_client.py`, `tests/fixtures/*`
