import streamlit as st
import pandas as pd
import os
import random

# --- 1. 基礎設定與環境初始化 ---
st.set_page_config(page_title="網球賽事進化版-對撞系統", layout="wide")

# 初始化 Session State
if 'match_list' not in st.session_state:
    st.session_state.match_list = []
if 'team_codes' not in st.session_state:
    st.session_state.team_codes = {}
if 'is_locked' not in st.session_state:
    st.session_state.is_locked = False

@st.cache_data
def load_master_db():
    if os.path.exists('players.csv'):
        return pd.read_csv('players.csv')
    return pd.DataFrame(columns=['name', 'utr_s', 'utr_d', 'gender'])

TODAY_PLAYERS_FILE = "today_players.csv"
LINEUPS_FILE = "lineups_storage.csv"
master_df = load_master_db()

# --- 2. 側邊欄導航 ---
st.sidebar.title("🎾 專業對撞中控台")
role = st.sidebar.selectbox("身分入口", ["隊長填單入口", "總監管理後台"])
admin_pwd = st.sidebar.text_input("後台管理密碼", type="password")

# --- 3. 總監管理後台邏輯 ---
if role == "總監管理後台":
    if admin_pwd != "666":
        st.info("請在左側輸入管理員密碼以進入後台。")
    else:
        st.header("🛠️ 賽事總監管理中控")
        
        col1, col2 = st.columns(2)
        with col1:
            # A. 建立參賽名單
            with st.expander("第一步：設定參賽隊伍與名單", expanded=True):
                team_input = st.text_input("隊伍名稱 (用逗號隔開)", "A隊, B隊, C隊, D隊")
                active_teams = [t.strip() for t in team_input.split(",")]
                
                selected_players = st.multiselect("從800人庫中挑選今日選手", master_df['name'].tolist())
                
                if st.button("確認建立今日名單並生成密碼"):
                    today_df = master_df[master_df['name'].isin(selected_players)].copy()
                    today_df['team'] = "未分配"
                    today_df.to_csv(TODAY_PLAYERS_FILE, index=False)
                    # 為每個隊伍生成隨機 4 位密碼
                    st.session_state.team_codes = {t: str(random.randint(1000, 9999)) for t in active_teams}
                    st.success("選手庫已建立！請將下方授權碼發給各隊隊長。")

            # B. 展示授權碼
            if st.session_state.team_codes:
                st.warning("🔑 隊長授權碼 (請私發隊長):")
                st.write(st.session_state.team_codes)

        with col2:
            # C. 設定比賽項目與鎖定
            with st.expander("第二步：發布項目與鎖定控制", expanded=True):
                m_type = st.selectbox("新增對撞項目", ["男單", "女单", "男双", "女双", "混双"])
                if st.button("➕ 新增項目"):
                    st.session_state.match_list.append(m_type)
                
                if st.button("🗑️ 重置全部賽事"):
                    st.session_state.match_list = []
                    st.session_state.is_locked = False
                    if os.path.exists(LINEUPS_FILE): os.remove(LINEUPS_FILE)
                    st.rerun()
                
                st.divider()
                st.session_state.is_locked = st.toggle("🔒 全局填單鎖定 (鎖定後隊長無法修改)", value=st.session_state.is_locked)

        # D. 分配選手隊伍
        if os.path.exists(TODAY_PLAYERS_FILE):
            with st.expander("第三步：分配選手到隊伍"):
                current_today = pd.read_csv(TODAY_PLAYERS_FILE)
                updated_list = []
                for idx, row in current_today.iterrows():
                    # 動態生成下拉選單
                    t_idx = active_teams.index(row['team']) if row['team'] in active_teams else 0
                    assigned_team = st.selectbox(f"選手: {row['name']}", active_teams, index=t_idx, key=f"assign_{row['name']}")
                    updated_list.append([row['name'], row['utr_s'], row['utr_d'], row['gender'], assigned_team])
                
                if st.button("保存分配結果"):
                    pd.DataFrame(updated_list, columns=['name', 'utr_s', 'utr_d', 'gender', 'team']).to_csv(TODAY_PLAYERS_FILE, index=False)
                    st.success("隊伍同步完成！")

# --- 4. 隊長填單入口邏輯 ---
elif role == "隊長填單入口":
    st.header("📋 隊長填報系統")
    
    if not os.path.exists(TODAY_PLAYERS_FILE):
        st.warning("總監尚未建立名單，請聯繫總監。")
    elif not st.session_state.match_list:
        st.info("目前無對撞項目。")
    else:
        today_df = pd.read_csv(TODAY_PLAYERS_FILE)
        teams_list = today_df['team'].unique().tolist()
        
        # 隊伍與授權驗證
        selected_team = st.selectbox("請選擇您的隊伍", ["請選擇"] + teams_list)
        code_input = st.text_input("輸入該隊 4 位授權碼", type="password")
        
        if selected_team != "請選擇":
            correct_code = st.session_state.team_codes.get(selected_team)
            if code_input != correct_code:
                st.error("授權碼錯誤，無法開啟排陣單。")
            elif st.session_state.is_locked:
                st.error("⛔ 總監已鎖定填報，目前僅供查看，無法修改。")
                # 唯讀顯示已提交數據（略）
            else:
                st.success(f"驗證通過，請填寫 {selected_team} 排陣：")
                my_players = today_df[today_df['team'] == selected_team]['name'].tolist()
                
                with st.form(f"form_{selected_team}"):
                    submissions = []
                    for i, m_label in enumerate(st.session_state.match_list):
                        st.write(f"**第 {i+1} 場：{m_label}**")
                        c1, c2 = st.columns(2)
                        with c1:
                            p1 = st.selectbox("選手 1", ["-"] + my_players, key=f"p1_{selected_team}_{i}")
                        with c2:
                            p2 = st.selectbox("選手 2", ["-"] + my_players, key=f"p2_{selected_team}_{i}") if "双" in m_label else "-"
                        submissions.append([selected_team, i, m_label, p1, p2])
                    
                    if st.form_submit_button("📢 提交排陣單"):
                        new_data = pd.DataFrame(submissions, columns=['team', 'match_id', 'type', 'p1', 'p2'])
                        if os.path.exists(LINEUPS_FILE):
                            all_lineups = pd.read_csv(LINEUPS_FILE)
                            all_lineups = all_lineups[all_lineups['team'] != selected_team]
                            all_lineups = pd.concat([all_lineups, new_data])
                        else:
                            all_lineups = new_data
                        all_lineups.to_csv(LINEUPS_FILE, index=False)
                        st.balloons()
                        st.success("提交成功！")

# --- 5. 對撞與戰略分析 ---
st.divider()
if st.button("🚀 刷新對撞結果與局數計算"):
    if os.path.exists(LINEUPS_FILE) and os.path.exists(TODAY_PLAYERS_FILE):
        all_l = pd.read_csv(LINEUPS_FILE)
        t_info = pd.read_csv(TODAY_PLAYERS_FILE)
        
        st.header("💥 最終對撞榜單")
        
        for mid in range(len(st.session_state.match_list)):
            m_type = st.session_state.match_list[mid]
            m_data = all_l[all_l['match_id'] == mid]
            
            if len(m_data) < 2:
                st.info(f"第 {mid+1} 場 ({m_type}): 等待兩隊提交後顯示對撞...")
                continue

            st.subheader(f"場次 {mid+1}：{m_type}")
            
            # 對撞分組顯示 (假設兩兩對抗)
            teams = m_data['team'].tolist()
            for k in range(0, len(teams)-1, 2):
                t1, t2 = teams[k], teams[k+1]
                r1 = m_data[m_data['team'] == t1].iloc[0]
                r2 = m_data[m_data['team'] == t2].iloc[0]

                def get_stats(names, mt):
                    active_n = [n for n in names if n != "-"]
                    rows = t_info[t_info['name'].isin(active_n)]
                    avg_utr = rows['utr_d' if "双" in mt else 'utr_s'].mean()
                    genders = rows['gender'].tolist()
                    return avg_utr, genders, active_n

                u1, g1, n1 = get_stats([r1['p1'], r1['p2']], m_type)
                u2, g2, n2 = get_stats([r2['p1'], r2['p2']], m_type)
                
                diff = abs(u1 - u2)
                # 穩健型目標算法
                target = 5 if diff<=0.5 else 4 if diff<=1.0 else 3 if diff<=1.5 else 2 if diff<=2.0 else 1
                
                with st.container():
                    col_a, col_vs, col_b = st.columns([2, 1, 2])
                    with col_a:
                        st.markdown(f"**{t1}**")
                        st.caption(f"{', '.join(n1)}")
                        st.write(f"平均 UTR: {u1:.2f}")
                    with col_vs:
                        st.markdown("### VS")
                    with col_b:
                        st.markdown(f"**{t2}**")
                        st.caption(f"{', '.join(n2)}")
                        st.write(f"平均 UTR: {u2:.2f}")
                    
                    low_t = t1 if u1 < u2 else t2
                    st.info(f"⚖️ 低分方【{low_t}】目標局數：{target} 局 (分差:{diff:.2f})")
            st.divider()
    else:
        st.info("數據準備中，請等待隊長完成提交。")
