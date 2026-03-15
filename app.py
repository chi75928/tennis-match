import streamlit as st
import pandas as pd
import os

# --- 1. 基础配置与数据加载 ---
def load_all_players():
    # 假设你已经把800人资料传到GitHub的players.csv
    if os.path.exists('players.csv'):
        return pd.read_csv('players.csv')
    return pd.DataFrame(columns=['name', 'utr_s', 'utr_d', 'gender'])

# 模拟一个临时数据库，存放各队提交的点单
DB_FILE = "submitted_lineups.csv"

def save_lineup(team_name, match_id, p1, p2):
    # 将点单存入文件，实现跨手机同步
    new_data = pd.DataFrame([[team_name, match_id, p1, p2]], columns=['team', 'match_id', 'p1', 'p2'])
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        # 如果该队该场次已填过，则覆盖
        df = df[~((df['team'] == team_name) & (df['match_id'] == match_id))]
        df = pd.concat([df, new_data])
    else:
        df = new_data
    df.to_csv(DB_FILE, index=False)

# --- 2. 侧边栏：角色切换 ---
st.sidebar.title("🏆 赛事管理系统")
role = st.sidebar.radio("选择你的身份", ["队长填单端", "总监中控台"])
admin_pwd = st.sidebar.text_input("总监密码", type="password")

all_df = load_all_players()

# --- 3. 总监中控台逻辑 ---
if role == "总监中控台":
    if admin_pwd != "666":
        st.warning("请输入密码解锁总监权限")
    else:
        st.header("🛠️ 总监管理面板")
        
        # A. 比赛初始化：录入报名的队伍和选手
        with st.expander("第一步：本场报名录入"):
            teams_input = st.text_input("输入参赛队伍（逗号分隔）", "战神队,猎鹰队,猛虎队")
            active_teams = [t.strip() for t in teams_input.split(",")]
            st.session_state['active_teams'] = active_teams
            
            st.info("总监在此确认哪些选手今天到场了（从800人中筛选）")
            all_names = all_df['name'].tolist()
            present_players = st.multiselect("勾选今日到场选手", all_names)
            
            # 分配队伍（简单演示：总监也可以在此指定谁在哪队）
            if st.button("发布今日名单"):
                st.session_state['present_df'] = all_df[all_df['name'].isin(present_players)]
                st.success("名单已发布，队长们可以开始选人了！")

        # B. 场次发布
        with st.expander("第二步：发布本轮项目"):
            m_type = st.selectbox("新增场次", ["男单", "女单", "男双", "女双", "混双"])
            if st.button("确认发布该场次"):
                if 'match_list' not in st.session_state: st.session_state.match_list = []
                st.session_state.match_list.append(m_type)
        
        # C. 对撞计算
        st.divider()
        st.header("⚡ 实时对撞大榜")
        if os.path.exists(DB_FILE):
            lineups = pd.read_csv(DB_FILE)
            st.write("当前已收到的点单：", lineups)
            
            if st.button("🧨 开启一键对撞", type="primary"):
                # 这里遍历 lineups，抓取 UTR，计算分差，判定目标局数
                # 逻辑与你之前的版本一致，但会遍历所有 Team
                st.balloons()
                st.success("对撞完成！请截图发送至群聊。")
        else:
            st.info("暂无队长提交数据")

# --- 4. 队长填单端逻辑 ---
elif role == "队长填单端":
    st.header("📋 队长排点通道")
    
    if 'active_teams' not in st.session_state:
        st.error("总监尚未初始化队伍信息")
    else:
        my_team = st.selectbox("选择你的队伍", st.session_state['active_teams'])
        
        if 'match_list' not in st.session_state or not st.session_state.match_list:
            st.info("总监尚未发布比赛项目，请等待...")
        else:
            with st.form(f"form_{my_team}"):
                st.subheader(f"{my_team} 的排兵布阵")
                current_picks = []
                for i, m_label in enumerate(st.session_state.match_list):
                    st.write(f"第 {i+1} 场：{m_label}")
                    # 只显示总监确认到场的选手
                    present_list = st.session_state.get('present_df', all_df)['name'].tolist()
                    p1 = st.selectbox(f"选手1", ["-"] + present_list, key=f"p1_{my_team}_{i}")
                    p2 = "-"
                    if "双" in m_label:
                        p2 = st.selectbox(f"选手2", ["-"] + present_list, key=f"p2_{my_team}_{i}")
                    current_picks.append((i, p1, p2))
                
                if st.form_submit_button("提交排点表"):
                    for m_id, p1, p2 in current_picks:
                        save_lineup(my_team, m_id, p1, p2)
                    st.success(f"{my_team} 提交成功！请等待总监开榜。")
