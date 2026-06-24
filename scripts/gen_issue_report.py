#!/usr/bin/env python3
"""Generate an Open Issue report for a GitCode repository.

Reads the GitCode API token from the GITCODE_TOKEN environment variable.
Writes a Markdown report to cann-samples/issues/reports/issue-report-<ts>.md
(sorted by issue number, descending).

Usage:
    GITCODE_TOKEN=xxx python3 scripts/gen_issue_report.py [owner/repo]
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

API_BASE = "https://gitcode.com/api/v5"
DEFAULT_REPO = "cann/cann-samples"
REPORT_DIR = "cann-samples/issues/reports"
CN_TZ = timezone(timedelta(hours=8))  # UTC+8


def fetch_open_issues(owner_repo, token):
    issues = []
    page = 1
    while True:
        url = (
            f"{API_BASE}/repos/{owner_repo}/issues"
            f"?state=open&per_page=100&page={page}&sort=created&direction=desc"
        )
        req = urllib.request.Request(url)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            batch = json.loads(resp.read().decode("utf-8"))
        if not isinstance(batch, list) or not batch:
            break
        issues.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return issues


def parse_ts(ts):
    return datetime.fromisoformat(ts) if ts else None


def human_dur(td):
    if td is None:
        return "—"
    secs = int(td.total_seconds())
    days, rem = divmod(secs, 86400)
    hrs, rem = divmod(rem, 3600)
    mins = rem // 60
    if days > 0:
        return f"{days}天{hrs}小时"
    if hrs > 0:
        return f"{hrs}小时{mins}分"
    return f"{mins}分钟"


def build_report(owner_repo, issues, now):
    issues.sort(key=lambda x: int(x["number"]), reverse=True)
    lines = [
        f"# {owner_repo} Open Issue 报告\n",
        f"- 仓库：[{owner_repo}](https://gitcode.com/{owner_repo})",
        f"- 生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)",
        f"- Open Issue 数量：{len(issues)}",
        "- 排序：按 Issue 编号从大到小\n",
        "| # | 标题 | 链接 | 提出人 | 负责人 | 提出时间 | 最后活动时间 | 存在时长 | 未活动时长 |",
        "|---|------|------|--------|--------|----------|--------------|----------|------------|",
    ]
    for it in issues:
        num = it["number"]
        title = it["title"].replace("|", "\\|").replace("\n", " ").strip()
        link = it["html_url"]
        user = it.get("user") or {}
        reporter = user.get("name") or user.get("login") or "—"
        assignee = it.get("assignee") or {}
        owner = assignee.get("name") or assignee.get("login") or "未指派"
        created = parse_ts(it.get("created_at"))
        updated = parse_ts(it.get("updated_at"))
        created_s = created.strftime("%Y-%m-%d %H:%M:%S") if created else "—"
        updated_s = updated.strftime("%Y-%m-%d %H:%M:%S") if updated else "—"
        age = human_dur(now - created) if created else "—"
        inactive = human_dur(now - updated) if updated else "—"
        lines.append(
            f"| {num} | {title} | [#{num}]({link}) | {reporter} | {owner} "
            f"| {created_s} | {updated_s} | {age} | {inactive} |"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    token = os.environ.get("GITCODE_TOKEN")
    if not token:
        print("ERROR: GITCODE_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    owner_repo = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPO
    now = datetime.now(CN_TZ)

    try:
        issues = fetch_open_issues(owner_repo, token)
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code} when fetching issues: {e.reason}", file=sys.stderr)
        sys.exit(1)

    report = build_report(owner_repo, issues, now)

    os.makedirs(REPORT_DIR, exist_ok=True)
    fname = os.path.join(REPORT_DIR, f"issue-report-{now.strftime('%Y-%m-%d-%H-%M-%S')}.md")
    with open(fname, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Wrote {fname} ({len(issues)} open issues)")
    # Expose path to GitHub Actions steps, if running in CI.
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"report_path={fname}\n")
            f.write(f"issue_count={len(issues)}\n")


if __name__ == "__main__":
    main()
