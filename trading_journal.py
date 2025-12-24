import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.express as px

# --- 基礎設定 ---
st.set_page_config(page_title="雲端外匯交易紀錄系統", layout="wide")
st.title("🌐 Cloud Forex Trading Journal")

# 1. 你的試算表網址（已簡化）
SHEET_URL = "https://docs.google.com/spreadsheets/d/1cRHmM9wPughGNmLboM844Hr4SiULdQrP53vAG_h5e8Q"
# 2. 你的分頁名稱（務必與截圖中的 Sheet1 一致）
SHEET_NAME = "Sheet1" 

# 初始化 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # 讀取雲端資料
    return conn.read(spreadsheet=SHEET_URL, worksheet=SHEET_NAME, ttl=0)

def save_data(df):
    # 將整份 DataFrame 覆蓋回雲端
    conn.update(spreadsheet=SHEET_URL, worksheet=SHEET_NAME, data=df)

# --- 嘗試讀取資料 ---
try:
    df = load_data()
    # 移除完全空白的列
    df = df.dropna(how='all')
except Exception as e:
    st.error("⚠️ 無法連線至 Google Sheets")
    st.warning(f"技術訊息：{e}")
    df = pd.DataFrame()

# --- 介面選單 ---
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
        # 計算新的 ID
        if not df.empty and 'id' in df.columns:
            try:
                max_id = pd.to_numeric(df['id'], errors='coerce').max()
                new_id = int(max_id + 1) if not pd.isna(max_id) else 1
            except:
                new_id = 1
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
        
        # 合併新舊資料
        updated_df = pd.concat([df, new_row], ignore_index=True)
        
        try:
            save_data(updated_df)
            st.success("🎉 紀錄已成功同步至 Google Sheets！")
            st.balloons()
            st.rerun()
        except Exception as e:
            st.error(f"儲存失敗，請檢查 Secrets 權限設定。錯誤: {e}")

elif choice == "數據統計":
    st.header("📊 交易績效分析")
    if not df.empty and len(df) > 0:
        # 數據轉換處理
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        df = df.dropna(subset=['time']).sort_values(by='time')
        df['profit'] = pd.to_numeric(df['profit'], errors='coerce').fillna(0)
        df['cumulative_profit'] = df['profit'].cumsum()
        
        col1, col2 = st.columns(2)
        win_rate = (df['outcome'] == '勝').sum() / len(df) * 100
        col1.metric("總交易次數", len(df))
        col2.metric("勝率", f"{win_rate:.2f}%")
        
        st.plotly_chart(px.line(df, x='time', y='cumulative_profit', title='資金曲線 (Equity Curve)'), use_container_width=True)
        st.dataframe(df.sort_values(by='id', ascending=False), use_container_width=True)
        
        st.divider()
        st.subheader("🗑️ 刪除紀錄")
        delete_id = st.number_input("輸入要刪除的 ID", step=1, value=0)
        if st.button("確認刪除", type="primary"):
            updated_df = df[df['id'] != delete_id]
            save_data(updated_df)
            st.warning(f"ID {delete_id} 已從雲端刪除")
            st.rerun()
    else:
        st.warning("目前尚無資料可統計。")

elif choice == "匯出與導出":
    st.header("📤 導出 JSON 資料給 Gemini")
    if not df.empty:
        json_data = df.to_json(orient='records', force_ascii=False)
        st.download_button("下載 JSON 檔案", json_data, file_name="trading_data.json", mime="application/json")
        st.info("💡 下載此檔案後，直接貼給 Gemini 即可開始生成 EA 策略分析。")
