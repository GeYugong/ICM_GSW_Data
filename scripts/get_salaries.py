import pandas as pd
import requests
import os
import time
import random
import urllib3

# --- 配置 ---
# 目标：抓取 2021-2025 赛季 (对应 Spotrac year 参数 2020-2024)
SEASONS = list(range(2021, 2026)) 
TEAM_SLUG = "golden-state-warriors"
OUTPUT_FILE = "data/gsw_salaries_5years.csv"

# --- 代理设置 (端口 7897) ---
PROXIES = {
    "http": "http://127.0.0.1:7897",
    "https": "http://127.0.0.1:7897",
}
# 清除环境变量干扰
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

# 禁用 SSL 警告 (因为我们要用 verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 浏览器伪装池 ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
]

def get_salaries_hardcore():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    all_data = []

    print(f"💰 开始抓取薪资数据 (死磕模式：不使用保底，直到成功)...")

    for season in SEASONS:
        # Spotrac URL 逻辑：
        # 2021 赛季 -> year/2020
        # 2025 赛季 -> year/2024
        year_param = season - 1
        url = f"https://www.spotrac.com/nba/{TEAM_SLUG}/cap/_/year/{year_param}"
        
        print(f"\n   🎯 目标: {season} 赛季 ({year_param}-{season}) -> {url}")
        
        success = False
        attempt = 0
        max_retries = 10  # 最大尝试次数，防止死循环
        
        while not success and attempt < max_retries:
            attempt += 1
            # 每次请求随机切换 User-Agent
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.spotrac.com/nba/cap/",
                "Connection": "keep-alive" # 保持连接
            }

            try:
                # 关键修改：verify=False 忽略 SSL 证书验证，解决 SSLEOFError
                response = requests.get(url, headers=headers, proxies=PROXIES, timeout=20, verify=False)
                
                if response.status_code == 200:
                    dfs = pd.read_html(response.text)
                    
                    found_salary = False
                    # 遍历所有表格寻找薪资数据
                    for df in dfs:
                        # 清洗列名
                        df.columns = [str(c).replace(' ', '') for c in df.columns] # 去除列名空格
                        
                        # 查找包含 CapHit 的列
                        hit_col = next((c for c in df.columns if 'CapHit' in c), None)
                        
                        if hit_col:
                            # 清洗数值
                            if df[hit_col].dtype == object:
                                clean_series = df[hit_col].replace('[\$,]', '', regex=True)
                                clean_series = pd.to_numeric(clean_series, errors='coerce').fillna(0)
                            else:
                                clean_series = df[hit_col]
                            
                            # 逻辑判断：如果是有效的薪资表，总和应该很大
                            total_cap = clean_series.sum()
                            
                            # 勇士队薪资通常 > 1亿 (100,000,000)
                            if total_cap > 100000000:
                                all_data.append({
                                    "Season": season,
                                    "Total_Salary_Expense": total_cap,
                                    "Source": "Spotrac_Scraped"
                                })
                                print(f"      ✅ [第{attempt}次] 抓取成功: ${total_cap:,.0f}")
                                success = True
                                break
                    
                    if not success:
                        print(f"      ⚠️ [第{attempt}次] 页面下载成功，但未解析到有效总薪资，可能是表格结构变了。")
                        # 如果页面对了但没数，可能需要人工检查，这里我们选择重试
                        raise ValueError("Data Validation Failed")

                else:
                    print(f"      ❌ [第{attempt}次] HTTP {response.status_code}")
                    if response.status_code == 404:
                         print("      ⚠️ 404 Not Found, 该年份页面可能不存在。")
                         break # 404就不重试了

            except Exception as e:
                print(f"      ❌ [第{attempt}次] 错误: {str(e)[:100]}...") # 只打印前100个字符
            
            if not success:
                # 失败后的退避策略：休息时间随重试次数增加 (3s, 6s, 9s...)
                wait_time = attempt * 3 + random.uniform(1, 3)
                print(f"      ⏳ 休息 {wait_time:.1f} 秒后重试...")
                time.sleep(wait_time)

        if not success:
            print(f"      💀 {season} 赛季彻底失败，即使尝试了 {max_retries} 次。")
            # 如果你真的想要“宁缺毋滥”，这里就不添加任何数据
            # 如果想至少占个位，可以在这里加个空行

    # --- 保存 ---
    if all_data:
        final_df = pd.DataFrame(all_data)
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n💾 真实薪资数据已保存至: {OUTPUT_FILE}")
        print(final_df)
    else:
        print("\n⚠️ 未获取到任何数据。")

if __name__ == "__main__":
    get_salaries_hardcore()