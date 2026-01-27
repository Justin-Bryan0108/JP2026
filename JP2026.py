import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import urllib.parse
from streamlit_gsheets import GSheetsConnection

# --- 1. 網頁基本配置 ---
st.set_page_config(page_title="2026 日本旅遊雲端專業版", layout="wide", page_icon="🇯🇵")

# --- 2. 建立 Google Sheets 連接 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_from_gs(sheet_name="行程"):
    """從 Google Sheets 指定分頁讀取資料"""
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df.fillna("").astype(str)
    except Exception as e:
        st.error(f"讀取「{sheet_name}」失敗。請確保雲端試算表有此分頁名稱。")
        return pd.DataFrame()

def save_all_to_gs(all_data_dict, sheet_name="行程"):
    """將資料更新回雲端"""
    try:
        combined_list = []
        for day, df in all_data_dict.items():
            temp_df = df.copy()
            temp_df['日期分類'] = day
            combined_list.append(temp_df)
        
        final_df = pd.concat(combined_list, ignore_index=True)
        conn.update(worksheet=sheet_name, data=final_df)
        st.success(f"✅ {sheet_name} 同步成功！")
        st.balloons()
    except Exception as e:
        st.error(f"儲存失敗：{e}")

# --- 3. 初始化行程資料與狀態 ---
days_options = [
    "Day 1: 02/11(三)", "Day 2: 02/12(四)", "Day 3: 02/13(五)",
    "Day 4: 02/14(六)", "Day 5: 02/15(日)", "Day 6: 02/16(一)", "Day 7: 02/17(二)"
]

# --- 4. 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 管理面板")
    app_mode = st.radio("功能模式", ["📅 每日行程", "💰 預算管理", "🏨 住宿資訊"])
    
    st.divider()
    
    if app_mode == "📅 每日行程":
        selected_day = st.selectbox("切換日期", days_options)
        transport_mode = st.selectbox(
            "導航模式", ["transit", "walking", "driving"], 
            format_func=lambda x: {"transit":"大眾運輸", "walking":"走路", "driving":"開車"}[x]
        )
    
    if st.button("🔄 強制重新載入雲端資料"):
        st.cache_data.clear()
        if 'all_days_data' in st.session_state: del st.session_state.all_days_data
        st.rerun()

# --- 5. 邏輯處理：每日行程 ---
if app_mode == "📅 每日行程":
    if 'all_days_data' not in st.session_state:
        with st.spinner('同步雲端行程中...'):
            saved_df = load_data_from_gs("行程")
            st.session_state.all_days_data = {}
            for day in days_options:
                if not saved_df.empty and '日期分類' in saved_df.columns and day in saved_df['日期分類'].values:
                    day_data = saved_df[saved_df['日期分類'] == day].drop(columns=['日期分類'])
                    # 確保有序號欄位
                    if "序號" not in day_data.columns: day_data.insert(0, "序號", range(1, len(day_data)+1))
                    st.session_state.all_days_data[day] = day_data
                else:
                    st.session_state.all_days_data[day] = pd.DataFrame([{"序號": "1", "時間": "", "景點": "", "交通備註": ""}]).astype(str)

    st.title(f"✈️ {selected_day}")
    col_left, col_right = st.columns([1.6, 1], gap="medium")

    with col_left:
        st.subheader("📝 行程清單")
        curr_df = st.session_state.all_days_data[selected_day]
        
        # 排序與編輯
        edited_df = st.data_editor(
            curr_df, num_rows="dynamic", use_container_width=True,
            column_config={
                "序號": st.column_config.NumberColumn("🔢 序號", width="small"),
                "時間": st.column_config.TextColumn("⏰ 時間"),
                "景點": st.column_config.TextColumn("📍 景點"),
                "交通備註": st.column_config.TextColumn("🚌 備註")
            }
        )

        c1, c2 = st.columns(2)
        if c1.button("🪄 依照序號排序並暫存"):
            edited_df["序號"] = pd.to_numeric(edited_df["序號"], errors='coerce').fillna(99)
            sorted_df = edited_df.sort_values(by="序號").reset_index(drop=True)
            sorted_df["序號"] = range(1, len(sorted_df) + 1)
            st.session_state.all_days_data[selected_day] = sorted_df.astype(str)
            st.rerun()
            
        if c2.button("☁️ 儲存全部行程至雲端", type="primary"):
            st.session_state.all_days_data[selected_day] = edited_df
            save_all_to_gs(st.session_state.all_days_data, "行程")

    with col_right:
        st.subheader("🗺️ 路線導航")
        valid_places = [p for p in edited_df["景點"].tolist() if str(p).strip() != ""]
        if valid_places:
            origin = st.selectbox("📍 起點", ["我的位置"] + valid_places)
            destination = st.selectbox("🏁 終點", valid_places, index=len(valid_places)-1)
            dest_q = urllib.parse.quote(destination)
            
            # 內嵌地圖預覽
            embed_url = f"https://www.google.com/maps/embed/v1/place?key=YOUR_API_KEY&q={dest_q}" 
            # 註：若無 API Key，可沿用你先前的 iframe 格式，但標準 Google Maps 連結較穩
            map_url = f"https://maps.google.com/maps?q={dest_q}&hl=zh-TW&z=15&output=embed"
            components.html(f'<iframe width="100%" height="350" frameborder="0" src="{map_url}"></iframe>', height=360)
            
            # 導航按鈕
            if origin == "我的位置":
                nav_url = f"
