import pandas as pd
import requests
import os
import time
import random

# --- 配置 ---
SEASONS = list(range(2021, 2027)) 
TEAM_CODE = "GSW"
OUTPUT_FILE = "data/gsw_schedule_5years.csv"

# --- 关键网络配置 ---
# 1. 设置你的代理地址 (端口 7897)
PROXIES = {
    "http": "http://127.0.0.1:7897",
    "https": "http://127.0.0.1:7897",
}

# 2. 清除系统环境变量干扰 (防止与其他软件冲突)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

def get_schedule_multi_year():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    all_seasons_data = [] 

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    print(f"🏀 开始抓取 {SEASONS[0]}-{SEASONS[-1]} 赛季数据 (使用代理: 127.0.0.1:7897)...")

    for season in SEASONS:
        url = f"https://www.basketball-reference.com/teams/{TEAM_CODE}/{season}_games.html"
        print(f"   ⏳ 正在处理 {season} 赛季: {url} ...")
        
        try:
            # 关键：这里传入 proxies 参数，强制走 7897 端口
            # timeout=20 防止一直卡住
            response = requests.get(url, headers=headers, proxies=PROXIES, timeout=20)
            
            if response.status_code == 404:
                print(f"   ⚠️ {season} 赛季页面不存在，跳过。")
                continue
                
            response.raise_for_status()
            
            # --- 解析与清洗 ---
            dfs = pd.read_html(response.text)
            season_df = dfs[0]
            
            # 过滤表头
            season_df = season_df[season_df['G'] != 'G'].copy()
            
            # 列名处理
            if 'Unnamed: 7' not in season_df.columns and 'Unnamed: 5' in season_df.columns:
                season_df.rename(columns={'Unnamed: 5': 'Result'}, inplace=True)
            else:
                season_df.rename(columns={'Unnamed: 7': 'Result'}, inplace=True)

            season_df.rename(columns={'Tm': 'Points_Scored', 'Opp': 'Points_Allowed'}, inplace=True)
            
            # 筛选列
            cols_to_keep = ['Date', 'Opponent', 'Result', 'Points_Scored', 'Points_Allowed']
            season_df = season_df[[c for c in cols_to_keep if c in season_df.columns]]
            
            # 丢弃未开赛场次
            season_df = season_df.dropna(subset=['Result'])
            
            # 添加赛季标签
            season_df['Season'] = season
            
            # 胜负逻辑
            season_df['Win_Flag'] = season_df['Result'].apply(lambda x: 1 if x == 'W' else 0)
            
            # 计算近期胜率
            season_df['Recent_Win_Rate_10'] = season_df['Win_Flag'].rolling(window=10).mean()
            season_df['Recent_Win_Rate_10'] = season_df['Recent_Win_Rate_10'].fillna(
                season_df['Win_Flag'].expanding().mean()
            )
            
            all_seasons_data.append(season_df)
            print(f"   ✅ {season} 赛季获取成功 ({len(season_df)} 场)。")

            # 随机休眠
            time.sleep(random.uniform(2, 4))

        except requests.exceptions.ProxyError:
            print(f"   ❌ 代理连接失败: 请确认你的代理软件正在运行，且端口确实是 7897。")
        except requests.exceptions.SSLError:
            print(f"   ❌ SSL 验证失败: 请尝试将 requests.get 中的 verify 改为 False。")
        except Exception as e:
            print(f"   ❌ {season} 赛季抓取失败: {e}")

    # --- 保存 ---
    if all_seasons_data:
        final_df = pd.concat(all_seasons_data, ignore_index=True)
        final_df['Points_Scored'] = pd.to_numeric(final_df['Points_Scored'], errors='coerce')
        final_df['Points_Allowed'] = pd.to_numeric(final_df['Points_Allowed'], errors='coerce')
        
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n💾 5年完整数据已保存至: {OUTPUT_FILE}")
    else:
        print("\n⚠️ 未获取到任何数据，请检查网络设置。")

if __name__ == "__main__":
    get_schedule_multi_year()