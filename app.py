import streamlit as st
import pandas as pd

# 1. 核心选手库 (内置数据，确保国内访问稳定)
def get_data():
    data = {
        'name': ["Daisy", "Hsuanchi", "Han Zixiao", "Ye WenBo", "Charles", "XiaoDong Yin", "MingHan Huang", 
                 "Jiachu qiu", "Ge lei", "Yu Qiu", "Yu Li", "Yuhang Zhao", "Yulin zhu", "Jiarui Xiao"],
        'utr_s': [5.26, 6.79, 4.60, 5.85, 1.00, 5.55, 4.94, 4.90, 1.54, 5.39, 3.94, 5.47, 5.89, 4.65],
        'utr_d': [5.26, 7.18, 5.06, 5.07, 1.00, 5.55, 4.94, 4.94, 1.54, 5.39, 3.94, 6.09, 6.67, 3.96],
        'gender': ["女", "男", "男", "男", "男", "男", "女", "男", "男", "女", "女", "男", "男", "男"],
        'team': ["A", "A", "A", "A", "A", "A", "A", "B", "B", "B", "B", "B", "B", "B"]
    }
    return pd.DataFrame(data)

st.set_page_config(page_title="网球点单系统", layout="wide")
df = get_data()

# --- 总监侧边栏 ---
st.sidebar.title("🔐 赛事总监端")
pwd = st.sidebar.text_input("总监密码", type="password")

if 'match_config' not in st.session_state:
    st.session_state.match_config = []

if pwd == "666":
    st.sidebar.subheader("预设本轮场次")
    # 支持 5 个项目，但排阵不限性别
    m_type = st.sidebar.selectbox("项目类型", ["男单", "女单", "男双", "女双", "混双"])
    if st.sidebar.button("➕ 添加场次"):
        st.session_state.match_config.append(m_type)
    if st.sidebar.button("🗑️ 全部清空"):
        st.session_state.match_config = []
        st.rerun()

# --- 主界面 ---
st.title("🏆 现场点单排阵系统")

if not st.session_state.match_config:
    st.info("等待总监在左侧发布比赛项目...")
else:
    with st.form(key="match_input_form"):
        choices = []
        for i, m in enumerate(st.session_state.match_config):
            st.subheader(f"第 {i+1} 场：{m}")
            c1, c2 = st.columns(2)
            
            is_doubles = "双" in m
            
            with c1:
                st.write("**A队排阵**")
                a_list = df[df['team']=='A']['name'].tolist()
                p1a = st.selectbox(f"选手1", ["-选择-"] + a_list, key=f"a1_{i}")
                p2a = st.selectbox(f"选手2", ["-选择-"] + a_list, key=f"a2_{i}") if is_doubles else "-"
            with c2:
                st.write("**B队排阵**")
                b_list = df[df['team']=='B']['name'].tolist()
                p1b = st.selectbox(f"选手1", ["-选择-"] + b_list, key=f"b1_{i}")
                p2b = st.selectbox(f"选手2", ["-选择-"] + b_list, key=f"b2_{i}") if is_doubles else "-"
            
            choices.append({"type": m, "a": [p1a, p2a], "b": [p1b, p2b]})
        
        submit_clicked = st.form_submit_button("📢 开启对撞计算")

        if submit_clicked:
            if pwd != "666":
                st.error("🔒 请在左侧输入正确密码后再次提交")
            else:
                st.balloons()
                for i, res in enumerate(choices):
                    m_label = res['type']
                    
                    def process_team(names, mt):
                        actual = [n for n in names if n not in ["-选择-", "-"]]
                        if not actual: return 0, []
                        rows = df[df['name'].isin(actual)]
                        # 单打项目用 utr_s，双打/混双项目用 utr_d
                        scores = rows['utr_d' if "双" in mt else 'utr_s'].tolist()
                        genders = rows['gender'].tolist()
                        return sum(scores)/len(scores), genders

                    va, ga = process_team(res['a'], m_label)
                    vb, gb = process_team(res['b'], m_label)
                    
                    diff = abs(va - vb)
                    # 你的核心阶梯：0.5->5, 1.0->4, 1.5->3, 2.0->2, 2.0+ ->1
                    t = 5 if diff<=0.5 else 4 if diff<=1.0 else 3 if diff<=1.5 else 2 if diff<=2.0 else 1
                    
                    st.write("---")
                    st.success(f"### 第 {i+1} 场 ({m_label})：目标 {t} 局")
                    
                    col_res1, col_res2 = st.columns(2)
                    with col_res1:
                        st.write(f"**A队:** {', '.join([n for n in res['a'] if n != '-'])}")
                        st.write(f"平均分: {va:.2f}")
                    with col_res2:
                        st.write(f"**B队:** {', '.join([n for n in res['b'] if n != '-'])}")
                        st.write(f"平均分: {vb:.2f}")
                    
                    st.info(f"实力分差: {diff:.2f}")

                    # 核心补偿逻辑：只要两队性别构成不一致，就触发提醒
                    if ("女" in ga and "女" not in gb) or ("女" in gb and "女" not in ga):
                        st.warning("💡 性别补偿提示：含女选手队为低分方时，建议额外 +1 局")
