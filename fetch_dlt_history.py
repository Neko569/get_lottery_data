import requests
import json
import csv
import time
import sys
from datetime import datetime, timedelta

BASE_URL = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "Referer": "https://m.lottery.gov.cn/mkjdlt/",
    "Accept-Encoding": "gzip, deflate, br",
}

GAME_NO = "85"
PAGE_SIZE = 30
YEARS = 10


def fetch_page(page_no):
    params = {
        "gameNo": GAME_NO,
        "provinceId": "0",
        "pageSize": PAGE_SIZE,
        "isVerify": "1",
        "termLimits": "0",
        "pageNo": page_no,
    }
    response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def parse_record(item):
    result = item.get("lotteryDrawResult", "")
    numbers = result.split() if result else []

    front = numbers[:5]
    back = numbers[5:7]

    prize_levels = item.get("prizeLevelList", []) or []
    prize_info = {}
    for p in prize_levels:
        level_name = p.get("prizeLevel", "")
        stake_count = p.get("stakeCount", "")
        stake_amount = p.get("stakeAmount", "")
        total_prize = p.get("totalPrizeamount", "")
        prize_info[level_name] = {
            "stakeCount": stake_count,
            "stakeAmount": stake_amount,
            "totalPrizeAmount": total_prize,
        }

    return {
        "期号": item.get("lotteryDrawNum", ""),
        "开奖日期": item.get("lotteryDrawTime", ""),
        "前区号码": " ".join(front),
        "后区号码": " ".join(back),
        "开奖号码": result,
        "奖池金额(元)": item.get("poolBalance", ""),
        "开奖后奖池(元)": item.get("poolBalanceAfterdraw", ""),
        "销售金额(元)": item.get("totalSaleAmount", ""),
        "一等奖注数": prize_info.get("一等奖", {}).get("stakeCount", ""),
        "一等奖单注奖金(元)": prize_info.get("一等奖", {}).get("stakeAmount", ""),
        "二等奖注数": prize_info.get("二等奖", {}).get("stakeCount", ""),
        "二等奖单注奖金(元)": prize_info.get("二等奖", {}).get("stakeAmount", ""),
    }


def fetch_all_years_data(years=YEARS):
    cutoff_date = datetime.now() - timedelta(days=years * 365)
    print(f"截止日期: {cutoff_date.strftime('%Y-%m-%d')}")

    all_records = []
    page_no = 1
    reached_cutoff = False

    first_resp = fetch_page(1)
    if not first_resp.get("success"):
        print(f"请求失败: {first_resp.get('message')}")
        sys.exit(1)

    value = first_resp.get("value", {})
    total_pages = value.get("pages", 1)
    total_count = value.get("total", 0)
    print(f"总期数: {total_count}, 总页数: {total_pages}")

    while page_no <= total_pages and not reached_cutoff:
        print(f"正在获取第 {page_no}/{total_pages} 页...", end=" ")
        sys.stdout.flush()

        if page_no == 1:
            resp = first_resp
        else:
            resp = fetch_page(page_no)

        page_list = resp.get("value", {}).get("list", [])
        page_count = 0

        for item in page_list:
            draw_time_str = item.get("lotteryDrawTime", "")
            try:
                draw_date = datetime.strptime(draw_time_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                continue

            if draw_date < cutoff_date:
                reached_cutoff = True
                break

            all_records.append(parse_record(item))
            page_count += 1

        print(f"获取 {page_count} 条")
        page_no += 1
        time.sleep(0.3)

    print(f"\n共获取 {len(all_records)} 条开奖记录")
    return all_records


def save_csv(records, filepath):
    if not records:
        print("无数据可保存")
        return

    fieldnames = list(records[0].keys())
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"已保存 CSV: {filepath}")


def save_json(records, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"已保存 JSON: {filepath}")


def main():
    print(f"开始获取过去 {YEARS} 年大乐透开奖数据...")
    print("-" * 50)

    records = fetch_all_years_data(YEARS)

    if records:
        latest = records[0]
        earliest = records[-1]
        print(f"\n数据范围: {earliest['开奖日期']} ({earliest['期号']}) 至 {latest['开奖日期']} ({latest['期号']})")

        timestamp = datetime.now().strftime("%Y%m%d")
        csv_path = f"dlt_history_{YEARS}years_{timestamp}.csv"
        json_path = f"dlt_history_{YEARS}years_{timestamp}.json"

        save_csv(records, csv_path)
        save_json(records, json_path)

        print("\n完成!")
    else:
        print("未获取到任何数据")


if __name__ == "__main__":
    main()
