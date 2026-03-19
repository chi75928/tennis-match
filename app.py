import streamlit as st
import pandas as pd

# --- 1. 核心數據庫初始化 (對接您的截圖資料) ---
def init_all_master_data():
    # 選手數據：包含 UTR、地區、角色、辦賽權限、個人聲望
    p_data = {
        'nickname': ['本吹提要次西瓜', '香云', 'Tiff', '天空', 'Admin', '小昊', '黑Sir', '瑞德勒'],
        'email': ['jianghao36@163.com', '297774997@qq.com', '464495858@qq.com', '18915599771@189.cn', 'admin@mptennis.com', '18502134025@163.com', '123970381@qq.com', '527887451@qq.com'],
        'utr_s': [4.66, 1.00, 1.00, 2.50, 13.00, 1.00, 1.00, 2.85],
        'utr_d': [2.00, 1.00, 1.00, 3.86, 13.00, 1.00, 1.00, 1.00],
        'region': ['江蘇省 蘇州市', '吉林省 長春市', '江蘇省 蘇州市', '江蘇省 蘇州市', '全中國', '上海市 靜安區', '福建省 福州市', '江蘇省 蘇州市'],
        'club': ['無', '海德網球社', '無', '威爾森精英隊', '系統', '無', '耐克之星', '無'],
        'p_prestige': [0.00, 0.00, 0.00, 0.00, 999.00, 0.00, 0.00, 0.00],
        'role': ['player', 'player', 'player', 'player', 'admin', 'player', 'player', 'player'],
        'can_organize': [False, True, False, False, True, False, False, False] # 總監辦賽權限
    }
    # 俱樂部數據：包含總聲望
    c_data = {
        'club_name': ['海德網球社', '威爾森精英隊', '耐克之星', '系統'],
        'total_prestige': [50.00, 35.00, 10.00, 9999.00],
        'founder': ['香云', '天空', '管理員', 'Admin']
    }
    return pd.DataFrame(p_data), pd.DataFrame(c_data)

# --- 2. 系統配置 ---
st.set_page_config(page_title="MP Tennis Pro System", layout="wide")

if 'p_db' not in st.session_state:
    st.session_state.p_db, st.session_state.c_db = init_all_master_data()
if 'events' not in st.session_state:
    st.session_state.events = [] # 賽事列表
if 'rejoin_log' not in st.session_state:
    st.session_state.rejoin_log = {} # 記錄回歸次數

# --- 3. 登入模組 (郵箱保護) ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.sidebar.title("🎾 MP Tennis 登入")
    u_mail = st.sidebar.text_input("UTR 註冊郵箱")
    u_pw = st.sidebar.text_input("密碼", type="password")
    if st.sidebar.button("驗證登入"):
        if u_mail in st.session_state.p_db['email'].values:
            st.session_state.logged_in = True
            st.session_state.user_email = u_mail
            st.rerun()
        else:
            st.sidebar.error("郵箱未關聯 UTR，請聯繫管理員")
    st.stop()

# 獲取當前用戶對象
user = st.session_state.p_db[st.session_state.p_db['email'] == st.session_state.user_email].iloc[0]

# --- 4. 頂部狀態列 ---
st.markdown(f"### 👋 歡迎，{user['nickname']} | 單打: {user['utr_s']:.2f} | 雙打: {user['utr_d']:.2f}")
if user['role'] == 'admin':
    st.info("👑 超級管理員模式已啟動")

st.divider()

# --- 5. 五大核心分頁 ---
tabs = st.tabs(["🏆 實力榜單", "🛡️ 俱樂部中心", "🎾 賽事報名", "🛠️ 總監辦賽", "👑 超級管理"])

# ----- TAB 1: 實力榜單 (全國/地區) -----
with tabs[0]:
    st.subheader("🌏 UTR 全國實力排行榜")
    scope = st.selectbox("區域篩選", ["全國", "江蘇省", "上海市", "吉林省", "福建省"])
    r_df = st.session_state.p_db.copy()
    if scope != "全國":
        r_df = r_df[r_df['region'].str.contains(scope)]
    
    r_df = r_df.sort_values(by='utr_s', ascending=False).reset_index(drop=True)
    r_df.index += 1
    # 格式化輸出
    display_df = r_df[['nickname', 'utr_s', 'utr_d', 'region', 'club', 'p_prestige']].copy()
    display_df['utr_s'] = display_df['utr_s'].map('{:.2f}'.format)
    display_df['utr_d'] = display_df['utr_d'].map('{:.2f}'.format)
    st.table(display_df)

# ----- TAB 2: 俱樂部中心 (聲望與折扣) -----
with tabs[1]:
    st.subheader("🛡️ 俱樂部聲望與管理")
    c_rank = st.session_state.c_db.sort_values(by='total_prestige', ascending=False)
    st.dataframe(c_rank, use_container_width=True)
    
    st.divider()
    if user['club'] == "無":
        col1, col2 = st.columns(2)
        with col1:
            st.write("🔍 加入俱樂部")
            target_c = st.selectbox("選擇要加入的俱樂部", st.session_state.c_db['club_name'].tolist())
            if st.button(f"申請加入 {target_c}"):
                # 回歸折扣邏輯
                rejoin_key = f"{user['email']}_{target_c}"
                discount = 1.0
                if rejoin_key in st.session_state.rejoin_log:
                    st.session_state.rejoin_log[rejoin_key] += 1
                    count = st.session_state.rejoin_log[rejoin_key]
                    discount = 0.5 if count == 2 else 0.33
                    st.warning(f"偵測到回歸！聲望恢復比例為 {int(discount*100)}%")
                else:
                    st.session_state.rejoin_log[rejoin_key] = 1
                
                st.session_state.p_db.loc[st.session_state.p_db['email']==user['email'], 'club'] = target_c
                st.rerun()
    else:
        st.success(f"目前所屬：{user['club']} | 個人貢獻：{user['p_prestige']:.2f}")
        if st.button("❌ 退出俱樂部 (聲望將歸零)"):
            st.session_state.p_db.loc[st.session_state.p_db['email']==user['email'], 'club'] = "無"
            st.session_state.p_db.loc[st.session_state.p_db['email']==user['email'], 'p_prestige'] = 0.0
            st.rerun()

# ----- TAB 3: 賽事報名 (大廳) -----
with tabs[2]:
    st.subheader("🎾 賽事大廳")
    if not st.session_state.events:
        st.info("目前沒有報名中的賽事")
    else:
        for i, ev in enumerate(st.session_state.events):
            with st.expander(f"【{ev['type']}】{ev['name']} - {ev['format']}"):
                st.write(f"簽位人數：{ev['size']} | 總監：{ev['organizer']}")
                if st.button(f"確認報名", key=f"reg_{i}"):
                    st.toast("報名已提交！")

# ----- TAB 4: 總監辦賽 (多元賽制+排點位) -----
with tabs[3]:
    if not user['can_organize']:
        st.error("🔒 權限不足。您需要由超級管理員授權「總監權限」後方可辦賽。")
    else:
        st.subheader("🛠️ 總監控制台")
        with st.form("event_creator"):
            e_name = st.text_input("賽事名稱")
            e_type = st.selectbox("賽事分類", ["單打賽", "雙打賽", "團體賽"])
            e_format = st.selectbox("詳細賽制", ["單淘汰賽", "分組循環賽", "循環後淘汰", "趣味對撞賽"])
            e_size = st.number_input("預計簽位/人數", 4, 128, 16)
            if st.form_submit_button("發布賽事"):
                st.session_state.events.append({
                    "name": e_name, "type": e_type, "format": e_format,
                    "size": e_size, "organizer": user['nickname']
                })
                st.rerun()
        
        st.divider()
        if any(e['type'] == '團體賽' for e in st.session_state.events):
            st.subheader("🚩 團體賽排點位系統")
            st.write("請安排出賽名單：")
            c1, c2, c3 = st.columns(3)
            c1.selectbox("第一單打 (S1)", st.session_state.p_db['nickname'])
            c2.selectbox("第二單打 (S2)", st.session_state.p_db['nickname'])
            c3.selectbox("關鍵雙打 (D1)", st.session_state.p_db['nickname'], index=2)
            st.button("保存陣容")

# ----- TAB 5: 超級管理 (全局控制) -----
with tabs[4]:
    if user['role'] != 'admin':
        st.error("此頁面僅供超級管理員 admin@mptennis.com 訪問")
    else:
        st.subheader("👑 超級管理控制面板")
        
        # 1. 授權總監頁面
        st.write("### 授權總監權限")
        edited_p = st.data_editor(
            st.session_state.p_db[['nickname', 'email', 'can_organize']],
            column_config={"can_organize": st.column_config.CheckboxColumn("辦賽總監權限")},
            disabled=["nickname", "email"],
            key="admin_editor"
        )
        if st.button("保存權限更改"):
            st.session_state.p_db['can_organize'] = edited_p['can_organize']
            st.success("權限已更新！")
            
        # 2. 錄入比分與聲望結算 (勝利平分邏輯)
        st.divider()
        st.write("### 賽事比分結算 (發放聲望)")
        with st.form("score_final"):
            win_c = st.selectbox("獲勝俱樂部", st.session_state.c_db['club_name'].tolist())
            p_type = st.radio("得分性質", ["普通 (+1)", "V-UTR (+3)", "對撞賽勝利 (+10)"])
            # 選擇參與球員平分分數
            members = st.session_state.p_db[st.session_state.p_db['club'] == win_c]['nickname'].tolist()
            winners = st.multiselect("選擇參與獲勝球員 (分數將平分給他們)", members)
            
            if st.form_submit_button("執行結算"):
                pts = 1.0 if "普通" in p_type else 3.0 if "V-UTR" in p_type else 10.0
                # 更新俱樂部
                st.session_state.c_db.loc[st.session_state.c_db['club_name']==win_c, 'total_prestige'] += pts
                # 平分給個人
                if winners:
                    share = pts / len(winners)
                    for w in winners:
                        st.session_state.p_db.loc[st.session_state.p_db['nickname']==w, 'p_prestige'] += share
                    st.success(f"結算完成！{win_c} 獲得 {pts} 分，參與球員各得 {share:.2f} 分。")
                st.rerun()

st.caption("MP Tennis 2026 | 穩健守護型賽事邏輯系統")
