import streamlit as st
import pandas as pd
import os
import random
import json

# --- 1. 核心數據持久化邏輯 ---
st.set_page_config(page_title="網球專業對撞與戰績系統", layout="wide")

TODAY_PLAYERS_FILE = "today_players.csv"
LINEUPS_FILE = "lineups_storage.csv"
CONFIG_FILE = "match_config.json"
RESULTS_FILE = "results_storage.csv"

def save_config_to_file(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def load_config_from_file():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"match_list": [], "team_codes": {}, "is_locked": False}

# 初始化加載
current_config = load_config_from_file()

@st.cache_data
def load_master_db():
    if os.path.exists('players.csv'):
        return pd.read_csv( 'players.csv')
    return pd.DataFrame(columns=['name', 'utr_s', 'utr_d', 'gender'])

master_df = load_master_db()

# --- 2. 側邊欄入口 ---
st.sidebar.title("🎾 賽事數據中心")
role = st.sidebar.selectbox("切換入口", ["隊長填單端", "總監管理端"])
admin_pwd = st.sidebar.text_input("管理員密碼", type="password")

# --- 3. 總監管理端 ---
if role == "總監管理端":
    if admin_pwd != "666":
        st.info("🔒 請輸入管理員密碼")
    else:
        tab1, tab2 = st.tabs(["⚙️ 賽事設定與分配", "🏆 戰績匯總榜"])
        
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("1. 名單與授權碼 (固定密碼)", expanded=True):
                    team_in = st.text_input("隊伍名稱", "A隊, B隊, C隊, D隊")
                    active_teams = [t.strip() for t in team_in.split(",")]
                    sel_players = st.multiselect("勾選今日選手", master_df['name'].tolist())
                    
                    if st.button("✅ 建立名單並鎖定密碼"):
                        today_df = master_df[master_df['name'].isin(sel_players)].copy()
                        today_df['team'] = "未分配"
                        today_df.to_csv(TODAY_PLAYERS_FILE, index=False)
                        # 生成並「永久儲存」密碼
                        current_config["team_codes"] = {t: str(random.randint(1000, 9999)) for t in active_teams}
                        save_config_to_file(current_config)
                        st.rerun()

                # 密碼顯示區：只要檔案裡有密碼，就一直顯示
                if current_config["team_codes"]:
                    st.warning("🔑 隊長授權碼 (永久固定):")
                    st.json(current_config["team_codes"])

            with col2:
                with st.expander("2. 項目與鎖定控制", expanded=True):
                    m_type = st.selectbox("新增對撞項目", ["男單", "女单", "男双", "女双", "混双"])
                    if st.button("➕ 確認新增項目"):
                        current_config["match_list"].append(m_type)
                        save_config_to_file(current_config)
                        st.rerun()
                    
                    st.write("**📝 當前項目：**", current_config["match_list"])
                    
                    st.divider()
                    lock_state = st.toggle("🔒 鎖定隊長修改", value=current_config["is_locked"])
                    if lock_state != current_config["is_locked"]:
                        current_config["is_locked"] = lock_state
                        save_config_to_file(current_config)
                        st.rerun()

                    if st.button("🗑️ 重置所有比賽 (清空所有資料)"):
                        for f in [LINEUPS_FILE, CONFIG_FILE, RESULTS_FILE, TODAY_PLAYERS_FILE]:
                            if os.path.exists(f): os.remove(f)
                        st.rerun()

            if os.path.exists(TODAY_PLAYERS_FILE):
                st.subheader("3. 選手隊伍分配")
                curr_today = pd.read_csv(TODAY_PLAYERS_FILE)
                updated_rows = []
                current_teams = list(current_config["team_codes"].keys()) if current_config["team_codes"] else ["未分配"]
                
                with st.form("team_assignment_form"):
                    cols = st.columns(3)
                    for idx, row in curr_today.iterrows():
                        with cols[idx % 3]:
                            t_idx = current_teams.index(row['team']) if row['team'] in current_teams else 0
                            new_t = st.selectbox(f"{row['name']}", current_teams, index=t_idx, key=f"sel_{row['name']}")
                            updated_rows.append([row['name'], row['utr_s'], row['utr_d'], row['gender'], new_t])
                    
                    if st.form_submit_button("💾 儲存並送出隊伍分配", type="primary"):
                        pd.DataFrame(updated_rows, columns=['name','utr_s','utr_d','gender','team']).to_csv(TODAY_PLAYERS_FILE, index=False)
                        st.success("隊伍分配已存檔！")

        with tab2:
            st.subheader("📊 隊伍戰績統計")
            if os.path.exists(RESULTS_FILE):
                st.dataframe(pd.read_csv(RESULTS_FILE), use_container_width=True)
            else:
                st.info("暫無報分數據")

# --- 4. 隊長填單端 ---
elif role == "隊長填單端":
    st.header("📋 隊長填報系統")
    if not os.path.exists(TODAY_PLAYERS_FILE) or not current_config["match_list"]:
        st.warning("⏳ 等待總監設定中...")
    else:
        today_df = pd.read_csv(TODAY_PLAYERS_FILE)
        teams_list = [t for t in today_df['team'].unique().tolist() if t != "未分配"]
        my_t = st.selectbox("請選擇您的隊伍", ["請選擇"] + teams_list)
        pwd_in = st.text_input("輸入該隊 4 位授權碼", type="password")
        
        if my_t != "請選擇" and pwd_in == current_config["team_codes"].get(my_t):
            if current_config["is_locked"]:
                st.error("🔒 總監已鎖定，無法修改。")
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
                        st.success("提交成功！")

# --- 5. 對撞與穩定報分區 ---
st.divider()
if st.button("🧨 刷新對撞結果與報分介面"):
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

            # --- 關鍵修復：使用 FORM 穩定報分 ---
            with st.form(f"score_form_{mid}"):
                c1, c2 = st.columns(2)
                sc1 = c1.number_input(f"{t1} 局數", 0, 10, key=f"in1_{mid}")
                sc2 = c2.number_input(f"{t2} 局數", 0, 10, key=f"in2_{mid}")
                if st.form_submit_button("✅ 儲存此場比分"):
                    winner = t1 if sc1 > sc2 else t2 if sc2 > sc1 else "平"
                    low_sc = sc1 if low_t == t1 else sc2
                    challenge = "成功" if low_sc >= target else "失敗"
                    res_row = pd.DataFrame([[mid, m_label, t1, t2, sc1, sc2, winner, challenge]], 
                                         columns=['mid','type','t1','t2','s1','s2','winner','challenge'])
                    if os.path.exists(RESULTS_FILE):
                        old_res = pd.read_csv(RESULTS_FILE)
                        res_row = pd.concat([old_res[old_res['mid'] != mid], res_row])
                    res_row.to_csv(RESULTS_FILE, index=False)
                    st.success(f"已儲存！挑戰{challenge}")
            st.divider()
