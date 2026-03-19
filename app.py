import streamlit as st
import pandas as pd
import os

# --- 1. 核心數據庫模擬 (對接截圖資料) ---
def init_db():
    data = {
        'nickname': ['本吹提要次西瓜', '香云', 'Tiff', 'MP_IYDUHP', '天空', '小昊', '黑Sir', '瑞德勒'],
        'real_name': ['姜浩', '毕彩云', 'Tiff', '钱佳宁', '李光宇', '吴园园', '樊志海', '杨瑞'],
        'utr_name': ['John jiang', 'caiyun bi', 'tian tiff', 'jianing qian', 'guangyu li', 'yuanyuan wu', 'zhihai fan', 'rui yang'],
        'email': ['jianghao36@163.com', '297774997@qq.com', '464495858@qq.com', '8611605@qq.com', '18915599771@189.cn', '18502134025@163.com', '123970381@qq.com', '527887451@qq.com'],
        'utr_s': [4.66, 1.00, 1.00, 1.00, 2.50, 1.00, 1.00, 2.85],
        'utr_d': [2.00, 1.00, 1.00, 1.00, 3.86, 1.00, 1.00, 1.00],
        'region': ['江苏省 苏州市', '吉林省 长春市', '江苏省 苏州市', '浙江省 嘉兴市', '江苏省 苏州市', '上海市 静安区', '福建省 福州市', '江苏省 苏州市'],
        'status': ['已認證'] * 8,
        'club': ['無', '海德網球社', '無', '無', '威爾森精英隊', '無', '耐克之星', '無'],
        'contribution': [0.0, 500.0, 0.0, 0.0, 350.0, 0.0, 420.0, 0.0]
    }
    return pd.DataFrame(data)

# --- 2. 初始化環境 ---
st.set_page_config(page_title="MP Tennis Pro", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = init_db()
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 3. 側邊欄：郵箱登入 ---
st.sidebar.title("🎾 MP Tennis 登入")
if not st.session_state.logged_in:
    with st.sidebar.form("login"):
        u_email = st.text_input("輸入 UTR 註冊郵箱 (搜索實力用)")
        u_pw = st.text_input("輸入密碼 (保護帳號用)", type="password")
        if st.form_submit_button("登入 / 驗證"):
            if u_email in st.session_state.db['email'].values:
                st.session_state.logged_in = True
                st.session_state.user_email = u_email
                st.rerun()
            else:
                st.error("郵箱未關聯 UTR，請聯繫總監")
    st.stop()
else:
    user = st.session_state.db[st.session_state.db['email'] == st.session_state.user_email].iloc[0]
    st.sidebar.success(f"已登入: {user['nickname']}")
    if st.sidebar.button("登出"):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. 主介面展示 ---
st.header(f"👋 {user['nickname']} (UTR名稱: {user['utr_name']})")
c1, c2, c3 = st.columns(3)
c1.metric("單打 UTR", user['utr_s'])
c2.metric("雙打 UTR", user['utr_d'])
c3.metric("所屬地區", user['region'])

# --- 5. 核心模組跳轉 ---
tab1, tab2, tab3 = st.tabs(["🏆 實力榜單", "🛡️ 俱樂部管理", "⚔️ 賽事中心"])

with tab1:
    st.subheader("🌏 全國 / 地區 UTR 實力排名")
    scope = st.selectbox("地區篩選", ["全國", "江苏省", "上海市", "浙江省", "吉林省"])
    utr_type = st.radio("排序依據", ["單打", "雙打"], horizontal=True)
    
    r_df = st.session_state.db.copy()
    if scope != "全國": r_df = r_df[r_df['region'].str.contains(scope)]
    
    sort_key = 'utr_s' if utr_type == "單打" else 'utr_d'
    r_df = r_df.sort_values(by=sort_key, ascending=False).reset_index(drop=True)
    r_df.index += 1
    st.table(r_df[['nickname', 'utr_name', 'utr_s', 'utr_d', 'region', 'club']])

with tab2:
    st.subheader("🛡️ 俱樂部聲望中心")
    if user['club'] == "無":
        st.warning("目前無俱樂部")
        st.button("🔍 申請加入 / ➕ 創建俱樂部")
    else:
        st.success(f"目前俱樂部：{user['club']} | 貢獻值：{user['contribution']}")
        if st.button("❌ 退出俱樂部", help="聲望將歸零"):
            idx = st.session_state.db[st.session_state.db['email'] == st.session_state.user_email].index
            st.session_state.db.loc[idx, 'club'] = "無"
            st.session_state.db.loc[idx, 'contribution'] = 0.0
            st.rerun()

with tab3:
    st.subheader("⚔️ 團體對抗賽 (對撞補償)")
    role = st.toggle("切換為 總監管理端", False)
    
    if role:
        st.info("🛠️ 總監後台：發布賽制、錄入比分、審核報名")
    else:
        st.info("🚩 隊長端：預估補償分")
        opp_utr = st.slider("預計對手平均 UTR", 1.0, 13.0, 6.0)
        diff = abs(user['utr_s'] - opp_utr)
        # 對撞階梯
        target = 5 if diff <= 0.5 else 4 if diff <= 1.0 else 3 if diff <= 1.5 else 2 if diff <= 2.0 else 1
        st.success(f"💡 對撞結果：我方單打為 {user['utr_s']}，分差 {diff:.2f}。低分方目標：{target} 局")

st.caption("MP Tennis 2026 | UTR 實力導向賽事系統")
