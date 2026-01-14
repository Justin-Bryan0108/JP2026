import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import urllib.parse
from streamlit_gsheets import GSheetsConnection

# --- 1. 網頁基本配置 ---
st.set_page_config(page_title="2026 日本旅遊雲端版", layout="wide", page_icon="🇯🇵")

# --- 2. 建立 Google Sheets 連接 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_from_gs():
    try:
        # 讀取整張表
        df = conn.read(ttl=0) # ttl=0 確保每次都讀取最新資料，不使用快取
        return df.fillna("").astype(str)
    except:
        return pd.DataFrame(columns=["日期分類", "時間", "景點", "交通方式"])

def save_data_to_gs(all_data_dict):
    combined_list = []
    for day, df in all_data_dict.items():
        temp_df = df.copy()
        temp_df['日期分類'] = day
        combined_list.append(temp_df)
    final_df = pd.concat(combined_list, ignore_index=True)
    # 更新回 Google Sheets
    conn.update(data=final_df)

# --- 3. 初始化資料 ---
days_options = [
    "Day 1: 02/11(三)", "Day 2: 02/12(四)", "Day 3: 02/13(五)",
    "Day 4: 02/14(六)", "Day 5: 02/15(日)", "Day 6: 02/16(一)", "Day 7: 02/17(二)"
]

if 'all_days_data' not in st.session_state:
    saved_df = load_data_from_gs()
    st.session_state.all_days_data = {}
    for day in days_options:
        if not saved_df.empty and day in saved_df['日期分類'].values:
            st.session_state.all_days_data[day] = saved_df[saved_df['日期分類'] == day].drop(columns=['日期分類']).astype(str)
        else:
            st.session_state.all_days_data[day] = pd.DataFrame([{"時間": "", "景點": "", "交通方式": ""}]).astype(str)

# --- 4. 介面邏輯 (側邊欄與主要區域) ---
with st.sidebar:
    st.header("📅 雲端同步選單")
    selected_day = st.selectbox("切換日期", days_options)
    if st.button("🔄 手動刷新資料"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    transport_mode = st.selectbox("導航模式", ["transit", "walking", "driving"])

st.title(f"✈️ {selected_day}")

col_left, col_right = st.columns([1.2, 1], gap="medium")

with col_left:
    with st.form(key=f"form_{selected_day}"):
        edited_df = st.data_editor(
            st.session_state.all_days_data[selected_day],
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "時間": st.column_config.TextColumn("⏰ 時間", width="small"),
                "景點": st.column_config.TextColumn("📍 景點"),
                "交通方式": st.column_config.TextColumn("🚌 交通/備註")
            }
        )
        if st.form_submit_button("☁️ 儲存並同步至雲端"):
            st.session_state.all_days_data[selected_day] = edited_df
            save_data_to_gs(st.session_state.all_days_data)
            st.success("雲端同步成功！家人現在也能看到最新行程了。")
            st.rerun()

with col_right:
    st.subheader("🗺️ 即時地圖")
    current_df = st.session_state.all_days_data[selected_day]
    valid_places = [p for p in current_df["景點"].tolist() if str(p).strip() != ""]
    
    if valid_places:
        view_target = st.selectbox("選取景點：", valid_places)
        q = urllib.parse.quote(view_target)
        map_url = f"https://maps.google.com/maps?q={q}&output=embed"
        components.html(f'<iframe width="100%" height="450" src="{map_url}"></iframe>', height=460)
        st.link_button(f"🚀 開啟導航", f"https://www.google.com/maps/dir/?api=1&destination={q}&travelmode={transport_mode}", use_container_width=True)