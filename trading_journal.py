import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.express as px

# --- 設定 ---
st.set_page_config(page_title="雲端外匯交易紀錄系統", layout="wide")
st.title("🌐 Cloud Forex Trading Journal")

# 1. 簡化網址：去掉 /edit#gid=0 之後的內容，只保留到 ID
SHEET_URL = "https://docs.google.com/spreadsheets/d/1cRHmM9wPughGNmLboM844Hr4SiULdQrP53vAG_h5e8Q"
# 2. 確保這是純文字，沒有空格或引號
SHEET_NAME = "Sheet1" 

# 初始化連線
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # 使用最簡單的讀取方式
    return conn.read(spreadsheet=SHEET_URL, worksheet=SHEET_NAME, ttl=0)

def save_data(df):
    conn.update(spreadsheet=SHEET_URL, worksheet=SHEET_NAME, data=df)

# --- 讀取資料 ---
try:
    df = load_data()
    # 確保資料表不是空的，且包含必要的欄位
    if df.empty:
        # 如果是空的，建立一個帶有標題的初始 DataFrame
        df = pd.DataFrame(columns=['id', 'time', 'direction', 'timeframe', 'target_rr', 'actual_rr', 'profit', 'outcome', 'setup', 'screenshot_path', 'notes'])
except Exception as e:
    st.error("⚠️ 連線失敗！")
    st.info(f"請檢查：\n1. Google 表格分頁名稱是否『剛好』是 Sheet1 (不能有引號或空格)\n2. 網址是否正確\n3. 權限是否已開啟給 Service Account")
    st.warning(f"技術錯誤訊息: {e}")
    df = pd.DataFrame()

# --- 後續選單邏輯 ---
menu = ["新增交易", "數據統計", "匯出與導出"]
choice = st.sidebar.selectbox("選單", menu)

if choice == "新增交易":
    st.header("📝 紀錄新交易")
    col1, col2 = st.columns(2)
    with col1:
        trade_date = st.date_input("交易日期", datetime.now())
        trade_time = st.time_input("交易時間", datetime.now())
        direction = st.selectbox("方向", ["Buy", "Sell"])
        timeframe = st.selectbox("時間級別", ["M5", "M15", "M30", "H1", "H4", "D1"])
        setup = st.text_area("進場設置")
    with col2:
        target_rr = st.number_input("目標止盈 RR", min_value=0.0, step=0.1)
        profit = st.number_input("結算獲利金額 (USD)", step=1.0)
        actual_rr = st.number_input("實際結算 RR", step=0.1)
        notes = st.text_area("備註")

    if st.button("儲存紀錄到雲端"):
        # 安全取得最大 ID
        try:
            if not df.empty and 'id' in df.columns:
                max_id = pd.to_numeric(df['id'], errors='coerce').max()
                new_id = int(max_id + 1) if not pd.isna(max_id) else 1
            else:
                new_id = 1
        except:
            new_id = 1
            
        new_row = pd.DataFrame([{
            "id": new_id,
            "time": f"{trade_date} {trade_time}",
            "direction": direction,
            "timeframe": timeframe,
            "target_rr": target_rr,
            "actual_rr": actual_rr,
            "profit": profit,
            "outcome": "勝" if profit > 0 else "敗",
            "setup": setup,
            "screenshot_path": "", 
            "notes": str(notes)
        }])
        
        updated_df = pd.concat([df, new_row], ignore_index=True)
        
        try:
            save_data(updated_df)
            st.success("🎉 儲存成功！")
            st.rerun()
        except Exception as e:
            st.error(f"儲存失敗: {e}")

elif choice == "數據統計":
    st.header("📊 雲端數據分析")
    if not df.empty and len(df) > 0:
        # 統計圖表顯示內容... (同前)
        st.dataframe(df.sort_values(by='id', ascending=False), use_container_width=True)
    else:
        st.warning("目前雲端尚無交易資料。")

elif choice == "匯出與導出":
    st.header("📤 數據導出")
    if not df.empty:
        json_data = df.to_json(orient='records', force_ascii=False)
        st.download_button("下載 JSON 給 Gemini", json_data, file_name="trades.json", mime="application/json")
