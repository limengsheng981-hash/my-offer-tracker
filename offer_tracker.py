import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 配置数据文件和选项
DATA_FILE = "job_applications.csv"
COLUMNS = ["公司名称", "岗位", "工作地点", "企业性质", "投递渠道", "岗位链接", "投递时间", "当前状态", "最后更新时间", "备注"]
STATUS_OPTIONS = ["已投递", "笔试", "一面", "二面", "技术面", "HR面", "Offer", "感谢信", "池子"]
COMPANY_TYPES = ["研究所", "国企", "私企/民企", "外企", "合资", "事业单位"]
CHANNEL_OPTIONS = ["官网投递", "招聘软件投递", "小程序投递", "线下招聘会投递", "内部推荐", "其他"]

# 定义求职进度的逻辑先后顺序（用于智能排序，Offer和面对应排在最前）
STATUS_RANKING = ["Offer", "HR面", "技术面", "二面", "一面", "笔试", "已投递", "池子", "感谢信"]

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        for col in COLUMNS:
            if col not in df.columns:
                if col == "最后更新时间" and "投递时间" in df.columns:
                    df[col] = df["投递时间"] + " 00:00:00"
                else:
                    df[col] = ""
        return df
    else:
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    if "距上次变动" in df.columns:
        df = df.drop(columns=["距上次变动"])
    df.to_csv(DATA_FILE, index=False)

def calculate_time_diff(update_time_str):
    if pd.isna(update_time_str) or not update_time_str:
        return "未知"
    try:
        update_time = datetime.strptime(str(update_time_str), "%Y-%m-%d %H:%M:%S")
        diff = datetime.now() - update_time
        if diff.days > 0:
            return f"{diff.days} 天前"
        elif diff.seconds >= 3600:
            return f"{diff.seconds // 3600} 小时前"
        elif diff.seconds >= 60:
            return f"{diff.seconds // 60} 分钟前"
        else:
            return "刚刚"
    except:
        return "格式错误"

# 页面配置
st.set_page_config(page_title="OfferFlow 个人版", layout="wide")
st.title("🚀 求职投递追踪系统 (高级排序版)")

df = load_data()

# 侧边栏：新增记录与备份
st.sidebar.header("➕ 新增投递记录")
with st.sidebar.form("add_record_form", clear_on_submit=True):
    company = st.text_input("公司名称*")
    position = st.text_input("岗位*")
    location = st.text_input("工作地点 (如: 北京、南京)")
    company_type = st.selectbox("企业性质", COMPANY_TYPES)
    channel = st.selectbox("投递渠道", CHANNEL_OPTIONS)
    job_link = st.text_input("岗位链接 (https://...)")
    apply_date = st.date_input("投递时间", datetime.today())
    status = st.selectbox("当前状态", STATUS_OPTIONS)
    notes = st.text_area("备注")
    
    submitted = st.form_submit_button("添加记录")
    if submitted:
        if company and position:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_record = pd.DataFrame([{
                "公司名称": company, "岗位": position, "工作地点": location,
                "企业性质": company_type, "投递渠道": channel, "岗位链接": job_link,
                "投递时间": apply_date.strftime("%Y-%m-%d"),
                "当前状态": status, "最后更新时间": now_str, "备注": notes
            }])
            df = pd.concat([df, new_record], ignore_index=True)
            save_data(df)
            st.sidebar.success(f"成功添加 {company}！")
            st.rerun()
        else:
            st.sidebar.error("公司名称和岗位不能为空！")

st.sidebar.markdown("---")
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "rb") as f:
        st.sidebar.download_button("📥 下载最新数据备份 (CSV)", f, file_name="my_offer_data.csv", mime="text/csv")

# 主界面
st.subheader("📋 投递状态监控")
if not df.empty:
    # 看板数据
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总投递数", len(df))
    col2.metric("流程中", len(df[df["当前状态"].isin(["笔试", "一面", "二面", "技术面", "HR面"])]))
    col3.metric("已拿 Offer 🏆", len(df[df["当前状态"] == "Offer"]))
    col4.metric("感谢信/无下文", len(df[df["当前状态"] == "感谢信"]))
    
    st.markdown("---")
    
    # 🌟 核心功能：交互式排序选择器
    sort_col1, sort_col2 = st.columns([1, 3])
    with sort_col1:
        sort_by = st.selectbox(
            "🗺️ 选择看板排序方式：",
            options=["默认 (添加顺序)", "按投递时间 (从新到旧)", "按投递进度 (核心流程优先)", "按工作地点 (城市拼音)"]
        )
    
    # 准备展示的数据
    display_df = df.copy()
    display_df["距上次变动"] = display_df["最后更新时间"].apply(calculate_time_diff)
    
    # 调整列顺序，让核心可看信息靠前
    cols_order = ["公司名称", "岗位", "当前状态", "距上次变动", "工作地点", "企业性质", "投递渠道", "岗位链接", "投递时间", "备注", "最后更新时间"]
    display_df = display_df[[c for c in cols_order if c in display_df.columns]]
    
    # 🌟 执行排序逻辑
    if sort_by == "按投递时间 (从新到旧)":
        display_df = display_df.sort_values(by="投递时间", ascending=False)
    elif sort_by == "按投递进度 (核心流程优先)":
        # 使用 Categorical 类型按招聘漏斗深度排序
        display_df["progress_rank"] = pd.Categorical(display_df["当前状态"], categories=STATUS_RANKING, ordered=True)
        display_df = display_df.sort_values(by="progress_rank")
        display_df = display_df.drop(columns=["progress_rank"])
    elif sort_by == "按工作地点 (城市拼音)":
        # 缺失值排在最后
        display_df = display_df.sort_values(by="工作地点", ascending=True, na_position='last')

    st.write("💡 **提示**：可直接双击下方表格的单元格进行**修改**，修改后数据会自动实时保存更新。")

    # 可交互编辑表格
    edited_df = st.data_editor(
        display_df,
        column_config={
            "当前状态": st.column_config.SelectboxColumn("当前状态", options=STATUS_OPTIONS, required=True),
            "企业性质": st.column_config.SelectboxColumn("企业性质", options=COMPANY_TYPES),
            "投递渠道": st.column_config.SelectboxColumn("投递渠道", options=CHANNEL_OPTIONS),
            "岗位链接": st.column_config.LinkColumn("岗位链接", display_text="🔗 查看岗位"),
            "距上次变动": st.column_config.TextColumn("⏱️ 距上次变动", disabled=True),
            "最后更新时间": None # 后台隐蔽
        },
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic"
    )
    
    # 数据修改动态保存检查
    if not display_df.equals(edited_df):
        # 检查是否改变了“当前状态”
        status_changed_mask = display_df["当前状态"] != edited_df["当前状态"]
        if status_changed_mask.any():
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            edited_df.loc[status_changed_mask, "最后更新时间"] = now_str
            st.toast("状态已更新，已重置变动时间 ⏱️")
            
        save_data(edited_df)
        st.success("✅ 数据已自动修改并保存！")
        st.rerun()
else:
    st.info("目前还没有投递记录，请在左侧填写并添加你的第一条求职记录！")
