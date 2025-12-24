import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.express as px

# --- 基礎設定 ---
st.set_page_config(page_title="雲端外匯交易紀錄系統", layout="wide")
st.title("🌐 Cloud Forex Trading Journal")

# 【重要：請確認網址】這是從您的截圖中提取的 ID
# 網址：https://docs.google.com/spreadsheets/d/1cRHmM9wPughGNmLboM844Hr4SiULdQrP53vAG_h5e8Q/edit
# ID 就是 d/ 之後，/edit 之前的那串字
SHEET_URL = "https://docs.google.com/spreadsheets/d/1cRHmM9wPughGNmLboM844Hr4SiULdQrP53vAG_h5e8Q/edit"

# 初始化連線
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # 使用指名道姓的方式讀取，分頁名稱務必是 Sheet1
    return conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)

def save_data(df):
    conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=df)

# --- 嘗試讀取資料 ---
try:
    df = load_data()
    df = df.dropna(how='all')
    if df.empty:
        df = pd.DataFrame(columns=['id', 'time', 'direction', 'timeframe', 'target_rr', 'actual_rr', 'profit', 'outcome', 'setup', 'screenshot_path', 'notes'])
except Exception as e:
    st.error("⚠️ 無法讀取 Google 表格")
    st.warning(f"可能原因：1.金鑰已更換但 Secrets 未更新 2.試算表未共用給 Service Account 3.分頁名稱不是 Sheet1")
    st.info(f"技術訊息：{e}")
    df = pd.DataFrame()

# --- 選單介面 ---
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

    if st.button("儲存紀錄"):
        try:
            # 安全計算新 ID
            if not df.empty and 'id' in df.columns:
                max_id = pd.to_numeric(df['id'], errors='coerce').max()
                new_id = int(max_id + 1) if not pd.isna(max_id) else 1
            else:
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
            save_data(updated_df)
            st.success("🎉 資料已寫入雲端表格！")
            st.rerun()
        except Exception as e:
            st.error(f"儲存失敗：{e}")

elif choice == "數據統計":
    st.header("📊 績效統計")
    if not df.empty and len(df) > 0:
        st.dataframe(df.sort_values(by='id', ascending=False), use_container_width=True)
    else:
        st.warning("目前尚無資料。")

elif choice == "匯出與導出":
    st.header("📤 導出")
    if not df.empty:
        st.download_button("下載 JSON", df.to_json(orient='records', force_ascii=False), file_name="trades.json")
