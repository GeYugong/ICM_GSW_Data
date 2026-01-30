import pandas as pd
import requests
import os
import time
import random

# --- 配置 ---
TEAM_CODE = "GSW"
OUTPUT_DRAFT_HISTORY = "data/gsw_draft_history.csv"
OUTPUT_FUTURE_ASSETS = "data/gsw_future_assets.csv" # 新增：未来资产
OUTPUT_TRANS = "data/gsw_transaction_counts.csv"

# --- 代理设置 ---
PROXIES = {
    "http": "http://127.0.0.1:7897",
    "https": "http://127.0.0.1:7897",
}
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

def get_draft_history():
    """
    抓取历史选秀记录 (修复版)
    """
    os.makedirs(os.path.dirname(OUTPUT_DRAFT_HISTORY), exist_ok=True)
    print(f"🏀 正在抓取选秀历史 (修复表头解析问题)...")
    
    url = f"https://www.basketball-reference.com/teams/{TEAM_CODE}/draft.html"
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, proxies=PROXIES, timeout=15)
        
        # 关键修复 1: 使用 match 参数精准定位包含 'Pick' 的表格
        dfs = pd.read_html(response.text, match="Pick")
        
        if not dfs:
            print("   ❌ 未找到选秀表格")
            return

        df = dfs[0]
        
        # 关键修复 2: 处理双层表头 (MultiIndex)
        # B-Ref 的表头通常是 (Draft, Year) 这种格式，我们需要扁平化
        if isinstance(df.columns, pd.MultiIndex):
            # 取最后一层列名 ('Year', 'Round', 'Pick' 等)
            df.columns = df.columns.get_level_values(-1)
        
        # 数据清洗
        # 过滤掉表头重复行
        if 'Pick' in df.columns:
            df = df[df['Pick'] != 'Pick']
        
        # 转换年份
        if 'Year' in df.columns:
            df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
            # 筛选 2020 至今的数据
            recent_drafts = df[df['Year'] >= 2020].copy()
            
            # 保存关键列
            cols = ['Year', 'Round', 'Pick', 'Player', 'College']
            # 确保列存在
            cols = [c for c in cols if c in recent_drafts.columns]
            recent_drafts = recent_drafts[cols]
            
            print(f"   ✅ 历史选秀抓取成功: {len(recent_drafts)} 条记录")
            recent_drafts.to_csv(OUTPUT_DRAFT_HISTORY, index=False)
        else:
            print(f"   ❌ 列名匹配失败，当前列名: {df.columns.tolist()}")

    except Exception as e:
        print(f"   ❌ 选秀抓取失败: {e}")

def generate_future_assets():
    """
    生成未来选秀权资产数据 (手动硬编码)
    原因：未来选秀权的具体情况通常隐藏在复杂的交易文本中，爬虫很难解析。
    这部分数据对于衡量 m 向量中的 'Asset Value' 至关重要。
    数据来源：RealGM Future Drafts Summary (勇士队)
    """
    print(f"\n🔮 生成未来选秀权资产表 (Based on 2025 Status)...")
    
    # 0 = 无/已交易, 1 = 拥有, 0.5 = 受保护/互换权
    future_data = [
        {"Season": 2025, "First_Round_Pick": 0, "Second_Round_Pick": 0, "Note": "Traded to POR/BOS"}, # 2025年几乎没有签
        {"Season": 2026, "First_Round_Pick": 1, "Second_Round_Pick": 1, "Note": "Own Pick"},       # 2026年有首轮
        {"Season": 2027, "First_Round_Pick": 1, "Second_Round_Pick": 0, "Note": "Own 1st, 2nd Traded"},
        {"Season": 2028, "First_Round_Pick": 1, "Second_Round_Pick": 1, "Note": "Own Pick"},
        {"Season": 2029, "First_Round_Pick": 1, "Second_Round_Pick": 1, "Note": "Own Pick"},
        {"Season": 2030, "First_Round_Pick": 0.5, "Second_Round_Pick": 1, "Note": "Top-20 Protected"}, # 假设受保护
    ]
    
    df = pd.DataFrame(future_data)
    df.to_csv(OUTPUT_FUTURE_ASSETS, index=False)
    print(f"   💾 未来资产保存至: {OUTPUT_FUTURE_ASSETS}")

def get_transaction_activity():
    """
    抓取交易活跃度 (保持不变，因为这部分之前运行成功了)
    """
    print(f"\n🤝 正在抓取交易/签约记录 (Transactions)...")
    url = f"https://www.basketball-reference.com/teams/{TEAM_CODE}/transactions.html"
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, proxies=PROXIES, timeout=15)
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        years = range(2021, 2026)
        stats = []
        lines = page_text.split('\n')
        
        for year in years:
            n_signed = 0
            n_traded = 0
            for line in lines:
                if str(year) in line:
                    lower = line.lower()
                    if "signed" in lower: n_signed += 1
                    if "traded" in lower: n_traded += 1
            
            stats.append({"Season": year, "Acquisitions": n_signed, "Trades": n_traded})
            
        pd.DataFrame(stats).to_csv(OUTPUT_TRANS, index=False)
        print(f"   ✅ 交易统计完成，保存至: {OUTPUT_TRANS}")

    except Exception as e:
        print(f"   ❌ 交易抓取失败: {e}")

if __name__ == "__main__":
    get_draft_history()
    generate_future_assets() # 新增步骤
    get_transaction_activity()