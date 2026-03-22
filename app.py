import streamlit as st
import pandas as pd
import os
import random
import json

# --- 1. 核心設定與數據持久化 ---
st.set_page_config(page_title="網球專業對撞系統 v2", layout="wide")

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
        "match_order": "", # 新增：對戰順序
        "court_num": ""    # 新增：場地號碼
    }

current_config = load_config()

@st.cache_data
def load_master_db():
    if os.path.exists('players.csv'):
        return pd.read_csv('players.csv')
    return pd.DataFrame(columns=['name', 'utr_s', 'utr_d', 'gender'])

master_df = load_master_db()

# --- 2. 側邊欄與權限 ---
st.sidebar.title("🎾 賽事管理終端")
role = st.sidebar.selectbox("切換入口", ["隊長填單端", "總監管理端"])
admin_pwd = st.sidebar.text_input("管理員密碼", type="password")

# --- 3. 總監管理端 ---
if role == "總監管理端":
    if admin_pwd != "666":
        st.info("🔒 請輸入管理員密碼進入管理模式")
    else:
        admin_page = st.sidebar.radio("管理功能分頁", ["1. 隊伍名單與對戰設定", "2. 比賽項目維護", "3. 戰績統計回報"])
        
        # --- 分頁 1：名單與對戰設定 ---
        if admin_page == "1. 隊伍名單與對戰設定":
            st.header("👥 隊伍名單與對戰順序")
            
            # 靈活鎖定控制
            is_team_locked = current_config.get("teams_finalized", False)
            allow_edit = st.checkbox("🔓 開啟修改模式 (解鎖名單與對戰設定)", value=not is_team_locked)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader("第一步：基礎設定")
                team_in = st.text_input("隊伍名稱", "A隊, B隊, C隊, D隊", disabled=not allow_edit)
                m_order = st.text_input("今日對戰順序 (例如: A vs B, C vs D)", current_config.get("match_order", ""), disabled=not allow_edit)
                c_num = st.text_input("比賽場地號碼", current_config.get("court_num", ""), disabled=not allow_edit)
                
                sel_players = st.multiselect("勾選今日參賽選手", master_df['name'].tolist(), disabled=not allow_edit)
                
                if allow_edit and st.button("🚀 更新基礎設定與密碼"):
                    active_teams = [t.strip() for t in team_in.split(",")]
                    # 只有在沒密碼時才生成新密碼，避免誤點導致原密碼失效
                    if not current_config["team_codes"]:
                        current_config["team_codes"] = {t: str(random.randint(1000, 9999)) for t in active_teams}
                    
                    current_config["match_order"] = m_order
                    current_config["court_num"] = c_num
                    save_config(current_config)
                    
                    # 處理選手名單
                    if sel_players:
                        today_df = master_df[master_df['name'].isin(sel_players)].copy()
                        if os.path.exists(FILES["today"]):
                            old_today = pd.read_csv(FILES["today"])
                            today_df = pd.merge(today_df, old_today[['name', 'team']], on='name', how='left').fillna("未分配")
                        else:
                            today_df['team'] = "未分配"
                        today_df.to_csv(FILES["today"], index=False)
                    
                    st.success("設定已更新！")
                    st.rerun()

                if current_config["team_codes"]:
                    st.warning(f"🔑 授權碼: {current_config['team_codes']}")

            with col2:
                st.subheader("第二步：人員分隊")
                if os.path.exists(FILES["today"]):
                    curr_today = pd.read_csv(FILES["today"])
                    current_teams = list(current_config["team_codes"].keys())
                    
                    with st.form("team_assignment_form"):
                        updated_rows = []
                        cols = st.columns(2)
                        for idx, row in curr_today.iterrows():
                            with cols[idx % 2]:
                                t_idx = current_teams.index(row['team']) if row['team'] in current_teams else 0
                                new_t = st.selectbox(f"選手: {row['name']}", current_teams, index=t_idx, key=f"sel_{row['name']}", disabled=not allow_edit)
                                updated_rows.append([row['name'], row['utr_s'], row['utr_d'], row['gender'], new_t])
                        
                        if st.form_submit_button("💾 儲存分隊名單"):
                            pd.DataFrame(updated_rows, columns=['name','utr_s','utr_d','gender','team']).to_csv(FILES["today"], index=False)
                            current_config["teams_finalized"] = True
                            save_config(current_config)
                            st.success("分隊已儲存！")
                            st.rerun()
                
                # 顯示當前對戰資訊
                st.info(f"📌 當前安排：{current_config.get('match_order')} | 🏟 場地：{current_config.get('court_num')}")

        # --- 分頁 2：比賽項目維護 ---
        elif admin_page == "2. 比賽項目維護":
            st.header("🎾 項目清單管理")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("新增項目")
                new_m = st.selectbox("選擇項目類型", ["男單", "女单", "男双", "女双", "混双"])
                if st.button("➕ 新增至賽程"):
                    current_config["match_list"].append(new_m)
                    save_config(current_config)
                    st.rerun()

            with col2:
                st.subheader("編輯現有項目")
                for i, m_name in enumerate(current_config["match_list"]):
                    c_edit1, c_edit2 = st.columns([3, 1])
                    with c_edit1:
                        # 允許直接重命名
                        new_name = st.text_input(f"場次 {i+1}", value=m_name, key=f"edit_m_{i}")
                        if new_name != m_name:
                            current_config["match_list"][i] = new_name
                            save_config(current_config)
                    with c_edit2:
                        if st.button("🗑️", key=f"del_m_{i}"):
                            current_config["match_list"].pop(i)
                            save_config(current_config)
                            st.rerun()

            st.divider()
            st.subheader("全局開關")
            current_config["is_locked"] = st.toggle("🔒 鎖定隊長提交端 (開啟後隊長不可修改名單)", value=current_config["is_locked"])
            if st.button("保存鎖定狀態"):
                save_config(current_config)
                st.success("狀態已更新")

        # --- 分頁 3：戰績統計 ---
        elif admin_page == "3. 戰績統計回報":
            st.header("🏆 戰績匯總")
            if os.path.exists(FILES["results"]):
                st.dataframe(pd.read_csv(FILES["results"]), use_container_width=True)
            else:
                st.info("尚無數據")

# --- 4. 隊長填單端 (顯示對戰順序) ---
elif role == "隊長填單端":
    st.header("📋 隊長填報系統")
    if current_config.get("match_order"):
        st.subheader(f"📢 今日對戰：{current_config['match_order']} | 場地：{current_config['court_num']}")
    
    if not os.path.exists(FILES["today"]) or not current_config["match_list"]:
        st.warning("⏳ 總監尚未發布今日比賽資訊...")
    else:
        today_df = pd.read_csv(FILES["today"])
        teams_list = list(current_config["team_codes"].keys())
        my_t = st.selectbox("請選擇您的隊伍", ["請選擇"] + teams_list)
        pwd_in = st.text_input("輸入授權碼", type="password")
        
        if my_t != "請選擇" and pwd_in == current_config["team_codes"].get(my_t):
            if current_config["is_locked"]:
                st.error("🔒 總監已鎖定提交，無法修改。")
            else:
                with st.form(f"form_{my_t}"):
                    picks = []
                    my_players = today_df[today_df['team'] == my_t]['name'].tolist()
                    for i, m_label in enumerate(current_config["match_list"]):
                        st.write(f"**場次 {i+1}：{m_label}**")
                        c1, c2 = st.columns(2)
                        p1 = c1.selectbox("選手 1", ["-"] + my_players, key=f"p1_{my_t}_{i}")
                        p2 = c2.selectbox("選手 2", ["-"] + my_players, key=f"p2_{my_t}_{i}") if "双" in m_label else "-"
                        picks.append([my_t, i, m_label, p1, p2])
                    if st.form_submit_button("📢 提交本輪名單"):
                        new_lineup = pd.DataFrame(picks, columns=['team','match_id','type','p1','p2'])
                        if os.path.exists(FILES["lineups"]):
                            old = pd.read_csv(FILES["lineups"])
                            new_lineup = pd.concat([old[old['team'] != my_t], new_lineup])
                        new_lineup.to_csv(FILES["lineups"], index=False)
                        st.success("提交成功！")

# --- 5. 對撞結果與報分區 (置底刷新) ---
st.divider()
if st.button("🧨 刷新對撞結果與報分介面"):
    st.session_state.show_results = True

if st.session_state.get("show_results"):
    # 檢查是否有足夠數據進行對撞
    if os.path.exists(FILES["lineups"]) and os.path.exists(FILES["today"]):
        all_l = pd.read_csv(FILES["lineups"])
        t_info = pd.read_csv(FILES["today"])
        
        # 遍歷所有比賽項目
        for mid, m_label in enumerate(current_config["match_list"]):
            # 過濾出該場次所有隊伍提交的名單
            m_data = all_l[all_l['match_id'] == mid]
            
            # 必須有至少兩支隊伍提交名單才能對撞
            if len(m_data) >= 2:
                st.subheader(f"🏟️ 場次 {mid+1}：{m_label}")
                
                # 這裡假設取前兩支提交名單的隊伍進行對決 (可依 match_order 邏輯進一步優化)
                t1, t2 = m_data['team'].iloc[0], m_data['team'].iloc[1]
                r1, r2 = m_data.iloc[0], m_data.iloc[1]
                
                # 1. 提取兩邊選手名單
                p1_list = [r1['p1'], r1['p2']]
                p2_list = [r2['p1'], r2['p2']]
                
                # 2. 根據比賽類型計算平均 UTR (單打用 s, 雙打用 d)
                utr_col = 'utr_d' if "双" in m_label else 'utr_s'
                u1 = t_info[t_info['name'].isin(p1_list)][utr_col].mean()
                u2 = t_info[t_info['name'].isin(p2_list)][utr_col].mean()
                
                # 3. 計算差距與目標局數 (保本策略邏輯)
                diff = abs(u1 - u2)
                # 差距越大，低分方目標局數越少 (最低1局，最高5局)
                target = 5 if diff <= 0.5 else 4 if diff <= 1.0 else 3 if diff <= 1.5 else 2 if diff <= 2.0 else 1
                low_t = t1 if u1 < u2 else t2
                
                # 顯示對撞看板
                col_a, col_b, col_c = st.columns([2, 1, 2])
                col_a.metric(f"隊伍: {t1}", f"{u1:.2f} UTR", help=f"選手: {r1['p1']}, {r1['p2']}")
                col_b.markdown(f"<h3 style='text-align: center;'>VS</h3>", unsafe_allow_html=True)
                col_c.metric(f"隊伍: {t2}", f"{u2:.2f} UTR", help=f"選手: {r2['p1']}, {r2['p2']}")
                
                st.warning(f"💡 實力分析：低分方 **【{low_t}】** 需拿到 **{target}** 局即視為挑戰成功！")

                # 4. 報分 Form
                with st.form(f"score_form_{mid}"):
                    c1, c2 = st.columns(2)
                    sc1 = c1.number_input(f"{t1} 最終局數", 0, 10, key=f"in1_{mid}")
                    sc2 = c2.number_input(f"{t2} 最終局數", 0, 10, key=f"in2_{mid}")
                    
                    submit_score = st.form_submit_button(f"💾 儲存場次 {mid+1} 比分")
                    
                    if submit_score:
                        winner = t1 if sc1 > sc2 else t2 if sc2 > sc1 else "平手"
                        low_sc = sc1 if low_t == t1 else sc2
                        challenge_status = "成功" if low_sc >= target else "失敗"
                        
                        # 封裝結果
                        res_row = pd.DataFrame([{
                            'mid': mid + 1,
                            'type': m_label,
                            't1': t1, 't2': t2,
                            's1': sc1, 's2': sc2,
                            'winner': winner,
                            'challenge': challenge_status,
                            'target_info': f"{low_t}需{target}局"
                        }])
                        
                        # 持久化儲存
                        if os.path.exists(FILES["results"]):
                            old_res = pd.read_csv(FILES["results"])
                            # 覆蓋舊的同場次紀錄
                            new_res = pd.concat([old_res[old_res['mid'] != (mid+1)], res_row])
                        else:
                            new_res = res_row
                        
                        new_res.to_csv(FILES["results"], index=False)
                        st.success(f"✅ 比分已錄入！{low_t} 挑戰{challenge_status}")
                st.divider()
        else:
            st.error("❌ 尚未有足夠的隊長提交名單，無法進行對撞。")
    else:
        st.info("ℹ️ 請先確保隊伍已分配且隊長已提交名單。")
