import streamlit as st
import pandas as pd
import os
from datetime import datetime
from github import Github

# 配置数据文件和选项
DATA_FILE = "job_applications.csv"
COLUMNS = ["公司名称", "岗位", "工作地点", "企业性质", "投递渠道", "岗位链接", "投递时间", "当前状态", "最后更新时间", "备注"]
STATUS_OPTIONS = ["已投递", "笔试", "一面", "二面", "技术面", "HR面", "Offer", "感谢信", "池子"]
COMPANY_TYPES = ["研究所", "国企", "私企/民企", "外企", "合资", "事业单位"]
CHANNEL_OPTIONS = ["官网投递", "招聘软件投递", "小程序投递", "线下招聘会投递", "内部推荐", "其他"]
STATUS_RANKING = ["Offer", "HR面", "技术面", "二面", "一面", "笔试", "已投递", "池子", "感谢信"]

# 🚀 获取 GitHub Token 和仓库信息
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", None)
REPO_NAME = "limengsheng981-hash/my-offer-tracker"

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
    # 1. 先保存本地
    if "距上次变动" in df.columns:
        df = df.drop(columns=["距上次变动"])
    df.to_csv(DATA_FILE, index=False)
    
    # 2. 自动同步到 GitHub
    if GITHUB_TOKEN:
        try:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                
            contents = repo.get_contents(DATA_FILE)
            repo.update_file(
                contents.path, 
                f"自动同步求职进度 {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                content, 
                contents.sha
            )
            st.toast("✅ 数据已自动同步至 GitHub 云端！", icon="☁️")
        except Exception as e:
            st.toast(f"❌ 云端同步失败: {e}", icon="⚠️")
    else:
        st.toast("⚠️ 未配置 GitHub Token，数据仅保存在临时服务器", icon="⚠️")

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

st.set_page_config(page_title="OfferFlow 个人版", layout="wide")
st.title("🚀 求职投递追踪系统 (自动云同步版)")

df = load_data()

st.sidebar.header("➕ 新增投递记录")
with st.sidebar.form("add_record_form", clear_on_submit=True):
    company = st.text_input("公司名称*")
    position = st.text_input("岗位*")
    location = st.text_input("工作地点")
    company_type = st.selectbox("企业性质", COMPANY_TYPES)
    channel = st.selectbox("投递渠道", CHANNEL_OPTIONS)
    job_link = st.text_input("岗位链接")
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
        st.sidebar.download_button("📥 手动下载数据备份", f, file_name="my_offer_data.csv", mime="text/csv")

st.subheader("📋 投递状态监控")
if not df.empty:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总投递数", len(df))
    col2.metric("流程中", len(df[df["当前状态"].isin(["笔试", "一面", "二面", "技术面", "HR面"])]))
    col3.metric("已拿 Offer 🏆", len(df[df["当前状态"] == "Offer"]))
    col4.metric("感谢信/无下文", len(df[df["当前状态"] == "感谢信"]))
    
    st.markdown("---")
    
    sort_col1, sort_col2 = st.columns([1, 3])
    with sort_col1:
        sort_by = st.selectbox(
            "🗺️ 选择看板排序方式：",
            options=["默认 (添加顺序)", "按投递时间 (从新到旧)", "按投递进度 (核心流程优先)", "按工作地点 (城市拼音)"]
        )
    
    display_df = df.copy()
    display_df["距上次变动"] = display_df["最后更新时间"].apply(calculate_time_diff)
    
    cols_order = ["公司名称", "岗位", "当前状态", "距上次变动", "工作地点", "企业性质", "投递渠道", "岗位链接", "投递时间", "备注", "最后更新时间"]
    display_df = display_df[[c for c in cols_order if c in display_df.columns]]
    
    if sort_by == "按投递时间 (从新到旧)":
        display_df = display_df.sort_values(by="投递时间", ascending=False)
    elif sort_by == "按投递进度 (核心流程优先)":
        display_df["progress_rank"] = pd.Categorical(display_df["当前状态"], categories=STATUS_RANKING, ordered=True)
        display_df = display_df.sort_values(by="progress_rank")
        display_df = display_df.drop(columns=["progress_rank"])
    elif sort_by == "按工作地点 (城市拼音)":
        display_df = display_df.sort_values(by="工作地点", ascending=True, na_position='last')

    edited_df = st.data_editor(
        display_df,
        column_config={
            "当前状态": st.column_config.SelectboxColumn("当前状态", options=STATUS_OPTIONS, required=True),
            "企业性质": st.column_config.SelectboxColumn("企业性质", options=COMPANY_TYPES),
            "投递渠道": st.column_config.SelectboxColumn("投递渠道", options=CHANNEL_OPTIONS),
            "岗位链接": st.column_config.LinkColumn("岗位链接", display_text="🔗 查看岗位"),
            "距上次变动": st.column_config.TextColumn("⏱️ 距上次变动", disabled=True),
            "最后更新时间": None 
        },
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic"
    )
    
    if not display_df.equals(edited_df):
        status_changed_mask = display_df["当前状态"] != edited_df["当前状态"]
        if status_changed_mask.any():
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            edited_df.loc[status_changed_mask, "最后更新时间"] = now_str
            
        save_data(edited_df)
        st.success("✅ 数据已更新！")
        st.rerun()
else:
    st.info("目前还没有投递记录，请在左侧填写并添加你的第一条求职记录！")
