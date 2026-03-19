import streamlit as st
import pandas as pd
import os
import json

# --- 1. 數據初始化 ---
PLAYER_FILE = "players_v3.csv"

# 如果是第一次測試，建立 800 位虛擬會員數據
if not os.path.exists(PLAYER_FILE):
    data = {
        'name': [f"選手_{i}" for i in range(1, 801)],
        'email': [f"user{i}@example.com" for i in range(1, 801)], # 用於搜索 UTR
        'utr_s': [round(2.0 + (i % 10), 2) for i in range(800)],
        'utr_d': [round(2.1 + (i % 10), 2) for i in range(800)],
        'region': [["上海", "北京", "廣州"][i % 3] for i in range(800)],
        'club': ["無"] * 800,
        'prestige': [0.0] * 800  # 選手對俱樂部的貢獻值
    }
    pd.DataFrame(data).to_csv(PLAYER_FILE, index=False)

def load_data(): return pd.read_csv(PLAYER_FILE)
def save_data(df): df.to_csv(PLAYER_FILE, index=False)

# 模擬回歸紀錄 (實務上存於數據庫)
if 'rejoin_log' not in st.session_state:
    st.session_state.rejoin_log = {} # {email: {club_name: count}}

# --- 2. 介面佈局 ---
st.title("🎾 MP Tennis 賽事邏輯實驗室 2.0")
st.sidebar.header("功能測試區")
mode = st.sidebar.radio("選擇測試模塊", ["🔍 郵箱登入與搜索", "🏆 地區實力榜", "🛡️ 俱樂部與聲望折扣", "⚔️ 團體對撞補償"])

# --- 3. 邏輯 A：郵箱搜索 UTR ---
if mode == "🔍 郵箱登入與搜索":
    st.header("🔑 微信登入 - 郵箱關聯 UTR")
    email_input = st.text_input("輸入 UTR 註冊郵箱進行搜索")
    df = load_data()
    
    if email_input:
        user_row = df[df['email'] == email_input]
        if not user_row.empty:
            u = user_row.iloc[0]
            st.success(f"✅ 找到選手：{u['name']}")
            st.metric("當前 UTR (單打)", u['utr_s'])
            st.write(f"所屬地區：{u['region']} | 當前俱樂部：{u['club']}")
        else:
            st.error("❌ 找不到該郵箱對應的 UTR 數據，請聯繫管理員。")

# --- 4. 邏輯 B：地區實力榜 ---
elif mode == "🏆 地區實力榜":
    st.header("🌏 地區 UTR 純實力排名")
    df = load_data()
    selected_reg = st.selectbox("選擇地區", df['region'].unique())
    
    # 僅按 UTR 排序
    rank_df = df[df['region'] == selected_reg].sort_values(by='utr_s', ascending=False).reset_index(drop=True)
    rank_df.index += 1
    st.table(rank_df[['name', 'utr_s', 'club']].head(20))

# --- 5. 邏輯 C：俱樂部聲望 (歸零與折扣) ---
elif mode == "🛡️ 俱樂部與聲望折扣":
    st.header("🛡️ 俱樂部聲望重置測試")
    df = load_data()
    target_p = st.selectbox("選擇測試選手", df['name'].tolist())
    p_info = df[df['name'] == target_p].iloc[0]
    p_email = p_info['email']
    
    st.write(f"目前俱樂部：**{p_info['club']}** | 貢獻值：{p_info['prestige']}")
    
    new_club = st.selectbox("變更至新俱樂部", ["無", "海德社", "威爾森隊"])
    
    if st.button("執行轉會"):
        # 1. 舊聲望歸零邏輯
        df.loc[df['name'] == target_p, 'prestige'] = 0.0
        
        # 2. 回歸折扣邏輯
        ratio = 1.0
        if p_email in st.session_state.rejoin_log and new_club in st.session_state.rejoin_log[p_email]:
            count = st.session_state.rejoin_log[p_email][new_club]
            ratio = 0.5 if count == 1 else 0.33
            st.warning(f"⚠️ 偵測到第 {count+1} 次加入該部，聲望恢復比例：{int(ratio*100)}%")
            st.session_state.rejoin_log[p_email][new_club] += 1
        else:
            if p_email not in st.session_state.rejoin_log: st.session_state.rejoin_log[p_email] = {}
            st.session_state.rejoin_log[p_email][new_club] = 1
            
        df.loc[df['name'] == target_p, 'club'] = new_club
        df.loc[df['name'] == target_p, 'prestige'] = 100.0 * ratio # 假設基礎貢獻 100
        save_data(df)
        st.success("轉會完成，數據已更新。")

# --- 6. 邏輯 D：團體對撞補償 ---
elif mode == "⚔️ 團體對撞補償":
    st.header("⚔️ 團體趣味賽 - 對撞邏輯")
    u1 = st.number_input("隊伍 A 平均 UTR", 2.0, 13.0, 8.0)
    u2 = st.number_input("隊伍 B 平均 UTR", 2.0, 13.0, 6.5)
    
    diff = abs(u1 - u2)
    # 延用您的對撞公式
    if diff <= 0.5: target = 5
    elif diff <= 1.0: target = 4
    elif diff <= 1.5: target = 3
    elif diff <= 2.0: target = 2
    else: target = 1
    
    st.divider()
    st.subheader(f"對撞結果：差值 {diff:.2f}")
    st.success(f"🎯 低分方目標局數：{target} 局")
