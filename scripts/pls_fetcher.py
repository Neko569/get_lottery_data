#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取体彩排列三开奖数据
数据源: https://kaijiang.500.com/static/info/kaijiang/xml/pls/list.xml

排列三：3个数字（0-9），每日开奖

用法:
    python pls_fetcher.py --latest    # 获取最新一期
    python pls_fetcher.py --history   # 获取全部历史数据
"""

import argparse
import csv
import json
import os
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "../data")
os.makedirs(DATA_DIR, exist_ok=True)

API_URL = "https://kaijiang.500.com/static/info/kaijiang/xml/pls/list.xml"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def _fetch_xml(timeout=30, retries=3):
    last_err = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(API_URL, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
            root = ET.fromstring(body)
            rows = root.findall("row")
            if rows:
                return rows
            last_err = "XML 中无 row 记录"
        except Exception as e:
            last_err = e
            print(f"请求失败（第{attempt}/{retries}次）: {e}")
            if attempt < retries:
                time.sleep(3 * attempt)
    print(f"已重试{retries}次仍失败: {last_err}")
    return None


def parse_record(row):
    """解析单条 XML row，排列三3个数字（0-9）

    XML 格式：<row expect="26166" opencode="2,2,9" opentime="2026-06-25 21:25:00"/>
    """
    expect = row.get("expect", "")
    opencode = row.get("opencode", "")
    opentime = row.get("opentime", "")

    numbers = [x.strip() for x in opencode.split(",") if x.strip()]

    return {
        "term": expect,
        "draw_time": opentime,
        "draw_result": opencode,
        "numbers": numbers,
    }


def get_latest():
    rows = _fetch_xml()
    if rows:
        return parse_record(rows[0])
    return None


def update_latest():
    filepath = os.path.join(DATA_DIR, "pls_history.json")
    latest = get_latest()
    if not latest:
        print("未能获取到最新数据")
        return False

    existing = {"items": []}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            existing = json.load(f)

    items = existing.get("items", [])
    if any(str(it.get("term")) == str(latest.get("term")) for it in items):
        print(f"最新一期（期号 {latest.get('term')}）已存在，无需更新")
        return True

    items.insert(0, latest)
    existing["items"] = items
    existing["total"] = len(items)
    existing["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"已更新 {filepath}，新增期号 {latest.get('term')}，共 {len(items)} 条记录")
    save_to_csv(items)
    return True


def get_all_data(months=None):
    print("正在拉取排列三全量历史数据...")
    rows = _fetch_xml()
    if not rows:
        return []

    cutoff_date = None
    if months:
        cutoff_date = datetime.now() - timedelta(days=30 * months)
        print(f"仅保留最近 {months} 个月的数据")

    all_records = []
    for row in rows:
        parsed = parse_record(row)
        if cutoff_date:
            draw_time = parsed.get("draw_time", "")
            if draw_time:
                try:
                    record_date = datetime.strptime(draw_time[:10], "%Y-%m-%d")
                    if record_date < cutoff_date:
                        continue
                except Exception:
                    pass
        all_records.append(parsed)

    print(f"共获取 {len(all_records)} 条记录")
    return all_records


def save_to_file(records, filename="pls_history.json"):
    filepath = os.path.join(DATA_DIR, filename)
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "kaijiang.500.com",
        "game": "排列三",
        "game_no": "pls",
        "total": len(records),
        "items": records
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"数据已保存到 {filepath}，共 {len(records)} 条记录")


def save_to_csv(records, filename="pls_history.csv"):
    if not records:
        return
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["term", "draw_time", "draw_result", "numbers"])
        writer.writeheader()
        writer.writerows(records)
    print(f"数据已保存到 {filepath}，共 {len(records)} 条记录")


def main():
    parser = argparse.ArgumentParser(description="获取排列三开奖数据")
    parser.add_argument("--latest", action="store_true", help="获取最新一期数据")
    parser.add_argument("--update", action="store_true", help="获取最新一期并增量更新到JSON文件")
    parser.add_argument("--history", action="store_true", help="获取全部历史数据")
    parser.add_argument("--recent", type=int, metavar="MONTHS", help="获取最近MONTHS个月的数据")
    parser.add_argument("--dry-run", action="store_true", help="仅输出不写入文件")
    args = parser.parse_args()

    print("=" * 50)
    if args.latest:
        print("获取排列三最新一期数据")
        record = get_latest()
        if record:
            print(json.dumps(record, ensure_ascii=False, indent=2))
        else:
            print("未能获取到最新数据")
    elif args.update:
        print("获取排列三最新一期并增量更新")
        update_latest()
    else:
        months = args.recent if args.recent else None
        if months:
            print(f"获取排列三最近 {months} 个月数据")
        else:
            print("获取排列三全部历史数据")
        print("=" * 50)
        records = get_all_data(months=months)
        if records:
            if args.dry_run:
                print(json.dumps(records, ensure_ascii=False, indent=2))
            else:
                save_to_file(records, "pls_history.json")
                save_to_csv(records, "pls_history.csv")
            print(f"\n共 {len(records)} 条记录")
        else:
            print("未能获取到数据")
    print("=" * 50)


if __name__ == "__main__":
    main()
