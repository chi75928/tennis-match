import streamlit as st
import pandas as pd
import os
import random
import json

# --- 1. 基礎設定與數據同步 ---
st.set_page_config(page_title="網球專業對撞與戰績系統", layout="wide")

TODAY_PLAYERS_FILE = "today_players.csv"
LINEUPS_FILE = "lineups_storage.csv"
CONFIG_FILE = "match_config.json"
RESULTS_FILE = "results_storage.csv" # 新增：存放比分

def save_config(match_list, team_codes, is_locked):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"match_list": match_list, "team_codes": team_codes, "is_locked": is_locked}, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    return {"match_list": [], "team_codes": {}, "is_locked": False}

config = load_config()
if 'match_list' not in st.session_state: st.session_state.match_list = config["match_list"]
if 'team_codes' not in st.session_state: st.session_state.team_codes = config["team_codes"]
if 'is_locked' not in st.session_state: st.session_state.is_locked = config["is_locked"]

@st.cache_data
def load_master_db():
    if os.path.exists('players.csv'): return pd.read_csv('players.csv')
    return pd.DataFrame(columns=['name', 'utr_s', 'utr_d', 'gender'])

master_df = load_master_db()

# --- 2. 側邊欄 ---
st.sidebar.title("🎾 賽事數據中心")
role = st.sidebar.selectbox("切換入口", ["隊長填單端", "總監管理端"])
admin_pwd = st.sidebar.text_input("管理員密碼", type="password")

# --- 3. 總監管理端 ---
if role == "總監管理端":
    if admin_pwd != "666":
        st.info("🔒 請輸入密碼解鎖後台")
    else:
        tab1, tab2 = st.tabs(["⚙️ 賽事設定", "🏆 戰績匯總榜"])
        
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("1. 名單與授權碼", expanded=True):
                    team_in = st.text_input("隊伍 (逗號隔開)", "A隊, B隊, C隊, D隊")
                    active_teams = [t.strip() for t in team_in.split(",")]
                    sel_players = st.multiselect("勾選今日選手", master_df['name'].tolist())
                    if st.button("生成名單與隨機密碼"):
                        today_df = master_df[master_df['name'].isin(sel_players)].copy()
                        today_df['team'] = "未分配"
                        today_df.to_csv(TODAY_PLAYERS_FILE, index=False)
                        st.session_state.team_codes = {t: str(random.randint(1000, 9999)) for t in active_teams}
                        save_config(st.session_state.match_list, st.session_state.team_codes, st.session_state.is_locked)
                        st.success("已生成！授權碼：" + str(st.session_state.team_codes))

            with col2:
                with st.expander("2. 項目與鎖定", expanded=True):
                    m_type = st.selectbox("新增項目", ["男單", "女单", "男双", "女双", "混双"])
                    if st.button("➕ 新增項目"):
                        st.session_state.match_list.append(m_type)
                        save_config(st.session_state.match_list, st.session_state.team_codes, st.session_state.is_locked)
                    
                    st.session_state.is_locked = st.toggle("🔒 鎖定隊長修改", value=st.session_state.is_locked)
                    if st.button("🗑️ 重置所有數據"):
                        for f in [LINEUPS_FILE, CONFIG_FILE, RESULTS_FILE]: 
                            if os.path.exists(f): os.remove(f)
                        st.rerun()

            if os.path.exists(TODAY_PLAYERS_FILE):
                with st.expander("3. 分配隊伍"):
                    curr_today = pd.read_csv(TODAY_PLAYERS_FILE)
                    updated = []
                    for idx, row in curr_today.iterrows():
                        t_idx = active_teams.index(row['team']) if row['team'] in active_teams else 0
                        new_t = st.selectbox(f"{row['name']}", active_teams, index=t_idx, key=f"t_{row['name']}")
                        updated.append([row['name'], row['utr_s'], row['utr_d'], row['gender'], new_t])
                    if st.button("💾 保存分配"):
                        pd.DataFrame(updated, columns=['name','utr_s','utr_d','gender','team']).to_csv(TODAY_PLAYERS_FILE, index=False)
                        st.success("分配已同步")

        with tab2:
            st.subheader("📊 隊伍積分大榜")
            if os.path.exists(RESULTS_FILE):
                res_df = pd.read_csv(RESULTS_FILE)
                # 簡單匯總邏輯：勝場、總局數
                summary = []
                all_teams = active_teams if 'active_teams' in locals() else res_df['team_a'].unique()
                for t in all_teams:
                    t_wins = len(res_df[res_df['winner'] == t])
                    t_challenges = len(res_df[(res_df['low_team'] == t) & (res_df['challenge'] == "成功")])
                    summary.append({"隊伍": t, "勝場數": t_wins, "挑戰成功": t_challenges})
                st.table(pd.DataFrame(summary))
            else:
                st.info("暫無比分數據，請先在下方「刷新對撞結果」處填寫比分。")

# --- 4. 隊長填單端 ---
elif role == "隊長填單端":
    st.header("📋 隊長排陣通道")
    cur_conf = load_config()
    if not os.path.exists(TODAY_PLAYERS_FILE) or not cur_conf["match_list"]:
        st.warning("總監尚未發布比賽項目。")
    else:
        today_df = pd.read_csv(TODAY_PLAYERS_FILE)
        my_t = st.selectbox("選擇隊伍", ["請選擇"] + today_df['team'].unique().tolist())
        pwd_in = st.text_input("授權碼", type="password")
        
        if my_t != "請選擇" and pwd_in == cur_conf["team_codes"].get(my_t):
            if cur_conf["is_locked"]: st.error("鎖定中，無法修改")
            else:
                with st.form(f"f_{my_t}"):
                    picks = []
                    for i, m in enumerate(cur_conf["match_list"]):
                        st.write(f"場次 {i+1}: {m}")
                        p_list = today_df[today_df['team'] == my_t]['name'].tolist()
                        c1, c2 = st.columns(2)
                        p1 = c1.selectbox("選手1", ["-"] + p_list, key=f"p1_{my_t}_{i}")
                        p2 = c2.selectbox("選手2", ["-"] + p_list, key=f"p2_{my_t}_{i}") if "双" in m else "-"
                        picks.append([my_t, i, m, p1, p2])
                    if st.form_submit_button("提交排陣"):
                        new_lineup = pd.DataFrame(picks, columns=['team','match_id','type','p1','p2'])
                        if os.path.exists(LINEUPS_FILE):
                            old = pd.read_csv(LINEUPS_FILE)
                            new_lineup = pd.concat([old[old['team'] != my_t], new_lineup])
                        new_lineup.to_csv(LINEUPS_FILE, index=False)
                        st.success("提交完成！")

# --- 5. 對撞結果與賽後報分 ---
st.divider()
if st.button("🚀 刷新對撞榜與報分單"):
    if os.path.exists(LINEUPS_FILE) and os.path.exists(TODAY_PLAYERS_FILE):
        all_l = pd.read_csv(LINEUPS_FILE)
        t_info = pd.read_csv(TODAY_PLAYERS_FILE)
        
        for mid in range(len(st.session_state.match_list)):
            m_type = st.session_state.match_list[mid]
            m_data = all_l[all_l['match_id'] == mid]
            if len(m_data) < 2: continue
            
            st.subheader(f"場次 {mid+1}：{m_type}")
            teams = m_data['team'].tolist()
            # 這裡簡化為前兩隊對撞
            t1, t2 = teams[0], teams[1]
            r1, r2 = m_data[m_data['team']==t1].iloc[0], m_data[m_data['team']==t2].iloc[0]
            
            u1 = t_info[t_info['name'].isin([r1['p1'], r1['p2']])]['utr_d' if "双" in m_type else 'utr_s'].mean()
            u2 = t_info[t_info['name'].isin([r2['p1'], r2['p2']])]['utr_d' if "双" in m_type else 'utr_s'].mean()
            diff = abs(u1 - u2)
            target = 5 if diff<=0.5 else 4 if diff<=1.0 else 3 if diff<=1.5 else 2 if diff<=2.0 else 1
            low_t = t1 if u1 < u2 else t2
            
            # 顯示對撞詳情
            st.info(f"【{t1} UTR:{u1:.2f}】 vs 【{t2} UTR:{u2:.2f}】 | 低分方【{low_t}】目標：{target} 局")
            
            # --- 賽後報分區 ---
            with st.expander(f"📝 輸入第 {mid+1} 場比分"):
                c1, c2, c3 = st.columns(3)
                score1 = c1.number_input(f"{t1} 局數", min_value=0, max_value=10, key=f"s1_{mid}")
                score2 = c2.number_input(f"{t2} 局數", min_value=0, max_value=10, key=f"s2_{mid}")
                if c3.button("儲存比分", key=f"btn_{mid}"):
                    winner = t1 if score1 > score2 else t2 if score2 > score1 else "平手"
                    # 判斷挑戰是否成功
                    low_score = score1 if low_t == t1 else score2
                    challenge = "成功" if low_score >= target else "失敗"
                    
                    res_row = pd.DataFrame([[mid, t1, t2, score1, score2, winner, low_t, target, challenge]], 
                                         columns=['mid','team_a','team_b','sc_a','sc_b','winner','low_team','target','challenge'])
                    if os.path.exists(RESULTS_FILE):
                        old_res = pd.read_csv(RESULTS_FILE)
                        res_row = pd.concat([old_res[old_res['mid'] != mid], res_row])
                    res_row.to_csv(RESULTS_FILE, index=False)
                    st.toast(f"場次 {mid+1} 比分已錄入！挑戰{challenge}")
            
            # 顯示已錄入的分數
            if os.path.exists(RESULTS_FILE):
                this_res = pd.read_csv(RESULTS_FILE)
                match_res = this_res[this_res['mid'] == mid]
                if not match_res.empty:
                    st.success(f"比分：{match_res.iloc[0]['sc_a']} : {match_res.iloc[0]['sc_b']} ({match_res.iloc[0]['challenge']})")
            st.divider()
