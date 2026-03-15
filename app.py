import streamlit as st
import pandas as pd
import os

# --- 1. 基礎設定與數據加載 ---
st.set_page_config(page_title="網球專業點單對撞系統", layout="wide")

@st.cache_data
def load_master_db():
    # 讀取 800+ 人的大資料庫
    if os.path.exists('players.csv'):
        return pd.read_csv('players.csv')
    return pd.DataFrame(columns=['name', 'utr_s', 'utr_d', 'gender'])

# 定義運行時的臨時數據路徑
TODAY_PLAYERS_FILE = "today_players.csv"
LINEUPS_FILE = "lineups_storage.csv"

master_df = load_master_db()

# --- 2. 導航與權限 ---
st.sidebar.title("🎾 網球指揮中心")
role = st.sidebar.radio("身份切換", ["隊長填單入口", "總監管理中控"])
pwd = st.sidebar.text_input("輸入密碼", type="password")

# 初始化 session 狀態
if 'match_list' not in st.session_state:
    st.session_state.match_list = []

# --- 3. 總監管理中控邏輯 ---
if role == "總監管理中控":
    if pwd != "666":
        st.info("請輸入正確密碼以解鎖管理功能")
    else:
        st.header("🛠️ 賽事總監管理面板")
        
        # A. 建立今日名單
        with st.expander("第一步：設定今日參賽隊伍與名單"):
            team_input = st.text_input("輸入隊伍名稱（用逗號隔開）", "A隊, B隊, C隊, D隊")
            active_teams = [t.strip() for t in team_input.split(",")]
            
            selected_players = st.multiselect("從800人庫中勾選今日到場選手", master_df['name'].tolist())
            
            if st.button("確認並建立今日選手庫"):
                today_df = master_df[master_df['name'].isin(selected_players)].copy()
                today_df['team'] = "未分配"
                today_df.to_csv(TODAY_PLAYERS_FILE, index=False)
                st.success("今日選手庫已建立！")

        # B. 分配隊伍（確保隊長只能選自己的人）
        if os.path.exists(TODAY_PLAYERS_FILE):
            with st.expander("第二步：分配選手所屬隊伍"):
                current_today = pd.read_csv(TODAY_PLAYERS_FILE)
                updated_list = []
                for idx, row in current_today.iterrows():
                    # 預設選中已分配的隊伍
                    t_idx = active_teams.index(row['team']) if row['team'] in active_teams else 0
                    assigned_team = st.selectbox(f"選手: {row['name']}", active_teams, index=t_idx, key=f"assign_{row['name']}")
                    updated_list.append([row['name'], row['utr_s'], row['utr_d'], row['gender'], assigned_team])
                
                if st.button("確認隊伍分配並同步"):
                    pd.DataFrame(updated_list, columns=['name', 'utr_s', 'utr_d', 'gender', 'team']).to_csv(TODAY_PLAYERS_FILE, index=False)
                    st.success("隊伍同步完成！隊長端已更新。")

        # C. 發布比賽項目
        with st.expander("第三步：發布本輪對撞項目"):
            m_type = st.selectbox("新增項目", ["男單", "女单", "男双", "女双", "混双"])
            if st.button("➕ 新增到比賽表"):
                st.session_state.match_list.append(m_type)
            if st.button("🗑️ 清空所有項目"):
                st.session_state.match_list = []
                if os.path.exists(LINEUPS_FILE): os.remove(LINEUPS_FILE)
                st.rerun()
            st.write("目前項目:", st.session_state.match_list)

# --- 4. 隊長填單入口邏輯 ---
elif role == "隊長填單入口":
    st.header("📋 隊長填單通道")
    if not os.path.exists(TODAY_PLAYERS_FILE):
        st.warning("請聯繫總監，等待其發布今日參賽名單...")
    elif not st.session_state.match_list:
        st.info("總監尚未發布比賽項目，請稍候。")
    else:
        today_df = pd.read_csv(TODAY_PLAYERS_FILE)
        teams = today_df['team'].unique().tolist()
        my_team = st.selectbox("選擇您的隊伍", teams)
        
        # 過濾該隊專屬名單（15人以內）
        my_team_players = today_df[today_df['team'] == my_team]['name'].tolist()
        
        with st.form(f"form_{my_team}"):
            st.subheader(f"{my_team} 排陣表")
            current_submissions = []
            for i, m_label in enumerate(st.session_state.match_list):
                st.write(f"**第 {i+1} 場：{m_label}**")
                c1, c2 = st.columns(2)
                with c1:
                    p1 = st.selectbox("選手 1", ["-"] + my_team_players, key=f"p1_{my_team}_{i}")
                with c2:
                    p2 = st.selectbox("選手 2", ["-"] + my_team_players, key=f"p2_{my_team}_{i}") if "双" in m_label else "-"
                current_submissions.append([my_team, i, m_label, p1, p2])
            
            if st.form_submit_button("📢 提交排陣單"):
                new_data = pd.DataFrame(current_submissions, columns=['team', 'match_id', 'type', 'p1', 'p2'])
                if os.path.exists(LINEUPS_FILE):
                    all_lineups = pd.read_csv(LINEUPS_FILE)
                    all_lineups = all_lineups[all_lineups['team'] != my_team] # 覆蓋舊的
                    all_lineups = pd.concat([all_lineups, new_data])
                else:
                    all_lineups = new_data
                all_lineups.to_csv(LINEUPS_FILE, index=False)
                st.success("點單提交成功！請等待總監公布結果。")

# --- 5. 核心：對撞結果計算 ---
st.divider()
if st.button("🧨 顯示/刷新對撞結果"):
    if os.path.exists(LINEUPS_FILE) and os.path.exists(TODAY_PLAYERS_FILE):
        all_l = pd.read_csv(LINEUPS_FILE)
        t_info = pd.read_csv(TODAY_PLAYERS_FILE)
        
        st.header("⚡ 對撞結果大榜")
        
        for mid in range(len(st.session_state.match_list)):
            m_type = st.session_state.match_list[mid]
            m_data = all_l[all_l['match_id'] == mid]
            
            if len(m_data) < 2:
                st.write(f"--- 第 {mid+1} 場 ({m_type})：等待其他隊伍提交... ---")
                continue

            st.subheader(f"第 {mid+1} 場：{m_type}")
            
            # 這裡進行兩兩配對展示（如果多於2隊，系統會自動分組顯示）
            team_list = m_data['team'].tolist()
            
            # A隊 vs B隊 邏輯
            for k in range(0, len(team_list)-1, 2):
                t1, t2 = team_list[k], team_list[k+1]
                row1 = m_data[m_data['team'] == t1].iloc[0]
                row2 = m_data[m_data['team'] == t2].iloc[0]

                def calc_score(p1, p2, mt):
                    names = [n for n in [p1, p2] if n != "-"]
                    rows = t_info[t_info['name'].isin(names)]
                    sc = rows['utr_d' if "双" in mt else 'utr_s'].mean()
                    gd = rows['gender'].tolist()
                    return sc, gd, names

                s1, g1, n1 = calc_score(row1['p1'], row1['p2'], m_type)
                s2, g2, n2 = calc_score(row2['p1'], row2['p2'], m_type)
                
                diff = abs(s1 - s2)
                target = 5 if diff<=0.5 else 4 if diff<=1.0 else 3 if diff<=1.5 else 2 if diff<=2.0 else 1
                
                low_team = t1 if s1 < s2 else t2
                low_players = ", ".join(n1 if s1 < s2 else n2)

                # 顯示對撞卡片
                with st.container():
                    c_a, c_b, c_c = st.columns([2, 1, 2])
                    with c_a:
                        st.write(f"**{t1}**")
                        st.caption(f"選手: {', '.join(n1)}")
                        st.write(f"UTR: {s1:.2f}")
                    with c_b:
                        st.markdown(f"### VS")
                        st.caption(f"分差 {diff:.2f}")
                    with c_c:
                        st.write(f"**{t2}**")
                        st.caption(f"選手: {', '.join(n2)}")
                        st.write(f"UTR: {s2:.2f}")
                    
                    st.success(f"🎯 低分方【{low_team} ({low_players})】目標局數：{target} 局")
                    
                    if ("女" in g1 and "女" not in g2) or ("女" in g2 and "女" not in g1):
                        st.warning(f"💡 性別補償：若含女選手的 {low_team} 是低分方，建議目標額外 +1")
            st.divider()
    else:
        st.info("尚未有足夠的排陣數據進行對撞。")
