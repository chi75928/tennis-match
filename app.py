import streamlit as st
import pandas as pd
import os
import random
import json

# --- 1. 核心數據持久化與路徑 ---
st.set_page_config(page_title="網球專業對撞系統", layout="wide")

FILES = {
    "today": "today_players.csv",
    "lineups": "lineups_storage.csv",
    "config": "match_config.json",
    "results": "results_storage.csv"
}

def save_config(data):
    with open(FILES["config"], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def load_config():
    if os.path.exists(FILES["config"]):
        try:
            with open(FILES["config"], 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {
        "match_list": [], 
        "team_codes": {}, 
        "is_locked": False, 
        "teams_finalized": False, 
        "match_order": "", 
        "court_num": ""
    }

current_config = load_config()

# --- 數據加載修復 ---
@st.cache_data
def load_master_db():
    if os.path.exists('players.csv'):
        df = pd.read_csv('players.csv')
        df['utr_s'] = pd.to_numeric(df['utr_s'], errors='coerce').fillna(0.0)
        df['utr_d'] = pd.to_numeric(df['utr_d'], errors='coerce').fillna(0.0)
        return df
    return pd.DataFrame(columns=['name', 'utr_s', 'utr_d', 'gender'])

master_df = load_master_db()

# --- 2. 側邊欄入口 ---
st.sidebar.title("🎾 賽事管理終端")
role = st.sidebar.selectbox("切換入口", ["隊長填單端", "總監管理端"])
admin_pwd = st.sidebar.text_input("管理員密碼", type="password")

# --- 3. 總監管理端 ---
if role == "總監管理端":
    if admin_pwd != "666":
        st.info("🔒 請輸入管理員密碼")
    else:
        admin_tab = st.sidebar.radio("管理功能", ["1. 名單與對戰設定", "2. 比賽項目維護", "3. 戰績匯總"])
        
        if admin_tab == "1. 名單與對戰設定":
            st.header("👥 名單與分隊")
            allow_edit = st.checkbox("🔓 開啟修改模式", value=not current_config["teams_finalized"])
            
            c1, c2 = st.columns(2)
            with c1:
                with st.expander("基礎對戰設定", expanded=True):
                    team_in = st.text_input("隊伍名稱", "A隊, B隊, C隊, D隊", disabled=not allow_edit)
                    m_order = st.text_input("對戰順序", current_config["match_order"], disabled=not allow_edit)
                    c_num = st.text_input("場地號碼", current_config["court_num"], disabled=not allow_edit)
                    sel_p = st.multiselect("勾選今日選手", master_df['name'].tolist(), disabled=not allow_edit)
                    
                    if allow_edit and st.button("🚀 生成/更新密碼與名單"):
                        active_teams = [t.strip() for t in team_in.split(",")]
                        if not current_config["team_codes"]:
                            current_config["team_codes"] = {t: str(random.randint(1000, 9999)) for t in active_teams}
                        current_config.update({"match_order": m_order, "court_num": c_num})
                        save_config(current_config)
                        
                        today_df = master_df[master_df['name'].isin(sel_p)].copy()
                        today_df['team'] = "未分配"
                        today_df.to_csv(FILES["today"], index=False)
                        st.rerun()

                if current_config["team_codes"]:
                    st.warning(f"🔑 隊長密碼：{current_config['team_codes']}")

            with c2:
                if os.path.exists(FILES["today"]):
                    st.subheader("分配隊伍")
                    curr_today = pd.read_csv(FILES["today"])
                    teams = list(current_config["team_codes"].keys())
                    with st.form("assign_form"):
                        updated = []
                        for i, row in curr_today.iterrows():
                            t_idx = teams.index(row['team']) if row['team'] in teams else 0
                            nt = st.selectbox(f"{row['name']}", teams, index=t_idx, key=f"assign_{row['name']}", disabled=not allow_edit)
                            updated.append([row['name'], row['utr_s'], row['utr_d'], row['gender'], nt])
                        if st.form_submit_button("🔒 鎖定分隊名單"):
                            pd.DataFrame(updated, columns=['name','utr_s','utr_d','gender','team']).to_csv(FILES["today"], index=False)
                            current_config["teams_finalized"] = True
                            save_config(current_config)
                            st.rerun()

        elif admin_tab == "2. 比賽項目維護":
            st.header("🎾 項目清單")
            c1, c2 = st.columns(2)
            with c1:
                new_m = st.selectbox("新增項目", ["男單", "女单", "男双", "女双", "混双"])
                if st.button("➕ 新增項目"):
                    current_config["match_list"].append(new_m)
                    save_config(current_config)
                    st.rerun()
            with c2:
                for i, m in enumerate(current_config["match_list"]):
                    cc1, cc2 = st.columns([3, 1])
                    current_config["match_list"][i] = cc1.text_input(f"場次 {i+1}", m, key=f"m_{i}")
                    if cc2.button("🗑️", key=f"del_{i}"):
                        current_config["match_list"].pop(i)
                        save_config(current_config)
                        st.rerun()
            current_config["is_locked"] = st.toggle("🔒 禁止隊長修改", value=current_config["is_locked"])
            if st.button("保存鎖定"): save_config(current_config)

        elif admin_tab == "3. 戰績匯總":
            if os.path.exists(FILES["results"]): 
                st.dataframe(pd.read_csv(FILES["results"]), use_container_width=True)
            else: st.info("無數據")

# --- 4. 隊長端 ---
elif role == "隊長填單端":
    st.header("📋 隊長名單提交")
    if current_config["match_order"]:
        st.info(f"📌 今日對戰：{current_config['match_order']} | 場地：{current_config['court_num']}")
    
    if os.path.exists(FILES["today"]):
        today_df = pd.read_csv(FILES["today"])
        teams = list(current_config["team_codes"].keys())
        my_t = st.selectbox("選擇隊伍", ["-"] + teams)
        pwd = st.text_input("密碼", type="password")
        
        if my_t != "-" and pwd == current_config["team_codes"].get(my_t):
            if current_config["is_locked"]: st.error("鎖定中，無法修改")
            else:
                with st.form("cap_form"):
                    picks = []
                    my_ps = today_df[today_df['team'] == my_t]['name'].tolist()
                    for i, m_name in enumerate(current_config["match_list"]):
                        st.write(f"**場次 {i+1}：{m_name}**")
                        c1, c2 = st.columns(2)
                        p1 = c1.selectbox("選手 1", ["-"] + my_ps, key=f"p1_{i}")
                        p2 = c2.selectbox("選手 2", ["-"] + my_ps, key=f"p2_{i}") if "双" in m_name else "-"
                        picks.append([my_t, i, m_name, p1, p2])
                    if st.form_submit_button("📢 提交"):
                        df = pd.DataFrame(picks, columns=['team','match_id','type','p1','p2'])
                        if os.path.exists(FILES["lineups"]):
                            old = pd.read_csv(FILES["lineups"])
                            df = pd.concat([old[old['team'] != my_t], df])
                        df.to_csv(FILES["lineups"], index=False)
                        st.success("提交成功")

# --- 5. 對撞結果與報分區 ---
st.divider()
if st.button("🧨 刷新對撞與報分"):
    st.session_state.show_res = True

if st.session_state.get("show_res"):
    if os.path.exists(FILES["lineups"]) and os.path.exists(FILES["today"]):
        all_l, t_info = pd.read_csv(FILES["lineups"]), pd.read_csv(FILES["today"])
        for mid, m_label in enumerate(current_config["match_list"]):
            m_data = all_l[all_l['match_id'] == mid]
            if len(m_data) >= 2:
                st.subheader(f"場次 {mid+1}：{m_label}")
                t1, t2 = m_data['team'].iloc[0], m_data['team'].iloc[1]
                r1, r2 = m_data.iloc[0], m_data.iloc[1]
                
                u_col = 'utr_d' if "双" in m_label else 'utr_s'
                t_info[u_col] = pd.to_numeric(t_info[u_col], errors='coerce').fillna(0.0)
                
                u1 = t_info[t_info['name'].isin([r1['p1'], r1['p2']])][u_col].mean()
                u2 = t_info[t_info['name'].isin([r2['p1'], r2['p2']])][u_col].mean()
                
                diff = abs(u1 - u2)
                target = 5 if diff<=0.5 else 4 if diff<=1.0 else 3 if diff<=1.5 else 2 if diff<=2.0 else 1
                
                # 區分高低分方
                low_t, high_t = (t1, t2) if u1 < u2 else (t2, t1)

                col_l, col_m, col_r = st.columns([2, 1, 2])
                with col_l:
                    st.markdown(f"### {t1}")
                    p1_info = f"{r1['p1']}" + (f" / {r1['p2']}" if r1['p2'] != "-" else "")
                    st.success(f"👤 **{p1_info}**")
                    st.code(f"UTR: {u1:.2f}")
                with col_m:
                    st.markdown("<h2 style='text-align:center;'>VS</h2>", unsafe_allow_html=True)
                with col_r:
                    st.markdown(f"### {t2}")
                    p2_info = f"{r2['p1']}" + (f" / {r2['p2']}" if r2['p2'] != "-" else "")
                    st.success(f"👤 **{p2_info}**")
                    st.code(f"UTR: {u2:.2f}")

                st.warning(f"🎯 低分方【{low_t}】目標拿到 **{target}** 局挑戰成功")

                with st.form(f"f_{mid}"):
                    c1, c2 = st.columns(2)
                    s1 = c1.number_input(f"{t1} 局數", 0, 10, key=f"s1_{mid}")
                    s2 = c2.number_input(f"{t2} 局數", 0, 10, key=f"s2_{mid}")
                    if st.form_submit_button("💾 儲存比分"):
                        win_actual = t1 if s1 > s2 else t2 if s2 > s1 else "平"
                        low_score = s1 if low_t == t1 else s2
                        
                        # --- 修改後的 Challenge 邏輯 ---
                        # 挑戰成功顯示低分方名稱，失敗顯示高分方名稱
                        challenge_winner = low_t if low_score >= target else high_t
                        
                        res = pd.DataFrame([[mid+1, m_label, t1, t2, s1, s2, win_actual, challenge_winner]], 
                                         columns=['mid','type','t1','t2','s1','s2','winner','challenge'])
                        
                        if os.path.exists(FILES["results"]):
                            old_res = pd.read_csv(FILES["results"])
                            res = pd.concat([old_res[old_res['mid'] != (mid+1)], res])
                        res.to_csv(FILES["results"], index=False)
                        st.success(f"存檔成功！本場挑戰結果：{challenge_winner}")
                st.divider()
