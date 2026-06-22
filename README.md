# 彩票数据采集项目

用于自动获取中国福彩双色球和体彩超级大乐透的开奖数据。

## 项目结构

```
.
├── scripts/           # 脚本目录
│   ├── dlt_fetcher.py     # 大乐透数据采集脚本
│   ├── ssq_fetcher.py     # 双色球数据采集脚本
│   └── scheduler.py       # 调度脚本（按星期自动执行）
└── data/              # 数据目录
    ├── dlt_history.json   # 大乐透历史数据(JSON格式)
    ├── dlt_history.csv    # 大乐透历史数据(CSV格式)
    ├── ssq_history.json   # 双色球历史数据(JSON格式)
    └── ssq_history.csv    # 双色球历史数据(CSV格式)
```

## 脚本说明

### 双色球脚本 (ssq_fetcher.py)

获取福彩双色球开奖数据。

**API来源**: https://gdwechat.daguoxiaoxian.com/api/lottery-results/list

**使用方式**:
```bash
# 获取最新一期数据
python scripts/ssq_fetcher.py --latest

# 获取近10年历史数据（保存到 data/ 目录）
python scripts/ssq_fetcher.py --history
```

### 大乐透脚本 (dlt_fetcher.py)

获取体彩超级大乐透开奖数据。

**API来源**: https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry

**使用方式**:
```bash
# 获取最新一期数据
python scripts/dlt_fetcher.py --latest

# 获取近10年历史数据（保存到 data/ 目录）
python scripts/dlt_fetcher.py --history
```

### 调度脚本 (scheduler.py)

根据北京时间自动判断当天开奖的彩票类型，并调用对应脚本获取最新数据。

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
[
  {
    "期号": "26069",
    "开奖日期": "2026-06-22",
    "开奖号码": "12 19 21 24 29 03 10"
  }
]
```

### CSV格式

| 期号 | 开奖日期 | 开奖号码 |
|------|----------|----------|
| 26069 | 2026-06-22 | 12 19 21 24 29 03 10 |

## 时区说明

脚本使用北京时间(UTC+8)进行判断，适用于GitHub Actions等UTC时区环境。

## GitHub Actions 使用建议

可以配置 GitHub Actions 定时任务，每天自动执行调度脚本：

```yaml
name: Lottery Data Update

on:
  schedule:
    - cron: '30 10 * * *'  # 北京时间 18:30（UTC 10:30）
  
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - name: Install dependencies
        run: pip install requests
      - name: Run scheduler
        run: python scripts/scheduler.py
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add data/
          git commit -m "Update lottery data" -a || true
          git push
```

## 注意事项

1. 请合理使用API，避免频繁请求
2. 数据仅供参考，请以官方公布为准
3. 建议定期更新脚本以适应API变化

## 许可证

MIT License
