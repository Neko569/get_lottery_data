#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彩票开奖调度脚本
根据北京时间判断当天开奖的彩票类型，调用对应脚本获取最新数据

开奖时间（北京时间）：
- 双色球：周二、周四、周日
- 大乐透：周一、周三、周六
- 周五：无开奖

在GitHub Actions执行时，默认是UTC时区，需要转换为北京时间(UTC+8)
"""

import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

BEIJING_TZ = timezone(timedelta(hours=8))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SSQ_SCRIPT = os.path.join(SCRIPT_DIR, "ssq_fetcher.py")
DALETOU_SCRIPT = os.path.join(SCRIPT_DIR, "dlt_fetcher.py")

LOTTERY_BY_WEEKDAY = {
    0: "daletou",   # 周一 - 大乐透
    1: "ssq",       # 周二 - 双色球
    2: "daletou",   # 周三 - 大乐透
    3: "ssq",       # 周四 - 双色球
    4: None,        # 周五 - 无开奖
    5: "daletou",   # 周六 - 大乐透
    6: "ssq",       # 周日 - 双色球
}


def get_beijing_time():
    return datetime.now(BEIJING_TZ)


def get_lottery_type():
    beijing_time = get_beijing_time()
    weekday = beijing_time.weekday()
    lottery_type = LOTTERY_BY_WEEKDAY.get(weekday)

    print(f"=" * 60)
    print(f"当前北京时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"今天是: 星期{['一','二','三','四','五','六','日'][weekday]}")
    print(f"=" * 60)

    return lottery_type, beijing_time


def run_script(script_path, args):
    """运行脚本，args 为参数列表，如 ['--recent', '1']"""
    cmd = [sys.executable, script_path] + args
    print(f"\n正在运行: {' '.join(cmd)}")
    print("-" * 60)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        if result.returncode == 0:
            print(f"\n✓ {script_path} 执行成功")
            return True
        else:
            print(f"\n✗ {script_path} 执行失败，退出码: {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        print(f"\n✗ {script_path} 执行超时（10分钟）")
        return False
    except Exception as e:
        print(f"\n✗ {script_path} 执行异常: {e}")
        return False


def fetch_latest(lottery_type, mode="update"):
    """获取指定彩票类型的最新数据并更新到文件

    mode:
    - "update": 仅获取最新一期并增量更新（默认）
    - "history": 重新拉取全量历史数据并覆盖文件
    """
    if lottery_type == "ssq":
        script = SSQ_SCRIPT
    elif lottery_type == "daletou":
        script = DALETOU_SCRIPT
    else:
        return False

    if mode == "history":
        # 全量刷新，覆盖 JSON 和 CSV
        return run_script(script, ["--history"])
    # 默认增量更新最新一期
    return run_script(script, ["--update"])


def main():
    # 支持通过环境变量传参（由 GitHub Actions workflow_dispatch 注入）
    # LOTTERY: both(默认) / ssq / daletou
    # FETCH_MODE: update(默认) / history
    lottery = os.environ.get("LOTTERY", "both").strip().lower()
    mode = os.environ.get("FETCH_MODE", "update").strip().lower()

    lottery_type, beijing_time = get_lottery_type()

    if lottery_type == "ssq":
        print("\n今天开奖: 双色球")
    elif lottery_type == "daletou":
        print("\n今天开奖: 大乐透")
    else:
        print("\n今天没有开奖任务（周五）")

    print(f"\n运行参数: LOTTERY={lottery} | FETCH_MODE={mode}")

    # 确定要获取的彩种
    if lottery == "ssq":
        targets = ["ssq"]
    elif lottery == "daletou":
        targets = ["daletou"]
    else:
        # both 或其它值：同时获取双色球和大乐透
        # 由于 GitHub Actions 的 schedule 可能延迟（甚至跨天），
        # 为保证数据完整性，每次都同时获取两种的最新数据。
        # update_latest 内部会按期号去重，已存在的不会重复写入。
        targets = ["ssq", "daletou"]

    print(f"将获取: {', '.join(targets)}\n")
    for t in targets:
        fetch_latest(t, mode=mode)

    print("\n" + "=" * 60)
    print("所有任务完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
