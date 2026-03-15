import streamlit as st
import pandas as pd

# 1. ????
def load_data():
    return pd.read_csv('players.csv')

st.set_page_config(page_title="??????", layout="wide")
df = load_data()

# 2. ??????
st.sidebar.title("?? ?????")
pwd = st.sidebar.text_input("?????", type="password")

if 'match_list' not in st.session_state:
    st.session_state.match_list = []

if pwd == "666": # ??????
    st.sidebar.subheader("???:??????")
    m_type = st.sidebar.selectbox("????", ["??", "??"])
    if st.sidebar.button("????"):
        st.session_state.match_list.append(m_type)
    if st.sidebar.button("????"):
        st.session_state.match_list = []

# 3. ?????????
st.title("?? ??????")

if not st.session_state.match_list:
    st.warning("?????????????????...")
else:
    with st.form("match_form"):
        temp_results = []
        for i, m_type in enumerate(st.session_state.match_list):
            st.subheader(f"? {i+1} ?:{m_type}")
            c1, c2 = st.columns(2)
            with c1:
                p1_a = st.selectbox(f"A?-??1", ["-"] + df[df['??']=='A']['??'].tolist(), key=f"a{i}1")
                p2_a = st.selectbox(f"A?-??2", ["-"] + df[df['??']=='A']['??'].tolist(), key=f"a{i}2") if m_type=="??" else "-"
            with c2:
                p1_b = st.selectbox(f"B?-??1", ["-"] + df[df['??']=='B']['??'].tolist(), key=f"b{i}1")
                p2_b = st.selectbox(f"B?-??2", ["-"] + df[df['??']=='B']['??'].tolist(), key=f"b{i}2") if m_type=="??" else "-"
            temp_results.append({"type": m_type, "a": [p1_a, p2_a], "b": [p1_b, p2_b]})
        
        submitted = st.form_submit_button("?? ???????")

        if submitted and pwd == "666":
            st.divider()
            for i, res in enumerate(temp_results):
                # ??????
                def get_val(names, mt):
                    scores = [df[df['??']==n]['??UTR' if mt=="??" else '??UTR'].values[0] for n in names if n != "-"]
                    genders = [df[df['??']==n]['??'].values[0] for n in names if n != "-"]
                    return sum(scores)/len(scores), genders
                
                va, ga = get_val(res['a'], res['type'])
                vb, gb = get_val(res['b'], res['type'])
                diff = abs(va - vb)
                # ????
                t = 5 if diff<=0.5 else 4 if diff<=1.0 else 3 if diff<=1.5 else 2 if diff<=2.0 else 1
                
                st.success(f"### ? {i+1} ?:{res['a']} vs {res['b']} -> **?? {t} ?**")
                if ("?" in ga and "?" not in gb) or ("?" in gb and "?" not in ga):
                    st.warning("?? ????:?????+1?")
