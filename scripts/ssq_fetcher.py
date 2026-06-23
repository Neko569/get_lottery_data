#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取福彩双色球开奖数据
API来源: https://gdwechat.daguoxiaoxian.com/api/lottery-results/list

用法:
    python ssq_fetcher.py --latest    # 获取最新一期
    python ssq_fetcher.py --history   # 获取近10年历史数据
"""

import argparse
import csv
import json
import os
import time
from datetime import datetime, timedelta

import requests

# 获取脚本所在目录，并设置数据存储目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "../data")
os.makedirs(DATA_DIR, exist_ok=True)

# API配置
API_URL = "https://gdwechat.daguoxiaoxian.com/api/lottery-results/list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "Referer": "https://gdwechat.daguoxiaoxian.com/frontend/#/pages/historySSQ/index?v=2"
}

LIMIT = 30  # 每页返回的记录数


def fetch_page(page, retries=3):
    """获取指定页码的数据，失败自动重试"""
    params = {
        "type": 1,
        "limit": LIMIT,
        "page": page
    }
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(API_URL, headers=HEADERS, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            last_err = e
            print(f"请求第{page}页失败（第{attempt}/{retries}次）: {e}")
            if attempt < retries:
                # 退避延时，避免连续握手失败
                time.sleep(3 * attempt)

    print(f"请求第{page}页已重试{retries}次仍失败: {last_err}")
    return None


def parse_record(record):
    """解析单条开奖记录，提取并重组所需字段"""
    win_code = record.get("win_code", "")
    # 支持逗号和空格分隔
    parts = [p.strip() for p in win_code.replace(",", " ").split()] if win_code else []
    # 分离前区(6个红球)和后区(1个蓝球)
    front_numbers = parts[:6]
    back_numbers = parts[6:7]
    return {
        "term": record.get("issue_number", ""),
        "draw_time": record.get("lottery_date", ""),
        "draw_result": " ".join(parts),
        "front_numbers": front_numbers,
        "back_numbers": back_numbers
    }


def get_latest():
    """获取最新一期的开奖数据"""
    data = fetch_page(1)
    if data is not None and data.get("code") == 1:
        records = data.get("data", {}).get("list", [])
        if records:
            return parse_record(records[0])
    return None


def update_latest():
    """获取最新一期并增量更新到现有JSON文件（若期号已存在则跳过）"""
    filepath = os.path.join(DATA_DIR, "ssq_history.json")
    latest = get_latest()
    if not latest:
        print("未能获取到最新数据")
        return False

    # 读取现有数据
    existing = {"items": []}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            existing = json.load(f)

    items = existing.get("items", [])
    # 检查最新期号是否已存在
    if any(str(it.get("term")) == str(latest.get("term")) for it in items):
        print(f"最新一期（期号 {latest.get('term')}）已存在，无需更新")
        return True

    # 插入到列表头部
    items.insert(0, latest)
    existing["items"] = items
    existing["total"] = len(items)
    existing["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"已更新 {filepath}，新增期号 {latest.get('term')}，共 {len(items)} 条记录")
    # 同步重写 CSV，保持 JSON 与 CSV 数据一致
    save_to_csv(items)
    return True


def get_all_data(months=None):
    """
    获取历史开奖数据
    通过分页遍历获取数据，直到达到指定月份前的记录或达到最大页数
    months: 保留最近几个月的数据，None表示保留所有数据（最多10年）
    """
    all_records = []
    page = 1
    max_records = 2000
    max_pages = (max_records // LIMIT) + 2

    cutoff_date = None
    if months:
        cutoff_date = datetime.now() - timedelta(days=30 * months)
        print(f"仅保留最近 {months} 个月的数据")

    while page <= max_pages:
        print(f"正在获取第 {page} 页...")
        data = fetch_page(page)

        # 检查API响应状态
        if data is None or data.get("code") != 1:
            print(f"API返回异常: {data}")
            break

        records = data.get("data", {}).get("list", [])
        if not records:
            print("没有更多数据了")
            break

        # 解析并收集每条记录
        for record in records:
            parsed = parse_record(record)
            all_records.append(parsed)

        # 检查是否已达到截止日期
        if cutoff_date and records:
            latest_date = records[0].get("lottery_date", "")
            if latest_date:
                try:
                    record_date = datetime.strptime(latest_date, "%Y-%m-%d")
                    if record_date < cutoff_date:
                        print(f"已超过 {months} 个月数据，停止获取")
                        break
                except:
                    pass

        # 数据不足一页说明已到末尾
        if len(records) < LIMIT:
            break

        page += 1
        # 请求间隔延时
        time.sleep(0.5)

    # 按日期和期号倒序排序，最新数据排在前面
    return sorted(all_records, key=lambda x: (x.get("draw_time") or "", x.get("term") or ""), reverse=True)


def save_to_file(records, filename="ssq_history.json"):
    """保存数据到JSON文件"""
    filepath = os.path.join(DATA_DIR, filename)
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "daguoxiaoxian.com",
        "game": "双色球",
        "game_no": "ssq",
        "total": len(records),
        "items": records
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"数据已保存到 {filepath}，共 {len(records)} 条记录")


def save_to_csv(records, filename="ssq_history.csv"):
    """保存数据到CSV文件"""
    if not records:
        return
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["term", "draw_time", "draw_result", "front_numbers", "back_numbers"])
        writer.writeheader()
        writer.writerows(records)
    print(f"数据已保存到 {filepath}，共 {len(records)} 条记录")


def main():
    """主函数，处理命令行参数并执行相应操作"""
    parser = argparse.ArgumentParser(description="获取双色球开奖数据")
    parser.add_argument("--latest", action="store_true", help="获取最新一期数据")
    parser.add_argument("--update", action="store_true", help="获取最新一期并增量更新到JSON文件")
    parser.add_argument("--history", action="store_true", help="获取近10年历史数据")
    parser.add_argument("--recent", type=int, metavar="MONTHS", help="获取最近MONTHS个月的数据")
    parser.add_argument("--dry-run", action="store_true", help="仅输出不写入文件")
    args = parser.parse_args()

    print("=" * 50)
    if args.latest:
        print("获取双色球最新一期数据")
        record = get_latest()
        if record:
            print(json.dumps(record, ensure_ascii=False, indent=2))
        else:
            print("未能获取到最新数据")
    elif args.update:
        print("获取双色球最新一期并增量更新")
        update_latest()
    else:
        months = args.recent if args.recent else None
        if months:
            print(f"获取双色球最近 {months} 个月数据")
        else:
            print("获取双色球近10年历史数据")
        print("=" * 50)
        records = get_all_data(months=months)
        if records:
            if args.dry_run:
                print(json.dumps(records, ensure_ascii=False, indent=2))
            else:
                save_to_file(records, "ssq_history.json")
                save_to_csv(records, "ssq_history.csv")
            print(f"\n共 {len(records)} 条记录")
        else:
            print("未能获取到数据")
    print("=" * 50)


if __name__ == "__main__":
    main()
