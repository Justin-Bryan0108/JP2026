import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import urllib.parse
from streamlit_gsheets import GSheetsConnection

# --- 1. 網頁基本配置 ---
st.set_page_config(page_title="2026 日本旅遊雲端版", layout="wide", page_icon="🇯🇵")

# --- 2. 建立 Google Sheets 連接 ---
# 這裡會自動讀取你在 Streamlit Cloud Secrets 設定的金鑰與網址
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_from_gs():
    """從 Google Sheets 讀取資料"""
    try:
        # ttl=0 代表不使用快取，每次重新整理都抓最新的資料
        df = conn.read(ttl=0)
        # 確保所有資料都是字串，避免處理數字時出錯
        return df.fillna("").astype(str)
    except Exception as e:
        st.error(f"讀取資料失敗，請檢查 Secrets 設定或試算表權限。錯誤: {e}")
        return pd.DataFrame(columns=["日期分類", "時間", "景點", "交通方式"])

def save_data_to_gs(all_data_dict):
    """將所有日期的資料合併後存回 Google Sheets"""
    combined_list = []
    for day, df in all_data_dict.items():
        temp_df = df.copy()
        temp_df['日期分類'] = day
        combined_list.append(temp_df)
    
    final_df = pd.concat(combined_list, ignore_index=True)
    # 執行更新動作
    conn.update(data=final_df)

# --- 3. 初始化行程資料 ---
days_options = [
    "Day 1: 2026/02/11(三)", "Day 2: 2026/02/12(四)", "Day 3: 2026/02/13(五)",
    "Day 4: 2026/02/14(六)", "Day 5: 2026/02/15(日)", "Day 6: 2026/02/16(一)", "Day 7: 2026/02/17(二)"
]

# 首次執行時從雲端抓取資料
if 'all_days_data' not in st.session_state:
    with st.spinner('正在從雲端下載行程...'):
        saved_df = load_data_from_gs()
        st.session_state.all_days_data = {}
        
        for day in days_options:
            # 如果雲端有該日期的資料就讀取，沒有就建立空的
            if not saved_df.empty and day in saved_df['日期分類'].values:
                day_data = saved_df[saved_df['日期分類'] == day].drop(columns=['日期分類'])
                st.session_state.all_days_data[day] = day_data.astype(str)
            else:
                st.session_state.all_days_data[day] = pd.DataFrame([{"時間": "", "景點": "", "交通方式": ""}]).astype(str)

# --- 4. 介面佈局 ---
with st.sidebar:
    st.header("📅 行程選單")
    selected_day = st.selectbox("切換日期", days_options)
    
    st.divider()
    st.markdown("### 🗺️ 導航設定")
    transport_mode = st.selectbox("導航模式", ["transit", "walking", "driving"], 
                                  format_func=lambda x: {"transit":"大眾運輸", "walking":"走路", "driving":"開車"}[x])
    
    if st.button("🔄 重新從雲端載入"):
        st.cache_data.clear()
        del st.session_state.all_days_data
        st.rerun()

st.title(f"✈️ {selected_day}")

# 分成左右兩欄：左邊編輯行程，右邊看地圖
col_left, col_right = st.columns([1.5, 1], gap="medium")

with col_left:
    st.subheader("📝 編輯行程")
    with st.form(key=f"form_{selected_day}"):
        # 使用 data_editor 讓使用者可以直接改表格
        edited_df = st.data_editor(
            st.session_state.all_days_data[selected_day],
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "時間": st.column_config.TextColumn("⏰ 時間", width="small"),
                "景點": st.column_config.TextColumn("📍 景點"),
                "交通方式": st.column_config.TextColumn("🚌 備註")
            }
        )
        
        submit_button = st.form_submit_button("☁️ 儲存並同步到雲端")
        
        if submit_button:
            st.session_state.all_days_data[selected_day] = edited_df
            with st.spinner('正在同步至 Google Sheets...'):
                save_data_to_gs(st.session_state.all_days_data)
            st.success("✅ 同步成功！家人刷新網頁即可看到更新。")
            st.balloons()

with col_right:
    st.subheader("🗺️ 即時地圖與導航")
    current_df = st.session_state.all_days_data[selected_day]
    # 抓取有填寫景點名稱的行
    valid_places = [p for p in current_df["景點"].tolist() if str(p).strip() != ""]
    
    if valid_places:
        view_target = st.selectbox("選擇景點：", valid_places)
        
        # 安全編碼景點文字
        encoded_q = urllib.parse.quote(view_target)
        
        # 1. 內嵌地圖 (使用標準 Google Maps 搜尋 URL)
        # 這個格式相容性最高，不需要額外申請 API Key
        map_url = f"https://www.google.com/maps?q={encoded_q}&output=embed&hl=zh-TW"
        components.html(
            f'<iframe width="100%" height="450" frameborder="0" src="{map_url}"></iframe>', 
            height=460
        )
        
        # 2. 修正後的導航連結 (使用 Google Maps Directions API 標準連結)
        # destination: 目的地, travelmode: 交通模式
        nav_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_q}&travelmode={transport_mode}"
        
        st.link_button(f"🚀 開啟 Google Maps 導航", nav_url, use_container_width=True)
    else:
        st.info("請在左側表格填入「景點」名稱後，地圖就會出現囉！")

# --- 頁尾資訊 ---
st.caption("2026 Japan Trip Planner - 資料即時同步於 Google Sheets")
