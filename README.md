# 彩票数据采集项目

用于自动获取中国福彩双色球和体彩超级大乐透的开奖数据。

## 项目结构

```
.
├── .github/
│   └── workflows/
│       └── lottery-schedule.yml  # GitHub Actions 定时任务
├── scripts/                       # 脚本目录
│   ├── dlt_fetcher.py             # 大乐透数据采集脚本
│   ├── ssq_fetcher.py             # 双色球数据采集脚本
│   └── scheduler.py               # 调度脚本（按星期自动执行）
└── data/                          # 数据目录
    ├── dlt_history.json           # 大乐透历史数据(JSON格式)
    ├── dlt_history.csv            # 大乐透历史数据(CSV格式)
    ├── ssq_history.json           # 双色球历史数据(JSON格式)
    └── ssq_history.csv            # 双色球历史数据(CSV格式)
```

## 脚本说明

### 双色球脚本 (ssq_fetcher.py)

获取福彩双色球开奖数据。

**API来源**: https://gdwechat.daguoxiaoxian.com/api/lottery-results/list

**使用方式**:
```bash
# 获取最新一期数据（仅输出，不写入文件）
python scripts/ssq_fetcher.py --latest

# 获取最新一期并增量更新到现有JSON文件（期号已存在则跳过）
python scripts/ssq_fetcher.py --update

# 获取近10年历史数据（保存到 data/ 目录）
python scripts/ssq_fetcher.py --history

# 获取最近N个月的数据（保存到 data/ 目录）
python scripts/ssq_fetcher.py --recent 3

# 仅输出不写入文件（与 --history 或 --recent 配合使用）
python scripts/ssq_fetcher.py --recent 3 --dry-run
```

### 大乐透脚本 (dlt_fetcher.py)

获取体彩超级大乐透开奖数据。

**数据来源**: https://kaijiang.500.com/static/info/kaijiang/xml/dlt/list.xml

> 说明：此前使用 `webapi.sporttery.cn` 的 JSON API，但该站点的 WAF 会封禁境外 IP（GitHub Actions runner 在美国 Azure 段），返回 HTTP 567，无论 headers 如何伪装都无法绕过。现改用 500.com 的静态 XML 端点（走 CDN/静态托管，不触发 WAF），一次返回全部历史期次（约 2800+ 期，回溯到 2007 年），无需分页。

**使用方式**:
```bash
# 获取最新一期数据（仅输出，不写入文件）
python scripts/dlt_fetcher.py --latest

# 获取最新一期并增量更新到现有JSON和CSV文件（期号已存在则跳过）
python scripts/dlt_fetcher.py --update

# 获取全部历史数据（保存到 data/ 目录）
python scripts/dlt_fetcher.py --history

# 获取最近N个月的数据（保存到 data/ 目录）
python scripts/dlt_fetcher.py --recent 3

# 仅输出不写入文件（与 --history 或 --recent 配合使用）
python scripts/dlt_fetcher.py --recent 3 --dry-run
```

### 调度脚本 (scheduler.py)

根据北京时间判断当天开奖的彩票类型，并调用对应脚本获取最新数据。支持通过环境变量传参实现按需获取。

**开奖时间（北京时间）**:
| 星期 | 开奖类型 |
|------|----------|
| 周一 | 大乐透 |
| 周二 | 双色球 |
| 周三 | 大乐透 |
| 周四 | 双色球 |
| 周五 | 无 |
| 周六 | 大乐透 |
| 周日 | 双色球 |

> 由于 GitHub Actions 的 schedule 可能延迟（甚至跨天），为保证数据完整性，默认每次都同时获取双色球和大乐透的最新数据。`update_latest` 内部会按期号去重，已存在的不会重复写入。

**环境变量参数**:

| 变量 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| `LOTTERY` | `both` / `ssq` / `daletou` | `both` | 获取哪个彩种 |
| `FETCH_MODE` | `update` / `history` | `update` | `update` 增量更新最新一期；`history` 全量刷新历史数据 |

**使用方式**:
```bash
# 默认：同时获取双色球和大乐透的最新一期（增量更新）
python scripts/scheduler.py

# 只获取大乐透
LOTTERY=daletou python scripts/scheduler.py

# 全量刷新双色球历史数据
LOTTERY=ssq FETCH_MODE=history python scripts/scheduler.py
```

## 数据格式

### JSON格式

```json
{
  "generated_at": "2026-06-22 13:57:33",
  "source": "kaijiang.500.com",
  "game": "超级大乐透",
  "game_no": "85",
  "total": 2887,
  "items": [
    {
      "term": "26069",
      "draw_time": "2026-06-22 21:25:00",
      "draw_result": "12,19,21,24,29|03,10",
      "front_numbers": ["12", "19", "21", "24", "29"],
      "back_numbers": ["03", "10"]
    }
  ]
}
```

双色球与大乐透使用相同的字段结构，区别如下：

| 字段 | 双色球 | 大乐透 |
|------|--------|--------|
| `source` | daguoxiaoxian.com | kaijiang.500.com |
| `game` | 双色球 | 超级大乐透 |
| `game_no` | ssq | 85 |
| `front_numbers` | 6个红球 | 5个前区号码 |
| `back_numbers` | 1个蓝球 | 2个后区号码 |
| `draw_result` 格式 | 逗号分隔，如 `03,08,19,25,31,33,05` | 前后区用 `\|` 分隔，如 `12,19,21,24,29\|03,10` |

### CSV格式

| term | draw_time | draw_result | front_numbers | back_numbers |
|------|-----------|-------------|---------------|--------------|
| 26069 | 2026-06-22 | 12 19 21 24 29 03 10 | ['12', '19', '21', '24', '29'] | ['03', '10'] |

## GitHub Actions 定时任务

项目已配置 GitHub Actions（[.github/workflows/lottery-schedule.yml](.github/workflows/lottery-schedule.yml)）：

### 触发方式

| 触发方式 | 说明 |
|----------|------|
| `schedule` | 北京时间每天 22:30（UTC 14:30）自动执行 |
| `push` | push 到 main 分支时执行（忽略 `data/`、`.github/`、`README.md` 变更，避免死循环） |
| `workflow_dispatch` | 在 Actions 页面手动触发，支持选择彩种和模式 |

### 手动触发参数

在 Actions 页面点 "Run workflow" 时可选择：

- **lottery**：`both`（默认，同时获取双色球和大乐透）/ `ssq`（仅双色球）/ `daletou`（仅大乐透）
- **mode**：`update`（默认，增量更新最新一期）/ `history`（全量刷新历史数据）

### 执行流程

1. 检出代码 → 安装 Python 3.11 + requests
2. 设置北京时间时区
3. 运行 `scripts/scheduler.py`（通过环境变量 `LOTTERY`/`FETCH_MODE` 注入参数）
4. 若 `data/` 目录有变更，自动 commit 并 push 到仓库

## 时区说明

脚本使用北京时间(UTC+8)进行判断，适用于GitHub Actions等UTC时区环境。

## 注意事项

1. 请合理使用API，避免频繁请求
2. 数据仅供参考，请以官方公布为准
3. 建议定期更新脚本以适应API变化
4. GitHub Actions 的 `schedule` 触发可能延迟数分钟（高峰期甚至延迟到跨天），属正常现象；因此 scheduler 默认每次都同时获取两种彩种，按期号去重保证数据完整
5. 大乐透数据源（`webapi.sporttery.cn`、`500.com` 主站）会封禁境外 IP 返回 HTTP 567，本项目改用 500.com 的静态 XML 端点绕过此限制

## 许可证

MIT License
