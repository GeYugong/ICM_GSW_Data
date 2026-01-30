import pandas as pd
import requests
import os
import time
import random
import urllib3
import re

# --- 配置 ---
SEASONS = list(range(2021, 2026))
OUTPUT_FILE = "data/gsw_ticket_revenue.csv"
TEAM_CODE = "GSW"

# --- 代理设置 (端口 7897) ---
PROXIES = {
    "http": "http://127.0.0.1:7897",
    "https": "http://127.0.0.1:7897",
}
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 票价估算模型 (Ticket Price Estimator) ---
# 由于没有网站公开每日门票收入，我们建立一个简单的估算模型
# 基础票价(Base) * (1 + 通胀率) * 球队表现系数
BASE_TICKET_PRICE = 280  # 勇士队平均票价极高 (美元)

def get_ticket_data_bref():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    all_data = []

    print(f"🎫 启动 B-Ref 门票数据爬虫 (纯净模式: 无保底数据)...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for season in SEASONS:
        # Basketball-Reference 赛季主页
        url = f"https://www.basketball-reference.com/teams/{TEAM_CODE}/{season}.html"
        print(f"\n   ⏳ [正在抓取] {season} 赛季: {url}")
        
        try:
            # 发送请求 (死磕模式: 必须成功，否则该年为空)
            response = requests.get(url, headers=headers, proxies=PROXIES, timeout=20, verify=False)
            
            if response.status_code == 200:
                # B-Ref 的 Misc 表格通常包含上座率
                # 我们寻找 id="team_misc" 的表格
                
                # 技巧: 有些表格被注释隐藏了，先清洗
                html = response.text.replace('', '')
                
                # 读取所有表格
                dfs = pd.read_html(html)
                
                found_data = False
                
                for df in dfs:
                    # 将列名转为字符串处理
                    df.columns = [str(c) for c in df.columns]
                    
                    # 寻找包含 'Attendance' 的表格
                    if 'Attendance' in df.columns:
                        # 通常这个表只有两行 (Team, League Avg) 或一行
                        # 我们取第一行 (Team)
                        
                        # 提取总上座人数
                        att_val = df.iloc[0]['Attendance']
                        
                        # 处理数据清洗 (有些年份可能是 NaN, 如2021)
                        if pd.isna(att_val):
                            home_total = 0
                        else:
                            home_total = int(att_val)
                            
                        # 场均上座 (Attendance/G)
                        if 'Attend./G' in df.columns:
                            avg_val = df.iloc[0]['Attend./G']
                            home_avg = int(avg_val) if not pd.isna(avg_val) else 0
                        else:
                            # 如果没有场均列，手动计算 (假设41场主场)
                            home_avg = int(home_total / 41) if home_total > 0 else 0
                        
                        # --- 收入模型计算 ---
                        # 2021年特殊处理 (疫情空场)
                        if season == 2021:
                            est_price = 0
                        else:
                            # 票价每年涨 5% (通胀)
                            inflation_factor = 1.05 ** (season - 2022)
                            # 表现系数: 夺冠年(2022) 票价更贵
                            perf_factor = 1.2 if season == 2022 else 1.0
                            
                            est_price = BASE_TICKET_PRICE * inflation_factor * perf_factor
                        
                        # 计算总收入 (百万美元)
                        # Revenue = (Total_Attendance * Price) / 1,000,000
                        revenue_m = (home_total * est_price) / 1_000_000
                        
                        # 记录数据
                        row = {
                            "Season": season,
                            "Home_Total_Attendance": home_total,
                            "Home_Avg_Attendance": home_avg,
                            "Est_Avg_Ticket_Price": round(est_price, 2),
                            "Gate_Revenue_M": round(revenue_m, 2),
                            "Source": "Basketball-Reference Scraped"
                        }
                        all_data.append(row)
                        print(f"      ✅ 抓取成功: 总人数 {home_total:,} | 估算收入 ${revenue_m:.1f}M")
                        found_data = True
                        break # 找到就跳出表格循环
                
                if not found_data:
                    print(f"      ⚠️ 页面下载成功，但未找到 'Attendance' 列。")
                    # 这里不再使用保底数据，直接跳过
            
            else:
                print(f"      ❌ HTTP {response.status_code} - 抓取失败")

        except Exception as e:
            print(f"      ❌ 严重错误: {e}")
        
        # 礼貌性延迟，防止 B-Ref 封 IP
        time.sleep(random.uniform(3, 5))

    # --- 保存结果 ---
    if all_data:
        df_result = pd.DataFrame(all_data)
        df_result.to_csv(OUTPUT_FILE, index=False)
        print(f"\n💾 数据已保存至: {OUTPUT_FILE}")
        print(df_result)
    else:
        print("\n⚠️ 警告: 未获取到任何数据 (由于禁用了保底数据，请检查网络连接)")

if __name__ == "__main__":
    get_ticket_data_bref()