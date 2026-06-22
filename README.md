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

**API来源**: https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry

**使用方式**:
```bash
# 获取最新一期数据（仅输出，不写入文件）
python scripts/dlt_fetcher.py --latest

# 获取最新一期并增量更新到现有JSON文件（期号已存在则跳过）
python scripts/dlt_fetcher.py --update

# 获取近10年历史数据（保存到 data/ 目录）
python scripts/dlt_fetcher.py --history

# 获取最近N个月的数据（保存到 data/ 目录）
python scripts/dlt_fetcher.py --recent 3

# 仅输出不写入文件（与 --history 或 --recent 配合使用）
python scripts/dlt_fetcher.py --recent 3 --dry-run
```

### 调度脚本 (scheduler.py)

根据北京时间自动判断当天开奖的彩票类型，并调用对应脚本以 `--update` 模式增量更新最新数据。

**开奖时间（北京时间）**:
| 星期 | 开奖类型 |
|------|----------|
| 周一 | 大乐透 |
| 周二 | 双色球 |
| 周三 | 大乐透 |
| 周四 | 双色球 |
| 周五 | 无（同时获取双色球和大乐透最新数据） |
| 周六 | 大乐透 |
| 周日 | 双色球 |

**使用方式**:
```bash
python scripts/scheduler.py
```

## 数据格式

### JSON格式

```json
{
  "generated_at": "2026-06-22 13:57:33",
  "source": "sporttery.cn",
  "game": "超级大乐透",
  "game_no": "85",
  "total": 1494,
  "items": [
    {
      "term": "26069",
      "draw_time": "2026-06-22",
      "draw_result": "12 19 21 24 29 03 10",
      "front_numbers": ["12", "19", "21", "24", "29"],
      "back_numbers": ["03", "10"]
    }
  ]
}
```

双色球与大乐透使用相同的字段结构，区别如下：

| 字段 | 双色球 | 大乐透 |
|------|--------|--------|
| `source` | daguoxiaoxian.com | sporttery.cn |
| `game` | 双色球 | 超级大乐透 |
| `game_no` | ssq | 85 |
| `front_numbers` | 6个红球 | 5个前区号码 |
| `back_numbers` | 1个蓝球 | 2个后区号码 |

### CSV格式

| term | draw_time | draw_result | front_numbers | back_numbers |
|------|-----------|-------------|---------------|--------------|
| 26069 | 2026-06-22 | 12 19 21 24 29 03 10 | ['12', '19', '21', '24', '29'] | ['03', '10'] |

## GitHub Actions 定时任务

项目已配置 GitHub Actions 定时任务（[.github/workflows/lottery-schedule.yml](.github/workflows/lottery-schedule.yml)）：

- **执行时间**：北京时间每天 22:30（UTC 14:30）
- **执行内容**：运行 `scripts/scheduler.py`，增量更新当天开奖数据
- **自动提交**：若 data 目录有变更，自动 commit 并 push 到仓库
- **手动触发**：支持在 Actions 页面手动运行（workflow_dispatch）

## 时区说明

脚本使用北京时间(UTC+8)进行判断，适用于GitHub Actions等UTC时区环境。

## 注意事项

1. 请合理使用API，避免频繁请求
2. 数据仅供参考，请以官方公布为准
3. 建议定期更新脚本以适应API变化
4. GitHub Actions 定时任务可能存在几分钟延迟，属正常现象

## 许可证

MIT License
