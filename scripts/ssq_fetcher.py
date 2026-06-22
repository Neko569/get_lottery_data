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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "../data")
os.makedirs(DATA_DIR, exist_ok=True)

API_URL = "https://gdwechat.daguoxiaoxian.com/api/lottery-results/list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "Referer": "https://gdwechat.daguoxiaoxian.com/frontend/#/pages/historySSQ/index?v=2"
}

LIMIT = 30


def fetch_page(page):
    params = {
        "type": 1,
        "limit": LIMIT,
        "page": page
    }
    try:
        response = requests.get(API_URL, headers=HEADERS, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"请求第{page}页失败: {e}")
        return None


def parse_record(record):
    return {
        "期号": record.get("issue_number", ""),
        "开奖日期": record.get("lottery_date", ""),
        "开奖号码": record.get("win_code", "")
    }


def get_latest():
    data = fetch_page(1)
    if data is not None and data.get("code") == 1:
        records = data.get("data", {}).get("list", [])
        if records:
            return parse_record(records[0])
    return None


def get_all_data():
    all_records = []
    page = 1
    max_records = 2000
    max_pages = (max_records // LIMIT) + 2

    while page <= max_pages:
        print(f"正在获取第 {page} 页...")
        data = fetch_page(page)

        if data is None or data.get("code") != 1:
            print(f"API返回异常: {data}")
            break

        records = data.get("data", {}).get("list", [])
        if not records:
            print("没有更多数据了")
            break

        for record in records:
            parsed = parse_record(record)
            all_records.append(parsed)

        if records:
            latest_date = records[0].get("lottery_date", "")
            if latest_date:
                try:
                    record_date = datetime.strptime(latest_date, "%Y-%m-%d")
                    ten_years_ago = datetime.now() - timedelta(days=365 * 10)
                    if record_date < ten_years_ago:
                        print("已超过10年数据，停止获取")
                        break
                except:
                    pass

        if len(records) < LIMIT:
            break

        page += 1
        time.sleep(0.5)

    return sorted(all_records, key=lambda x: (x.get("开奖日期") or "", x.get("期号") or ""), reverse=True)


def save_to_file(records, filename="ssq_history.json"):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"数据已保存到 {filepath}，共 {len(records)} 条记录")


def save_to_csv(records, filename="ssq_history.csv"):
    if not records:
        return
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["期号", "开奖日期", "开奖号码"])
        writer.writeheader()
        writer.writerows(records)
    print(f"数据已保存到 {filepath}，共 {len(records)} 条记录")


def main():
    parser = argparse.ArgumentParser(description="获取双色球开奖数据")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--latest", action="store_true", help="获取最新一期数据")
    group.add_argument("--history", action="store_true", help="获取近10年历史数据")
    args = parser.parse_args()

    print("=" * 50)
    if args.latest:
        print("获取双色球最新一期数据")
        record = get_latest()
        if record:
            print(json.dumps(record, ensure_ascii=False, indent=2))
        else:
            print("未能获取到最新数据")
    else:
        print("获取双色球近10年历史数据")
        print("=" * 50)
        records = get_all_data()
        if records:
            save_to_file(records, "ssq_history.json")
            save_to_csv(records, "ssq_history.csv")
            print("\n前5条数据预览:")
            for r in records[:5]:
                print(r)
        else:
            print("未能获取到数据")
    print("=" * 50)


if __name__ == "__main__":
    main()
