# enhance-knowledge-system

## Goal
- 完成 `openspec/changes/enhance-knowledge-system` 的 typed knowledge document 基础能力：类型、注入配置、摘要、检索、前端入口数据和验证。

## Phases
- [x] 阅读 OpenSpec proposal/design/spec/tasks，并执行 OpenSpec validate
- [x] 梳理现有 knowledge、memory、bootstrap 和上下文装配边界
- [x] 实现后端 knowledge 模型、服务、API 与兼容路径
- [x] 接入 AI 上下文注入策略与前端数据
- [x] 验证 typed knowledge 与 memory 分离，并回填 OpenSpec tasks

## Notes
- `openspec.cmd` 可运行；`openspec.ps1` 会被 PowerShell 执行策略拦截。
- `openspec.cmd` 会尝试 flush PostHog 并出现网络错误，但本地 validate/status/instructions 仍成功。
- ACE 代码索引因 `ACE_TOKEN` 失效不可用，改用本地文件分析。
- 工作区已有 `.ace-tool/index.json` 修改，当前任务不触碰该文件。
- `python -m pytest` 当前环境未安装；新增测试支持直接 `python` 执行。
