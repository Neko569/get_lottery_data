#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彩票开奖调度脚本
每天获取所有彩种的最新开奖数据（增量更新）

逻辑说明：
- 每天触发时，调用所有彩种的 fetcher 执行 --update（增量更新最新一期）
- 非开奖日的彩种，由于最新期号已存在，--update 会自动跳过，不会重复写入
- 开奖日的彩种，能获取到最新一期并追加到数据文件

在GitHub Actions执行时，默认是UTC时区，需要转换为北京时间(UTC+8)
"""

import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

BEIJING_TZ = timezone(timedelta(hours=8))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 各彩种 fetcher 脚本路径
SCRIPTS = {
    "ssq":   os.path.join(SCRIPT_DIR, "ssq_fetcher.py"),
    "dlt":   os.path.join(SCRIPT_DIR, "dlt_fetcher.py"),
    "qxc":   os.path.join(SCRIPT_DIR, "qxc_fetcher.py"),
    "pls":   os.path.join(SCRIPT_DIR, "pls_fetcher.py"),
    "plw":   os.path.join(SCRIPT_DIR, "plw_fetcher.py"),
    "fc3d":  os.path.join(SCRIPT_DIR, "fc3d_fetcher.py"),
    "qlc":   os.path.join(SCRIPT_DIR, "qlc_fetcher.py"),
    "kl8":   os.path.join(SCRIPT_DIR, "kl8_fetcher.py"),
}


def get_beijing_time():
    return datetime.now(BEIJING_TZ)


def get_lottery_types():
    """返回所有需要获取的彩种列表

    每天触发时，获取所有彩种的最新数据（增量更新）。
    各彩种在非开奖日调用 --update 时，由于最新期号已存在，会自动跳过，不会重复写入。
    """
    beijing_time = get_beijing_time()
    weekday = beijing_time.weekday()

    all_types = list(SCRIPTS.keys())

    print(f"=" * 60)
    print(f"当前北京时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"今天是: 星期{['一','二','三','四','五','六','日'][weekday]}")
    print(f"=" * 60)

    return all_types, beijing_time


def run_script(script_path, args):
    """运行脚本，args 为参数列表，如 ['--update']"""
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
    script = SCRIPTS.get(lottery_type)
    if not script:
        return False

    if mode == "history":
        return run_script(script, ["--history"])
    return run_script(script, ["--update"])


def main():
    # 支持通过环境变量传参（由 GitHub Actions workflow_dispatch 注入）
    # LOTTERY: all(默认) / ssq / dlt / qxc / pls / plw / fc3d / qlc / kl8
    # FETCH_MODE: update(默认) / history
    lottery = os.environ.get("LOTTERY", "all").strip().lower()
    mode = os.environ.get("FETCH_MODE", "update").strip().lower()

    types, beijing_time = get_lottery_types()

    lottery_names = {
        "ssq": "双色球", "dlt": "大乐透", "qxc": "七星彩",
        "pls": "排列三", "plw": "排列五", "fc3d": "福彩3D",
        "qlc": "七乐彩", "kl8": "快乐八",
    }
    today_names = [lottery_names.get(t, t) for t in types]
    print(f"\n本次将获取: {', '.join(today_names)}")

    print(f"\n运行参数: LOTTERY={lottery} | FETCH_MODE={mode}")

    # 确定要获取的彩种
    if lottery == "all":
        targets = types
    elif lottery in SCRIPTS:
        targets = [lottery]
    else:
        # 未知参数，默认获取所有彩种
        targets = types

    print(f"将获取: {', '.join(targets)}\n")
    for t in targets:
        fetch_latest(t, mode=mode)

    print("\n" + "=" * 60)
    print("所有任务完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
