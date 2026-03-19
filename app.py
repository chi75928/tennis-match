import streamlit as st
import pandas as pd

# --- 1. 核心數據初始化 ---
def init_all_data():
    # 選手數據庫 (增加個人累計聲望欄位)
    p_data = {
        'nickname': ['本吹提要次西瓜', '香云', 'Tiff', '天空', 'Admin'],
        'email': ['jianghao36@163.com', '297774997@qq.com', '464495858@qq.com', '18915599771@189.cn', 'admin@mptennis.com'],
        'utr_s': [4.66, 1.00, 1.00, 2.50, 13.00],
        'utr_d': [2.00, 1.00, 1.00, 3.86, 13.00],
        'region': ['江蘇省 蘇州市', '吉林省 長春市', '江蘇省 蘇州市', '江蘇省 蘇州市', '全中國'],
        'club': ['無', '海德網球社', '無', '威爾森精英隊', '系統'],
        'p_prestige': [0.00, 0.00, 0.00, 0.00, 0.00], # 個人貢獻分
        'role': ['player', 'player', 'player', 'player', 'admin']
    }
    # 俱樂部數據庫
    c_data = {
        'club_name': ['海德網球社', '威爾森精英隊', '耐克之星', '系統'],
        'total_prestige': [50.00, 35.00, 10.00, 999.99],
        'founder': ['香云', '天空', '管理員', 'Admin']
    }
    return pd.DataFrame(p_data), pd.DataFrame(c_data)

st.set_page_config(page_title="MP Tennis Pro Control", layout="wide")

if 'p_db' not in st.session_state:
    st.session_state.p_db, st.session_state.c_db = init_all_data()
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 2. 登入系統 ---
if not st.session_state.logged_in:
    st.sidebar.title("🔐 MP Tennis 登入")
    login_mail = st.sidebar.text_input("輸入 UTR 註冊郵箱")
    if st.sidebar.button("確認登入"):
        if login_mail in st.session_state.p_db['email'].values:
            st.session_state.logged_in = True
            st.session_state.user_email = login_mail
            st.rerun()
        else:
            st.sidebar.error("郵箱未關聯，請聯繫總監")
    st.stop()

user = st.session_state.p_db[st.session_state.p_db['email'] == st.session_state.user_email].iloc[0]

# --- 3. 頂部導航 ---
st.markdown(f"### 👋 {user['nickname']} (ID: {user['email']})")
c1, c2, c3, c4 = st.columns(4)
c1.metric("單打 UTR", f"{user['utr_s']:.2f}")
c2.metric("雙打 UTR", f"{user['utr_d']:.2f}")
c3.metric("個人聲望", f"{user['p_prestige']:.2f}")
c4.write(f"📍 地區: {user['region']}")

if user['role'] == 'admin':
    st.success("👑 超級管理員模式：已解鎖全局數據錄入權限")

st.divider()

# --- 4. 三大核心板塊 ---
tab1, tab2, tab3 = st.tabs(["🏆 實力榜單", "🛡️ 俱樂部管理", "⚔️ 賽事中心"])

# ----- 模組一：實力榜單 (保留兩位小數) -----
with tab1:
    st.subheader("🌏 全國 UTR 實力排名")
    r_df = st.session_state.p_db.sort_values(by='utr_s', ascending=False).copy()
    # 格式化顯示
    r_df['utr_s'] = r_df['utr_s'].map('{:.2f}'.format)
    r_df['utr_d'] = r_df['utr_d'].map('{:.2f}'.format)
    r_df['p_prestige'] = r_df['p_prestige'].map('{:.2f}'.format)
    st.table(r_df[['nickname', 'utr_s', 'utr_d', 'region', 'club', 'p_prestige']])

# ----- 模組二：俱樂部管理 (聲望排行) -----
with tab2:
    st.subheader("🛡️ 俱樂部聲望排行榜")
    c_rank = st.session_state.c_db.sort_values(by='total_prestige', ascending=False).copy()
    c_rank['total_prestige'] = c_rank['total_prestige'].map('{:.2f}'.format)
    st.dataframe(c_rank, use_container_width=True)
    
    if user['club'] == "無":
        st.button("🔍 申請加入 / ➕ 創建俱樂部")
    else:
        st.info(f"您目前所屬：{user['club']}")
        if st.button("❌ 退出俱樂部 (個人貢獻與聲望將重置)"):
            st.session_state.p_db.loc[st.session_state.p_db['email']==user['email'], 'club'] = "無"
            st.session_state.p_db.loc[st.session_state.p_db['email']==user['email'], 'p_prestige'] = 0.00
            st.rerun()

# ----- 模組三：賽事中心 (勝利平分邏輯) -----
with tab3:
    st.header("⚔️ 賽事比分與積分錄入")
    
    if user['role'] != 'admin':
        st.warning("🔒 只有總監/超級管理員能錄入積分。")
        # 隊長預覽對撞
        opp_utr = st.slider("對手平均 UTR", 1.00, 13.00, 5.00)
        diff = abs(user['utr_s'] - opp_utr)
        target = 5 if diff <= 0.5 else 4 if diff <= 1.0 else 3 if diff <= 1.5 else 2 if diff <= 2.0 else 1
        st.success(f"對撞預測：分差 {diff:.2f}，低分方目標為 {target} 局。")
    else:
        st.write("🛠️ **超級管理員錄入專區**")
        with st.form("match_record"):
            win_club = st.selectbox("獲勝俱樂部", st.session_state.c_db['club_name'].tolist())
            match_type = st.radio("比賽性質", ["普通比分 (+1)", "V-UTR 認證比分 (+3)", "趣味對撞賽勝利 (+10)"])
            
            # 獲勝球員選擇 (用於平分 10 分)
            club_members = st.session_state.p_db[st.session_state.p_db['club'] == win_club]['nickname'].tolist()
            winners = st.multiselect("選擇本次參賽獲勝球員 (平分勝利分數)", club_members)
            
            if st.form_submit_button("📢 確認結算"):
                points = 1.0 if "普通" in match_type else 3.0 if "V-UTR" in match_type else 10.0
                
                # 1. 更新俱樂部總分
                st.session_state.c_db.loc[st.session_state.c_db['club_name']==win_club, 'total_prestige'] += points
                
                # 2. 更新個人分數 (平分邏輯)
                if winners:
                    per_person_points = points / len(winners)
                    for w_name in winners:
                        st.session_state.p_db.loc[st.session_state.p_db['nickname']==w_name, 'p_prestige'] += per_person_points
                    st.success(f"結算完成！{win_club} 總分 +{points:.2f}。球員 {', '.join(winners)} 每人各獲 +{per_person_points:.2f} 分。")
                else:
                    st.warning("未選擇參賽球員，僅更新俱樂部總分。")
                st.rerun()
