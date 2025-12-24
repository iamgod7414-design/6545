import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.express as px
import os

# --- 設定 ---
st.set_page_config(page_title="雲端外匯交易紀錄系統", layout="wide")
st.title("🌐 Cloud Forex Trading Journal")

# 這是你的試算表網址 (已根據截圖填入)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1cRHmM9wPughGNmLboM844Hr4SiULdQrP53vAG_h5e8Q/edit#gid=0"

# 初始化連線
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # 強制在讀取時指定網址
    return conn.read(spreadsheet=SHEET_URL, ttl="0")

def save_data(df):
    # 強制在寫入時指定網址
    conn.update(spreadsheet=SHEET_URL, data=df)

# --- 邏輯處理 ---
df = load_data()

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
        # 確保 ID 是整數
        new_id = int(df['id'].max() + 1) if not df.empty and 'id' in df.columns else 1
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
            "notes": notes
        }])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        save_data(updated_df)
        st.success("雲端儲存成功！")
        st.rerun()

elif choice == "數據統計":
    st.header("📊 雲端數據分析")
    if not df.empty:
        # 確保時間格式正確
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values(by='time', ascending=True)
        df['cumulative_profit'] = df['profit'].cumsum()
        
        col_m1, col_m2 = st.columns(2)
        win_rate = (df['outcome'] == '勝').sum() / len(df) * 100
        col_m1.metric("總交易次數", len(df))
        col_m2.metric("勝率", f"{win_rate:.2f}%")
        
        st.plotly_chart(px.line(df, x='time', y='cumulative_profit', title='資金曲線'), use_container_width=True)
        st.dataframe(df.sort_values(by='time', ascending=False), use_container_width=True)

        st.divider()
        delete_id = st.number_input("輸入要刪除的 ID", step=1, value=0)
        if st.button("確認刪除", type="primary"):
            df = df[df['id'] != delete_id]
            save_data(df)
            st.warning(f"ID {delete_id} 已從雲端刪除")
            st.rerun()
    else:
        st.warning("尚無資料。")

elif choice == "匯出與導出":
    st.header("📤 數據導出")
    if not df.empty:
        json_data = df.to_json(orient='records', force_ascii=False)
        st.download_button("下載 JSON 給 Gemini", json_data, file_name="trades.json", mime="application/json")
    else:
        st.warning("無資料可匯出")
