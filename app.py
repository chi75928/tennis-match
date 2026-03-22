import streamlit as st
import pandas as pd
import os
import random
import json

# --- 1. 初始化與數據持久化 ---
st.set_page_config(page_title="網球專業對撞系統", layout="wide")

TODAY_PLAYERS_FILE = "today_players.csv"
LINEUPS_FILE = "lineups_storage.csv"
CONFIG_FILE = "match_config.json"
RESULTS_FILE = "results_storage.csv"

def save_config(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"match_list": [], "team_codes": {}, "is_locked": False, "teams_finalized": False}

current_config = load_config()

@st.cache_data
def load_master_db():
    if os.path.exists('players.csv'):
        return pd.read_csv('players.csv')
    return pd.DataFrame(columns=['name', 'utr_s', 'utr_d', 'gender'])

master_df = load_master_db()

# --- 2. 側邊欄與權限 ---
st.sidebar.title("🎾 賽事控制台")
role = st.sidebar.selectbox("切換入口", ["隊長填單端", "總監管理端"])
admin_pwd = st.sidebar.text_input("管理員密碼", type="password")

# --- 3. 總監管理端 (核心修改區) ---
if role == "總監管理端":
    if admin_pwd != "666":
        st.info("🔒 請輸入管理員密碼進入管理模式")
    else:
        # 使用 Radio 按鈕作為左側分頁導航，讓邏輯更清晰
        admin_page = st.sidebar.radio("管理分頁", ["1. 隊伍名單與授權", "2. 比賽項目設定", "3. 戰績統計回報"])
        
        # --- 分頁 1：名單與授權 ---
        if admin_page == "1. 隊伍名單與授權":
            st.header("👥 隊伍名單與授權管理")
            
            # 狀態檢查：如果已鎖定，則顯示唯讀狀態
            is_team_locked = current_config.get("teams_finalized", False)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader("第一步：設定隊伍與選手")
                team_in = st.text_input("隊伍名稱 (逗號隔開)", "A隊, B隊, C隊, D隊", disabled=is_team_locked)
                active_teams = [t.strip() for t in team_in.split(",")]
                sel_players = st.multiselect("勾選今日參賽選手", master_df['name'].tolist(), disabled=is_team_locked)
                
                if not is_team_locked:
                    if st.button("🚀 生成名單並鎖定密碼", type="primary"):
                        today_df = master_df[master_df['name'].isin(sel_players)].copy()
                        today_df['team'] = "未分配"
                        today_df.to_csv(TODAY_PLAYERS_FILE, index=False)
                        # 生成永久密碼
                        current_config["team_codes"] = {t: str(random.randint(1000, 9999)) for t in active_teams}
                        save_config(current_config)
                        st.success("名單初始化成功！請在右側分配隊伍。")
                        st.rerun()
                else:
                    st.warning("⚠️ 隊伍名單已鎖定。如需重新分配，請點擊下方的重置。")

                if current_config["team_codes"]:
                    st.info("🔑 隊長授權碼 (發放給隊長):")
                    st.json(current_config["team_codes"])

            with col2:
                st.subheader("第二步：分配隊伍")
                if os.path.exists(TODAY_PLAYERS_FILE):
                    curr_today = pd.read_csv(TODAY_PLAYERS_FILE)
                    current_teams = list(current_config["team_codes"].keys())
                    
                    with st.form("team_assignment_form"):
                        updated_rows = []
                        cols = st.columns(2)
                        for idx, row in curr_today.iterrows():
                            with cols[idx % 2]:
                                t_idx = current_teams.index(row['team']) if row['team'] in current_teams else 0
                                new_t = st.selectbox(f"選手: {row['name']}", current_teams, index=t_idx, key=f"sel_{row['name']}", disabled=is_team_locked)
                                updated_rows.append([row['name'], row['utr_s'], row['utr_d'], row['gender'], new_t])
                        
                        if not is_team_locked:
                            if st.form_submit_button("🔒 確認分配並鎖定隊伍"):
                                pd.DataFrame(updated_rows, columns=['name','utr_s','utr_d','gender','team']).to_csv(TODAY_PLAYERS_FILE, index=False)
                                current_config["teams_finalized"] = True
                                save_config(current_config)
                                st.success("隊伍已正式鎖定！")
                                st.rerun()
                        else:
                            st.form_submit_button("隊伍已鎖定", disabled=True)
                else:
                    st.write("請先在左側建立名單。")

            st.divider()
            if st.button("🚨 重置所有數據 (慎用)"):
                for f in [LINEUPS_FILE, CONFIG_FILE, RESULTS_FILE, TODAY_PLAYERS_FILE]:
                    if os.path.exists(f): os.remove(f)
                st.rerun()

        # --- 分頁 2：比賽項目設定 ---
        elif admin_page == "2. 比賽項目設定":
            st.header("🎾 比賽項目與鎖定控制")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("新增對戰項目")
                m_type = st.selectbox("選擇項目", ["男單", "女单", "男双", "女双", "混双"])
                if st.button("➕ 點擊新增至列表"):
                    current_config["match_list"].append(m_type)
                    save_config(current_config)
                    st.success(f"已新增 {m_type}")
                    st.rerun()

            with col2:
                st.subheader("當前已發布項目")
                if not current_config["match_list"]:
                    st.write("尚未設定項目")
                else:
                    # 使用清單顯示，不提供修改/刪除按鈕以符合「放上去不能修改」的需求
                    for i, m in enumerate(current_config["match_list"]):
                        st.code(f"場次 {i+1}: {m}")
                    st.caption("ℹ️ 項目一旦新增即固定，如需更改請使用重置功能。")
            
            st.divider()
            st.subheader("填單狀態控制")
            lock_state = st.toggle("🔒 禁止隊長修改名單 (正式比賽開始時開啟)", value=current_config["is_locked"])
            if lock_state != current_config["is_locked"]:
                current_config["is_locked"] = lock_state
                save_config(current_config)
                st.rerun()

        # --- 分頁 3：戰績統計 ---
        elif admin_page == "3. 戰績統計回報":
            st.header("🏆 戰績匯總榜")
            if os.path.exists(RESULTS_FILE):
                res_df = pd.read_csv(RESULTS_FILE)
                st.dataframe(res_df, use_container_width=True)
                
                # 簡單統計
                st.subheader("隊伍勝場統計")
                win_counts = res_df['winner'].value_counts()
                st.bar_chart(win_counts)
            else:
                st.info("目前尚無比賽報分數據。")

# --- 4. 隊長填單端 (邏輯保持穩定) ---
elif role == "隊長填單端":
    st.header("📋 隊長填報系統")
    if not os.path.exists(TODAY_PLAYERS_FILE) or not current_config["match_list"]:
        st.warning("⏳ 總監尚未完成初始設定或未發布項目。")
    else:
        today_df = pd.read_csv(TODAY_PLAYERS_FILE)
        teams_list = list(current_config["team_codes"].keys())
        my_t = st.selectbox("請選擇您的隊伍", ["請選擇"] + teams_list)
        pwd_in = st.text_input("輸入 4 位授權碼", type="password")
        
        if my_t != "請選擇" and pwd_in == current_config["team_codes"].get(my_t):
            if current_config["is_locked"]:
                st.error("🔒 比賽已鎖定，目前禁止修改名單。")
            else:
                with st.form(f"form_{my_t}"):
                    picks = []
                    my_players = today_df[today_df['team'] == my_t]['name'].tolist()
                    for i, m_label in enumerate(current_config["match_list"]):
                        st.write(f"**第 {i+1} 場：{m_label}**")
                        c1, c2 = st.columns(2)
                        p1 = c1.selectbox("選手 1", ["-"] + my_players, key=f"p1_{my_t}_{i}")
                        p2 = c2.selectbox("選手 2", ["-"] + my_players, key=f"p2_{my_t}_{i}") if "双" in m_label else "-"
                        picks.append([my_t, i, m_label, p1, p2])
                    if st.form_submit_button("📢 提交本輪點單"):
                        new_lineup = pd.DataFrame(picks, columns=['team','match_id','type','p1','p2'])
                        if os.path.exists(LINEUPS_FILE):
                            old = pd.read_csv(LINEUPS_FILE)
                            new_lineup = pd.concat([old[old['team'] != my_t], new_lineup])
                        new_lineup.to_csv(LINEUPS_FILE, index=False)
                        st.success("名單提交成功！")

# --- 5. 對撞結果刷新區 ---
if role == "總監管理端":
    st.divider()
    if st.button("🧨 進入對撞比分介面"):
        st.session_state.show_results = True

    if st.session_state.get("show_results"):
        if os.path.exists(LINEUPS_FILE) and os.path.exists(TODAY_PLAYERS_FILE):
            all_l, t_info = pd.read_csv(LINEUPS_FILE), pd.read_csv(TODAY_PLAYERS_FILE)
            
            for mid, m_label in enumerate(current_config["match_list"]):
                m_data = all_l[all_l['match_id'] == mid]
                if len(m_data) < 2: continue
                
                st.subheader(f"場次 {mid+1}：{m_label}")
                t1, t2 = m_data['team'].tolist()[0], m_data['team'].tolist()[1]
                r1, r2 = m_data[m_data['team']==t1].iloc[0], m_data[m_data['team']==t2].iloc[0]
                
                u1 = t_info[t_info['name'].isin([r1['p1'], r1['p2']])]['utr_d' if "双" in m_label else 'utr_s'].mean()
                u2 = t_info[t_info['name'].isin([r2['p1'], r2['p2']])]['utr_d' if "双" in m_label else 'utr_s'].mean()
                diff = abs(u1 - u2)
                target = 5 if diff<=0.5 else 4 if diff<=1.0 else 3 if diff<=1.5 else 2 if diff<=2.0 else 1
                low_t = t1 if u1 < u2 else t2

                st.write(f"【{t1}: {u1:.2f}】 vs 【{t2}: {u2:.2f}】 | 🎯 低分方【{low_t}】目標 {target} 局")

                with st.form(f"score_form_{mid}"):
                    c1, c2 = st.columns(2)
                    sc1 = c1.number_input(f"{t1} 局數", 0, 10, key=f"in1_{mid}")
                    sc2 = c2.number_input(f"{t2} 局數", 0, 10, key=f"in2_{mid}")
                    if st.form_submit_button(f"✅ 儲存第 {mid+1} 場比分"):
                        winner = t1 if sc1 > sc2 else t2 if sc2 > sc1 else "平"
                        low_sc = sc1 if low_t == t1 else sc2
                        challenge = "成功" if low_sc >= target else "失敗"
                        res_row = pd.DataFrame([[mid, m_label, t1, t2, sc1, sc2, winner, challenge]], 
                                             columns=['mid','type','t1','t2','s1','s2','winner','challenge'])
                        if os.path.exists(RESULTS_FILE):
                            old_res = pd.read_csv(RESULTS_FILE)
                            res_row = pd.concat([old_res[old_res['mid'] != mid], res_row])
                        res_row.to_csv(RESULTS_FILE, index=False)
                        st.success(f"比分已存檔！挑戰結果：{challenge}")
                st.divider()
