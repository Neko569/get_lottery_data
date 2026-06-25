# 彩票数据采集项目

用于自动获取中国福彩和体彩共 8 个彩种的开奖数据。

## 支持的彩种

| 彩种 | 类型 | 开奖频率 | 数据源 |
|-------|------|-----------|--------|
| 双色球（ssq） | 福彩 | 周二、四、日 | daguoxiaoxian.com |
| 福彩3D（fc3d） | 福彩 | 每日 | 500.com |
| 七乐彩（qlc） | 福彩 | 周一、三、五 | 500.com |
| 快乐八（kl8） | 福彩 | 每日 | 500.com |
| 大乐透（dlt） | 体彩 | 周一、三、六 | 500.com |
| 七星彩（qxc） | 体彩 | 周二、五、日 | 500.com |
| 排列三（pls） | 体彩 | 每日 | 500.com |
| 排列五（plw） | 体彩 | 每日 | 500.com |

## 项目结构

```
.
├── .github/
│   └── workflows/
│       └── lottery-schedule.yml  # GitHub Actions 定时任务
├── scripts/                       # 脚本目录
│   ├── scheduler.py               # 调度脚本（按星期自动执行）
│   ├── ssq_fetcher.py             # 双色球数据采集
│   ├── dlt_fetcher.py             # 大乐透数据采集
│   ├── qxc_fetcher.py             # 七星彩数据采集
│   ├── pls_fetcher.py             # 排列三数据采集
│   ├── plw_fetcher.py             # 排列五数据采集
│   ├── fc3d_fetcher.py            # 福彩3D数据采集
│   ├── qlc_fetcher.py             # 七乐彩数据采集
│   └── kl8_fetcher.py             # 快乐八数据采集
└── data/                          # 数据目录
    ├── ssq_history.json / .csv
    ├── dlt_history.json / .csv
    ├── qxc_history.json / .csv
    ├── pls_history.json / .csv
    ├── plw_history.json / .csv
    ├── fc3d_history.json / .csv
    ├── qlc_history.json / .csv
    └── kl8_history.json / .csv
```

## 脚本说明

所有 fetcher 脚本支持相同的命令行参数：

```bash
# 获取最新一期数据（仅输出，不写入文件）
python scripts/<name>_fetcher.py --latest

# 获取最新一期并增量更新到现有文件（期号已存在则跳过）
python scripts/<name>_fetcher.py --update

# 获取全部历史数据
python scripts/<name>_fetcher.py --history

# 获取最近N个月的数据
python scripts/<name>_fetcher.py --recent 3

# 仅输出不写入文件
python scripts/<name>_fetcher.py --recent 3 --dry-run
```

### 数据源说明

- **500.com 静态 XML**：大乐透、七星彩、排列三、排列五、福彩3D、七乐彩、快乐八均使用 `kaijiang.500.com` 的静态 XML 端点，无需分页，可在 GitHub Actions（境外 IP）稳定访问
- **daguoxiaoxian.com API**：双色球使用此 API（分页），需携带 Referer 请求头

### 调度脚本 (scheduler.py)

根据北京时间判断当天开奖的彩票类型，自动调用对应脚本获取最新数据。

**开奖时间（北京时间）**:

| 星期 | 开奖彩种 |
|-------|-----------|
| 周一 | 大乐透、七乐彩、排列三、排列五、福彩3D、快乐八 |
| 周二 | 双色球、七星彩、排列三、排列五、福彩3D、快乐八 |
| 周三 | 大乐透、七乐彩、排列三、排列五、福彩3D、快乐八 |
| 周四 | 双色球、七星彩、排列三、排列五、福彩3D、快乐八 |
| 周五 | 七星彩、七乐彩、排列三、排列五、福彩3D、快乐八 |
| 周六 | 大乐透、排列三、排列五、福彩3D、快乐八 |
| 周日 | 双色球、七星彩、排列三、排列五、福彩3D、快乐八 |

> 排列三、排列五、福彩3D、快乐八为每日开奖，每天都会更新。

**环境变量参数**:

| 变量 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| `LOTTERY` | `all` / `ssq` / `dlt` / `qxc` / `pls` / `plw` / `fc3d` / `qlc` / `kl8` | `all` | 获取哪个彩种 |
| `FETCH_MODE` | `update` / `history` | `update` | `update` 增量更新最新一期；`history` 全量刷新 |

## 数据格式

### JSON格式

```json
{
  "generated_at": "2026-06-22 13:57:33",
  "source": "kaijiang.500.com",
  "game": "七星彩",
  "game_no": "qxc",
  "total": 1024,
  "items": [
    {
      "term": "26071",
      "draw_time": "2026-06-23 21:25:00",
      "draw_result": "4,7,9,6,3,5,7",
      "numbers": ["4", "7", "9", "6", "3", "5", "7"]
    }
  ]
}
```

不同彩种的字段差异：

| 彩种 | 号码字段 | 说明 |
|-------|----------|------|
| 双色球 | `front_numbers` + `back_numbers` | 6红球 + 1蓝球 |
| 大乐透 | `front_numbers` + `back_numbers` | 5前区 + 2后区 |
| 七乐彩 | `front_numbers` + `back_numbers` | 7前区 + 1特别号 |
| 七星彩 | `numbers` | 7个数字（0-9） |
| 排列三 | `numbers` | 3个数字（0-9） |
| 排列五 | `numbers` | 5个数字（0-9） |
| 福彩3D | `numbers` | 3个数字（0-9） |
| 快乐八 | `numbers` | 20个数字（01-80） |

## GitHub Actions 定时任务

项目已配置 GitHub Actions（`.github/workflows/lottery-schedule.yml`）：

### 触发方式

| 触发方式 | 说明 |
|----------|------|
| `schedule` | 北京时间每天 22:30（UTC 14:30）自动执行 |
| `push` | push 到 main 分支时执行（忽略 `data/`、`.github/`、`README.md` 变更） |
| `workflow_dispatch` | 在 Actions 页面手动触发，支持选择彩种和模式 |

### 手动触发参数

在 Actions 页面点 "Run workflow" 时可选择：

- **lottery**：`all`（默认，按当天开奖日自动获取）/ 各彩种简称
- **mode**：`update`（默认，增量更新最新一期）/ `history`（全量刷新历史数据）

## 注意事项

1. 请合理使用API，避免频繁请求
2. 数据仅供参考，请以官方公布为准
3. 建议定期更新脚本以适应API变化
4. 所有使用 500.com 数据源的彩种均通过静态 XML 端点访问，可在 GitHub Actions 境外环境稳定运行
