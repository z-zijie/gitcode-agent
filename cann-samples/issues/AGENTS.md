# cann-samples Issue 报告工作流

本目录用于归档 GitCode 仓库 [`cann/cann-samples`](https://gitcode.com/cann/cann-samples) 的 Open Issue 报告。
生成的报告存放在 `reports/` 子目录。

## 工作流概述

| 步骤 | 说明 |
|------|------|
| 1. 拉取 | 通过 GitCode REST API v5 拉取 `state=open` 的全部 Issue（分页） |
| 2. 解析 | 提取所需字段，计算时长 |
| 3. 排序 | 按 Issue 编号（`number`）从大到小 |
| 4. 渲染 | 生成 Markdown 表格 |
| 5. 归档 | 写入 `reports/issue-report-YYYY-MM-DD-HH-MM-SS.md`，并 commit & push |

### 报告字段与 API 字段映射

| 报告列 | API 字段 | 备注 |
|--------|----------|------|
| 标题 | `title` | 转义 `\|` 和换行 |
| 链接 | `html_url` | |
| 提出人 | `user.name`（回退 `user.login`） | |
| 负责人 | `assignee.name`（回退 `login`） | 为空时记为「未指派」 |
| 提出时间 | `created_at` | ISO8601，含 `+08:00` 时区 |
| 最后活动时间 | `updated_at` | |
| 存在时长 | `now - created_at` | now 取 UTC+8 当前时刻 |
| 未活动时长 | `now - updated_at` | |

### 文件命名

`reports/issue-report-YYYY-MM-DD-HH-MM-SS.md`，时间戳为生成时刻（UTC+8）。

---

## GitCode REST API v5 使用方法

- **Base URL**：`https://gitcode.com/api/v5`
- **认证**：读操作（GET）一般免认证；写操作需 `-H "Authorization: Bearer $GITCODE_TOKEN"`。
  也可用 `-H "PRIVATE-TOKEN: $GITCODE_TOKEN"` 或 query 参数 `?access_token=$GITCODE_TOKEN`。
- **限流**：400 次/分钟、4000 次/小时，超限返回 `429`，需退避重试。
- **稳健性**：curl 务必加 `--max-time`（如 30s）防止个别请求挂起拖垮整个分页循环。

### 拉取 Open Issue（分页）

```bash
export GITCODE_TOKEN=<your_token>

# 单页：state=open，每页最多 100，按创建时间倒序
curl -s --max-time 30 \
  "https://gitcode.com/api/v5/repos/cann/cann-samples/issues?state=open&per_page=100&page=1&sort=created&direction=desc" \
  -H "Authorization: Bearer $GITCODE_TOKEN"
```

分页逻辑：从 `page=1` 起循环，单页返回 `< 100` 条即为最后一页；`= 0` 条停止。

**常用查询参数**：

| 参数 | 取值 | 说明 |
|------|------|------|
| `state` | `open` / `closed` / `all` | Issue 状态 |
| `per_page` | 1–100 | 每页条数 |
| `page` | ≥1 | 页码 |
| `sort` | `created` / `updated` | 排序字段 |
| `direction` | `asc` / `desc` | 排序方向 |

> 注：API 的 `sort`/`direction` 用于服务端排序；报告要求「按编号倒序」，仍需在本地按 `number` 再排一次。

### 单个 Issue / 其他常用端点

```bash
# 获取单个 Issue
curl -s "https://gitcode.com/api/v5/repos/cann/cann-samples/issues/{number}" \
  -H "Authorization: Bearer $GITCODE_TOKEN"

# 创建 Issue（注意：实际可用路径含 {repo}）
curl -s -X POST "https://gitcode.com/api/v5/repos/cann/cann-samples/issues" \
  -H "Authorization: Bearer $GITCODE_TOKEN" -H "Content-Type: application/json" \
  -d '{"title": "标题", "body": "描述"}'

# 关闭 / 重开 / 改标题
curl -s -X PATCH "https://gitcode.com/api/v5/repos/cann/issues/{number}" \
  -H "Authorization: Bearer $GITCODE_TOKEN" -H "Content-Type: application/json" \
  -d '{"state": "closed"}'

# 评论
curl -s -X POST "https://gitcode.com/api/v5/repos/cann/cann-samples/issues/{number}/comments" \
  -H "Authorization: Bearer $GITCODE_TOKEN" -H "Content-Type: application/json" \
  -d '{"body": "评论内容"}'
```

### Issue 对象关键字段（响应示例节选）

```json
{
  "number": "209",
  "title": "[Documentation|文档反馈]: ...",
  "html_url": "https://gitcode.com/cann/cann-samples/issues/209",
  "state": "open",
  "user":     { "login": "gcw_8UjZBGvp", "name": "gcw_8UjZBGvp" },
  "assignee": { "login": "yangyang016", "name": "yangyang016" },
  "created_at": "2026-06-21T23:19:04+08:00",
  "updated_at": "2026-06-22T09:55:03+08:00",
  "issue_state": "进行中",
  "issue_type": "任务"
}
```

### 已知坑

1. **创建 Issue 的路径不一致**：官方文档写 `POST /repos/{owner}/issues`（无 `{repo}`），实践中 `POST /repos/{owner}/{repo}/issues` 才稳定可用。一个返回 404 就换另一个。
2. **`assignee` 无法通过 PATCH 设置**：v5 会忽略更新请求里的 `assignee`。要指派需以评论形式发送 `/assign` 机器人命令。
3. **owner 大小写不敏感**：`cann` 与 `CANN` 均可访问同一仓库。
