import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.express as px
import plotly.io as pio
from fpdf import FPDF
import io
import os

# --- 基礎設定 ---
st.set_page_config(page_title="雲端外匯交易紀錄系統", layout="wide")
st.title("🌐 Cloud Forex Trading Journal")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1cRHmM9wPughGNmLboM844Hr4SiULdQrP53vAG_h5e8Q/edit"
SHEET_NAME = "Sheet1" 

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(spreadsheet=SHEET_URL, worksheet=SHEET_NAME, ttl=0)

def save_data(df):
    conn.update(spreadsheet=SHEET_URL, worksheet=SHEET_NAME, data=df)

# --- 讀取資料 ---
try:
    df = load_data()
    df = df.dropna(how='all')
except Exception as e:
    st.error("⚠️ 無法讀取 Google Sheets")
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
        setup = st.text_area("進場設置 (例如: SnR Bounce, S/R Flip)")
    with col2:
        target_rr = st.number_input("目標止盈 RR", min_value=0.0, step=0.1)
        profit = st.number_input("結算獲利金額 (USD)", step=1.0)
        actual_rr = st.number_input("實際結算 RR", step=0.1)
        notes = st.text_area("備註")

    if st.button("儲存紀錄"):
        try:
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
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("🎉 資料已同步！")
            st.balloons()
            st.rerun()
        except Exception as e:
            st.error(f"儲存失敗：{e}")

elif choice == "數據統計":
    st.header("📊 績效統計與資金曲線")
    if not df.empty and len(df) > 0:
        # 資料預處理
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        df = df.dropna(subset=['time']).sort_values(by='time')
        df['profit'] = pd.to_numeric(df['profit'], errors='coerce').fillna(0)
        df['cumulative_profit'] = df['profit'].cumsum()
        
        # 指標顯示
        col1, col2, col3 = st.columns(3)
        win_count = (df['outcome'] == '勝').sum()
        win_rate = win_count / len(df) * 100
        col1.metric("總交易次數", len(df))
        col2.metric("勝率", f"{win_rate:.2f}%")
        col3.metric("總盈虧", f"${df['profit'].sum():.2f}")
        
        # 繪製圖表
        fig = px.line(df, x='time', y='cumulative_profit', 
                     title='資金曲線 (Equity Curve)', 
                     markers=True, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        # 歷史清單
        st.subheader("📜 交易歷史紀錄")
        st.dataframe(df.sort_values(by='id', ascending=False), use_container_width=True)
        
        st.divider()
        delete_id = st.number_input("輸入要刪除的 ID", step=1, value=0)
        if st.button("確認刪除", type="primary"):
            save_data(df[df['id'] != delete_id])
            st.warning(f"ID {delete_id} 已從雲端刪除")
            st.rerun()
    else:
        st.warning("目前尚無資料。")

elif choice == "匯出與導出":
    st.header("📤 導出報表")
    if not df.empty:
        # 1. JSON 導出
        st.subheader("1. AI 訓練導出 (JSON)")
        json_data = df.to_json(orient='records', force_ascii=False)
        st.download_button("下載 JSON 給 Gemini", json_data, file_name="trading_data.json")
        
        # 2. PDF 導出 (包含圖表)
        st.subheader("2. PDF 報告導出 (包含資金圖)")
        if st.button("生成 PDF 報告"):
            with st.spinner("正在生成報告..."):
                # 重新整理資料以繪圖
                df['time'] = pd.to_datetime(df['time'])
                df = df.sort_values(by='time')
                df['cumulative_profit'] = df['profit'].cumsum()
                
                # 生成圖表圖片
                fig = px.line(df, x='time', y='cumulative_profit', title='Equity Curve')
                img_bytes = pio.to_image(fig, format="png", width=800, height=400)
                
                # 製作 PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 16)
                pdf.cell(0, 10, "Trading Journal Report", ln=True, align='C')
                
                # 插入圖表
                pdf.image(io.BytesIO(img_bytes), x=10, y=30, w=190)
                
                # 插入統計文字
                pdf.set_y(130)
                pdf.set_font("Helvetica", size=12)
                pdf.cell(0, 10, f"Total Trades: {len(df)}", ln=True)
                pdf.cell(0, 10, f"Total Profit: ${df['profit'].sum()}", ln=True)
                
                # 插入表格摘要 (改用英文標題以避免 PDF 編碼錯誤)
                pdf.ln(10)
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(20, 10, "ID", 1)
                pdf.cell(40, 10, "Time", 1)
                pdf.cell(20, 10, "Dir", 1)
                pdf.cell(30, 10, "Profit", 1)
                pdf.cell(20, 10, "Res", 1)
                pdf.ln()
                
                pdf.set_font("Helvetica", size=9)
                for _, row in df.sort_values(by='time', ascending=False).head(20).iterrows():
                    pdf.cell(20, 8, str(row['id']), 1)
                    pdf.cell(40, 8, str(row['time'])[:10], 1)
                    pdf.cell(20, 8, str(row['direction']), 1)
                    pdf.cell(30, 8, str(row['profit']), 1)
                    pdf.cell(20, 8, "Win" if row['profit']>0 else "Loss", 1)
                    pdf.ln()
                
                pdf_output = pdf.output()
                st.download_button("點此下載 PDF 報告", pdf_output, file_name="report.pdf", mime="application/pdf")
    else:
        st.warning("無資料可匯出")
