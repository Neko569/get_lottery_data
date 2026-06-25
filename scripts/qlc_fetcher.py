#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取福彩七乐彩开奖数据
数据源: https://kaijiang.500.com/static/info/kaijiang/xml/qlc/list.xml

七乐彩：前区7个数字（01-30），特别号1个，每周一、三、五开奖

用法:
    python qlc_fetcher.py --latest    # 获取最新一期
    python qlc_fetcher.py --history   # 获取全部历史数据
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

API_URL = "https://kaijiang.500.com/static/info/kaijiang/xml/qlc/list.xml"
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
    """解析单条 XML row，七乐彩7个前区号码 + 1个特别号

    XML 格式：<row expect="26071" opencode="10,12,14,20,25,26,30|21" opentime="2026-06-24 21:15:00"/>
    opencode 用 | 分隔前区(7个)和特别号(1个)
    """
    expect = row.get("expect", "")
    opencode = row.get("opencode", "")
    opentime = row.get("opentime", "")

    if "|" in opencode:
        front_str, back_str = opencode.split("|", 1)
    else:
        front_str, back_str = opencode, ""
    front_numbers = [x.strip() for x in front_str.split(",") if x.strip()]
    back_numbers = [x.strip() for x in back_str.split(",") if x.strip()]

    return {
        "term": expect,
        "draw_time": opentime,
        "draw_result": opencode,
        "front_numbers": front_numbers,
        "back_numbers": back_numbers,
    }


def get_latest():
    rows = _fetch_xml()
    if rows:
        return parse_record(rows[0])
    return None


def update_latest():
    filepath = os.path.join(DATA_DIR, "qlc_history.json")
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
    print("正在拉取七乐彩全量历史数据...")
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


def save_to_file(records, filename="qlc_history.json"):
    filepath = os.path.join(DATA_DIR, filename)
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "kaijiang.500.com",
        "game": "七乐彩",
        "game_no": "qlc",
        "total": len(records),
        "items": records
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"数据已保存到 {filepath}，共 {len(records)} 条记录")


def save_to_csv(records, filename="qlc_history.csv"):
    if not records:
        return
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["term", "draw_time", "draw_result", "front_numbers", "back_numbers"])
        writer.writeheader()
        writer.writerows(records)
    print(f"数据已保存到 {filepath}，共 {len(records)} 条记录")


def main():
    parser = argparse.ArgumentParser(description="获取七乐彩开奖数据")
    parser.add_argument("--latest", action="store_true", help="获取最新一期数据")
    parser.add_argument("--update", action="store_true", help="获取最新一期并增量更新到JSON文件")
    parser.add_argument("--history", action="store_true", help="获取全部历史数据")
    parser.add_argument("--recent", type=int, metavar="MONTHS", help="获取最近MONTHS个月的数据")
    parser.add_argument("--dry-run", action="store_true", help="仅输出不写入文件")
    args = parser.parse_args()

    print("=" * 50)
    if args.latest:
        print("获取七乐彩最新一期数据")
        record = get_latest()
        if record:
            print(json.dumps(record, ensure_ascii=False, indent=2))
        else:
            print("未能获取到最新数据")
    elif args.update:
        print("获取七乐彩最新一期并增量更新")
        update_latest()
    else:
        months = args.recent if args.recent else None
        if months:
            print(f"获取七乐彩最近 {months} 个月数据")
        else:
            print("获取七乐彩全部历史数据")
        print("=" * 50)
        records = get_all_data(months=months)
        if records:
            if args.dry_run:
                print(json.dumps(records, ensure_ascii=False, indent=2))
            else:
                save_to_file(records, "qlc_history.json")
                save_to_csv(records, "qlc_history.csv")
            print(f"\n共 {len(records)} 条记录")
        else:
            print("未能获取到数据")
    print("=" * 50)


if __name__ == "__main__":
    main()
