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

# 確保配置文件讀寫穩定
def save_config_to_file(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def load_config_from_file():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"match_list": [], "team_codes": {}, "is_locked": False}

# 強制實時載入最新配置
current_config = load_config_from_file()

@st.cache_data
def load_master_db():
    if os.path.exists('players.csv'):
        return pd.read_csv('players.csv')
    return pd.DataFrame(columns=['name', 'utr_s', 'utr_d', 'gender'])

master_df = load_master_db()

# --- 2. 側邊欄入口 ---
st.sidebar.title("🎾 賽事數據中心")
role = st.sidebar.selectbox("切換入口", ["隊長填單端", "總監管理端"])
admin_pwd = st.sidebar.text_input("管理員密碼", type="password")

# --- 3. 總監管理端 ---
if role == "總監管理端":
    if admin_pwd != "666":
        st.info("🔒 請輸入密碼解鎖後台")
    else:
        tab1, tab2 = st.tabs(["⚙️ 賽事設定與分配", "🏆 戰績匯總榜"])
        
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("1. 名單與授權碼生成", expanded=True):
                    team_in = st.text_input("隊伍名稱 (逗號隔開)", "A隊, B隊, C隊, D隊")
                    active_teams = [t.strip() for t in team_in.split(",")]
                    
                    all_player_names = master_df['name'].tolist()
                    sel_players = st.multiselect("勾選今日到場選手", all_player_names)
                    
                    if st.button("✅ 建立名單並生成密碼"):
                        today_df = master_df[master_df['name'].isin(sel_players)].copy()
                        today_df['team'] = "未分配"
                        today_df.to_csv(TODAY_PLAYERS_FILE, index=False)
                        
                        # 生成新密碼並直接寫入文件
                        current_config["team_codes"] = {t: str(random.randint(1000, 9999)) for t in active_teams}
                        save_config_to_file(current_config)
                        st.success(f"已建立！授權碼：{current_config['team_codes']}")

            with col2:
                with st.expander("2. 比賽項目確認", expanded=True):
                    m_type = st.selectbox("新增對撞項目", ["男單", "女单", "男双", "女双", "混双"])
                    if st.button("➕ 確認新增項目"):
                        current_config["match_list"].append(m_type)
                        save_config_to_file(current_config)
                        st.rerun() # 強制刷新顯示列表
                    
                    st.write("**📝 本輪待賽項目：**")
                    if current_config["match_list"]:
                        for i, m in enumerate(current_config["match_list"]):
                            st.text(f" {i+1}. {m}")
                    else:
                        st.caption("目前尚無項目")

                    st.divider()
                    current_config["is_locked"] = st.toggle("🔒 鎖定隊長修改", value=current_config["is_locked"])
                    if st.button("💾 保存鎖定狀態"):
                        save_config_to_file(current_config)
                        st.toast("鎖定設置已保存")

                    if st.button("🗑️ 重置/清空所有比賽"):
                        for f in [LINEUPS_FILE, CONFIG_FILE, RESULTS_FILE, TODAY_PLAYERS_FILE]: 
                            if os.path.exists(f): os.remove(f)
                        st.rerun()

            # 分配選手隊伍（獨立區塊）
            if os.path.exists(TODAY_PLAYERS_FILE):
                st.subheader("3. 選手隊伍分配")
                curr_today = pd.read_csv(TODAY_PLAYERS_FILE)
                updated_rows = []
                
                # 取得當前設定的隊伍列表
                current_teams = list(current_config["team_codes"].keys()) if current_config["team_codes"] else ["未分配"]
                
                c_idx = 0
                cols = st.columns(3)
                for idx, row in curr_today.iterrows():
                    with cols[c_idx % 3]:
                        t_idx = current_teams.index(row['team']) if row['team'] in current_teams else 0
                        new_t = st.selectbox(f"選手: {row['name']}", current_teams, index=t_idx, key=f"sel_{row['name']}")
                        updated_rows.append([row['name'], row['utr_s'], row['utr_d'], row['gender'], new_t])
                    c_idx += 1
                
                if st.button("💾 確認送出隊伍分配", type="primary"):
                    pd.DataFrame(updated_rows, columns=['name','utr_s','utr_d','gender','team']).to_csv(TODAY_PLAYERS_FILE, index=False)
                    st.success("隊伍分配已存檔！隊長現在可以使用其授權碼登入。")

        with tab2:
            st.subheader("📊 總戰績與積分榜")
            if os.path.exists(RESULTS_FILE):
                res_df = pd.read_csv(RESULTS_FILE)
                st.dataframe(res_df, use_container_width=True)
            else:
                st.info("暫無報分記錄")

# --- 4. 隊長填單端 (核心修復：強制讀取最新項目) ---
elif role == "隊長填單端":
    st.header("📋 隊長填報系統")
    
    if not os.path.exists(TODAY_PLAYERS_FILE) or not current_config["match_list"]:
        st.warning("⏳ 總監尚未完成名單分配或發布比賽項目，請稍候刷新。")
    else:
        today_df = pd.read_csv(TODAY_PLAYERS_FILE)
        teams_list = today_df['team'].unique().tolist()
        if "未分配" in teams_list: teams_list.remove("未分配")
        
        my_t = st.selectbox("請選擇您的隊伍", ["請選擇"] + teams_list)
        pwd_in = st.text_input("輸入該隊 4 位授權碼", type="password")
        
        if my_t != "請選擇" and pwd_in:
            correct_code = current_config["team_codes"].get(my_t)
            if pwd_in != correct_code:
                st.error("❌ 授權碼錯誤")
            elif current_config["is_locked"]:
                st.error("🔒 總監已鎖定填報，無法再進行修改。")
            else:
                st.success(f"✅ 驗證成功！請填寫 {my_t} 的排陣單：")
                my_players = today_df[today_df['team'] == my_t]['name'].tolist()
                
                with st.form(f"form_submit_{my_t}"):
                    picks = []
                    # 強制使用最新加載的 match_list
                    for i, m_label in enumerate(current_config["match_list"]):
                        st.markdown(f"**第 {i+1} 場：{m_label}**")
                        c1, c2 = st.columns(2)
                        p1 = c1.selectbox("選手 1", ["-"] + my_players, key=f"p1_{my_t}_{i}")
                        p2 = "-"
                        if "双" in m_label:
                            p2 = c2.selectbox("選手 2", ["-"] + my_players, key=f"p2_{my_t}_{i}")
                        picks.append([my_t, i, m_label, p1, p2])
                    
                    if st.form_submit_button("📢 提交本輪點單"):
                        new_lineup = pd.DataFrame(picks, columns=['team','match_id','type','p1','p2'])
                        if os.path.exists(LINEUPS_FILE):
                            old = pd.read_csv(LINEUPS_FILE)
                            new_lineup = pd.concat([old[old['team'] != my_t], new_lineup])
                        new_lineup.to_csv(LINEUPS_FILE, index=False)
                        st.balloons()
                        st.success(f"{my_t} 點單已成功送出！")

# --- 5. 對撞與報分結果顯示 ---
st.divider()
if st.button("🧨 顯示/刷新對撞結果與報分"):
    if os.path.exists(LINEUPS_FILE) and os.path.exists(TODAY_PLAYERS_FILE):
        all_l = pd.read_csv(LINEUPS_FILE)
        t_info = pd.read_csv(TODAY_PLAYERS_FILE)
        
        st.header("⚡ 實時對撞數據")
        
        # 遍歷總監設定的項目
        for mid in range(len(current_config["match_list"])):
            m_label = current_config["match_list"][mid]
            m_data = all_l[all_l['match_id'] == mid]
            
            if len(m_data) < 2:
                st.info(f"第 {mid+1} 場 ({m_label}): 等待對手提交中...")
                continue
            
            st.subheader(f"場次 {mid+1}：{m_label}")
            teams = m_data['team'].tolist()
            # 兩兩對撞
            for k in range(0, len(teams)-1, 2):
                t1, t2 = teams[k], teams[k+1]
                r1 = m_data[m_data['team']==t1].iloc[0]
                r2 = m_data[m_data['team']==t2].iloc[0]
                
                # 計算 UTR
                def get_utr(names, mt):
                    active = [n for n in names if n != "-"]
                    res = t_info[t_info['name'].isin(active)]
                    return res['utr_d' if "双" in mt else 'utr_s'].mean(), active

                u1, n1 = get_utr([r1['p1'], r1['p2']], m_label)
                u2, n2 = get_utr([r2['p1'], r2['p2']], m_label)
                
                diff = abs(u1 - u2)
                target = 5 if diff<=0.5 else 4 if diff<=1.0 else 3 if diff<=1.5 else 2 if diff<=2.0 else 1
                low_t = t1 if u1 < u2 else t2

                c1, c2, c3 = st.columns([2, 1, 2])
                with c1: st.metric(t1, f"{u1:.2f}", f"{', '.join(n1)}")
                with c2: st.markdown("### VS")
                with c3: st.metric(t2, f"{u2:.2f}", f"{', '.join(n2)}")
                
                st.warning(f"🎯 低分方【{low_t}】目標局數：{target} 局 (分差 {diff:.2f})")
                
                # 實時報分組件
                with st.expander(f"📝 錄入比分 (第 {mid+1} 場)"):
                    sc1 = st.number_input(f"{t1} 局數", 0, 10, key=f"score1_{mid}")
                    sc2 = st.number_input(f"{t2} 局數", 0, 10, key=f"score2_{mid}")
                    if st.button(f"提交比分 #{mid}", key=f"save_{mid}"):
                        winner = t1 if sc1 > sc2 else t2 if sc2 > sc1 else "平"
                        low_sc = sc1 if low_t == t1 else sc2
                        challenge = "成功" if low_sc >= target else "失敗"
                        
                        res_data = pd.DataFrame([[mid, m_label, t1, t2, sc1, sc2, winner, challenge]], 
                                              columns=['mid','type','t1','t2','s1','s2','winner','challenge'])
                        if os.path.exists(RESULTS_FILE):
                            old_res = pd.read_csv(RESULTS_FILE)
                            res_data = pd.concat([old_res[old_res['mid'] != mid], res_data])
                        res_data.to_csv(RESULTS_FILE, index=False)
                        st.success(f"已儲存！挑戰結果：{challenge}")
            st.divider()
    else:
        st.info("數據尚未準備就緒。")
