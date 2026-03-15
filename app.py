import streamlit as st
import pandas as pd

# 1. 强制读取数据
@st.cache_data(ttl=60)
def load_data():
    return pd.read_csv('players.csv')

st.set_page_config(page_title="网球点单系统", layout="wide")
df = load_data()

# --- 总监侧边栏 ---
st.sidebar.title("🔐 管理后台")
pwd = st.sidebar.text_input("总监密码", type="password")

if 'match_config' not in st.session_state:
    st.session_state.match_config = []

if pwd == "666":
    st.sidebar.subheader("设置本轮场次")
    m_type = st.sidebar.selectbox("选择类型", ["单打", "双打"])
    if st.sidebar.button("➕ 添加场次", key="add_btn"):
        st.session_state.match_config.append(m_type)
    if st.sidebar.button("🗑️ 清空重置", key="reset_btn"):
        st.session_state.match_config = []
        st.rerun()

# --- 主界面 ---
st.title("🏆 现场点单对撞")

if not st.session_state.match_config:
    st.info("等待总监在左侧添加场次项目...")
else:
    # 确保 form 包含所有内容
    with st.form("match_form"):
        choices = []
        for i, m in enumerate(st.session_state.match_config):
            st.subheader(f"第 {i+1} 场：{m}")
            c1, c2 = st.columns(2)
            with c1:
                # 使用英文列名 team 和 name
                a_list = df[df['team']=='A']['name'].tolist()
                p1a = st.selectbox(f"A队选手1", ["-选择-"] + a_list, key=f"a1_{i}")
                p2a = st.selectbox(f"A队选手2", ["-选择-"] + a_list, key=f"a2_{i}") if m=="双打" else "-"
            with c2:
                b_list = df[df['team']=='B']['name'].tolist()
                p1b = st.selectbox(f"B队选手1", ["-选择-"] + b_list, key=f"b1_{i}")
                p2b = st.selectbox(f"B队选手2", ["-选择-"] + b_list, key=f"b2_{i}") if m=="双打" else "-"
            choices.append({"type": m, "a": [p1a, p2a], "b": [p1b, p2b]})
        
        # 按钮必须放在 form 内部的最后
        submit_clicked = st.form_submit_button("📢 开始对撞计算")

        if submit_clicked:
            if pwd != "666":
                st.error("🔒 请在左侧输入正确密码后再提交")
            else:
                st.balloons()
                for i, res in enumerate(choices):
                    def get_scores(names, mt):
                        actual_names = [n for n in names if n != "-选择-" and n != "-"]
                        if not actual_names: return 0, []
                        row_data = df[df['name'].isin(actual_names)]
                        col = 'utr_d' if mt=="双打" else 'utr_s'
                        return row_data[col].mean(), row_data['gender'].tolist()
                    
                    va, ga = get_scores(res['a'], res['type'])
                    vb, gb = get_scores(res['b'], res['type'])
                    diff = abs(va - vb)
                    t = 5 if diff<=0.5 else 4 if diff<=1.0 else 3 if diff<=1.5 else 2 if diff<=2.0 else 1
                    
                    st.write("---")
                    st.success(f"### 第 {i+1} 场：**目标 {t} 局**")
                    st.write(f"A队({va:.2f}) vs B队({vb:.2f}) | 分差: {diff:.2f}")
                    if ("女" in ga and "女" not in gb) or ("女" in gb and "女" not in ga):
                        st.warning("💡 性别补偿：建议低分方额外 +1 局")
