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

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

# 脚本路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SSQ_SCRIPT = os.path.join(SCRIPT_DIR, "ssq_fetcher.py")
DALETOU_SCRIPT = os.path.join(SCRIPT_DIR, "daletou_fetch.py")

# 星期对应的开奖类型 (Python: Monday=0, Sunday=6)
# 双色球：周二、周四、周日
# 大乐透：周一、周三、周六
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
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)

def get_lottery_type():
    """根据北京时间获取当天开奖的彩票类型"""
    beijing_time = get_beijing_time()
    weekday = beijing_time.weekday()  # Python: Monday=0, Sunday=6

    lottery_type = LOTTERY_BY_WEEKDAY.get(weekday)

    print(f"=" * 60)
    print(f"当前北京时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"今天是: 星期{['一','二','三','四','五','六','日'][weekday]}")
    print(f"=" * 60)

    return lottery_type, beijing_time

def run_script(script_path):
    """运行指定的脚本"""
    print(f"\n正在运行: {script_path}")
    print("-" * 60)

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
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
        print(f"\n✗ {script_path} 执行超时（5分钟）")
        return False
    except Exception as e:
        print(f"\n✗ {script_path} 执行异常: {e}")
        return False

def main():
    lottery_type, beijing_time = get_lottery_type()

    if lottery_type is None:
        print("\n今天没有开奖任务（周五）")
        # 仍然运行两个脚本获取最新数据
        print("\n为确保数据完整性，仍将获取最新数据...")
        run_script(SSQ_SCRIPT)
        run_script(DALETOU_SCRIPT)
    elif lottery_type == "ssq":
        print("\n今天开奖: 双色球")
        run_script(SSQ_SCRIPT)
    elif lottery_type == "daletou":
        print("\n今天开奖: 大乐透")
        run_script(DALETOU_SCRIPT)

    print("\n" + "=" * 60)
    print("所有任务完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
