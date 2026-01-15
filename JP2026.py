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
    """從 Google Sheets 讀取最新資料"""
    try:
        df = conn.read(ttl=0)
        return df.fillna("").astype(str)
    except Exception as e:
        st.error(f"讀取資料失敗，請檢查 Secrets 或試算表權限。錯誤: {e}")
        return pd.DataFrame(columns=["日期分類", "時間", "景點", "交通方式"])

def save_data_to_gs(all_data_dict):
    """將所有行程資料合併後更新回雲端"""
    combined_list = []
    for day, df in all_data_dict.items():
        temp_df = df.copy()
        temp_df['日期分類'] = day
        combined_list.append(temp_df)
    
    final_df = pd.concat(combined_list, ignore_index=True)
    conn.update(data=final_df)

# --- 3. 初始化行程資料 ---
days_options = [
    "Day 1: 02/11(三)", "Day 2: 02/12(四)", "Day 3: 02/13(五)",
    "Day 4: 02/14(六)", "Day 5: 02/15(日)", "Day 6: 02/16(一)", "Day 7: 02/17(二)"
]

if 'all_days_data' not in st.session_state:
    with st.spinner('正在同步雲端行程...'):
        saved_df = load_data_from_gs()
        st.session_state.all_days_data = {}
        for day in days_options:
            if not saved_df.empty and day in saved_df['日期分類'].values:
                day_data = saved_df[saved_df['日期分類'] == day].drop(columns=['日期分類'])
                st.session_state.all_days_data[day] = day_data.astype(str)
            else:
                st.session_state.all_days_data[day] = pd.DataFrame([{"時間": "", "景點": "", "交通方式": ""}]).astype(str)

# --- 4. 側邊欄設定 ---
with st.sidebar:
    st.header("📅 行程切換")
    selected_day = st.selectbox("切換日期", days_options)
    
    st.divider()
    st.markdown("### 🗺️ 導航設定")
    transport_mode = st.selectbox(
        "導航模式", 
        ["transit", "walking", "driving"], 
        format_func=lambda x: {"transit":"大眾運輸", "walking":"走路", "driving":"開車"}[x]
    )
    
    if st.button("🔄 重新載入雲端資料"):
        st.cache_data.clear()
        if 'all_days_data' in st.session_state:
            del st.session_state.all_days_data
        st.rerun()

st.title(f"✈️ {selected_day}")

# 分欄：左邊編輯區，右邊地圖區
col_left, col_right = st.columns([1.5, 1], gap="medium")

with col_left:
    st.subheader("📝 行程清單")
    with st.form(key=f"form_{selected_day}"):
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
        
        if st.form_submit_button("☁️ 儲存並更新至雲端"):
            st.session_state.all_days_data[selected_day] = edited_df
            save_data_to_gs(st.session_state.all_days_data)
            st.success("✅ 同步成功！")
            st.balloons()

with col_right:
    st.subheader("🗺️ 路線導航")
    current_df = st.session_state.all_days_data[selected_day]
    # 取得當天所有填寫過的景點名稱
    valid_places = [p for p in current_df["景點"].tolist() if str(p).strip() != ""]
    
    if len(valid_places) >= 1:
        # 1. 選擇起點與終點
        c1, c2 = st.columns(2)
        with c1:
            origin = st.selectbox("📍 起點：", ["我的位置"] + valid_places, index=0)
        with c2:
            # 預設終點選取最後一個輸入的景點
            destination = st.selectbox("🏁 終點：", valid_places, index=len(valid_places)-1)
        
        # 2. 編碼文字避免亂碼
        dest_q = urllib.parse.quote(destination)
        
        # 3. 顯示地圖預覽 (顯示終點位置)
        map_url = f"https://www.google.com/maps?q={dest_q}&output=embed&hl=zh-TW"
        components.html(
            f'<iframe width="100%" height="400" frameborder="0" src="{map_url}"></iframe>', 
            height=410
        )
        
        # 4. 產生 Google Maps 導航連結
        if origin == "我的位置":
            # 起點為目前位置的導航連結
            nav_url = f"https://www.google.com/maps/dir/?api=1&destination={dest_q}&travelmode={transport_mode}"
        else:
            origin_q = urllib.parse.quote(origin)
            # A 點到 B 點的導航連結
            nav_url = f"https://www.google.com/maps/dir/?api=1&origin={origin_q}&destination={dest_q}&travelmode={transport_mode}"
        
        st.link_button(f"🚀 開啟 Google Maps 路線規劃", nav_url, use_container_width=True, type="primary")
        st.caption(f"目前導航設定：從 {origin} 往 {destination} ({ {'transit':'大眾運輸', 'walking':'走路', 'driving':'開車'}[transport_mode] })")
    else:
        st.info("請在左側表格填入「景點」名稱，即可開啟地圖與導航功能。")

st.caption("2026 Japan Trip Planner - 已連線至雲端試算表")
