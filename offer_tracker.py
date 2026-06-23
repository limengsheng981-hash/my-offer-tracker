import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 配置数据文件和选项
DATA_FILE = "job_applications.csv"
# 新增了：投递渠道、岗位链接、最后更新时间
COLUMNS = ["公司名称", "岗位", "工作地点", "企业性质", "投递渠道", "岗位链接", "投递时间", "当前状态", "最后更新时间",
           "备注"]
STATUS_OPTIONS = ["已投递", "笔试", "一面", "二面", "技术面", "HR面", "Offer", "感谢信", "池子"]
COMPANY_TYPES = ["研究所", "国企", "私企/民企", "外企", "合资", "事业单位"]
CHANNEL_OPTIONS = ["官网投递", "招聘软件投递", "小程序投递", "线下招聘会投递", "内部推荐", "其他"]


def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        # 兼容老数据：如果老数据没有新加的列，自动补齐
        for col in COLUMNS:
            if col not in df.columns:
                if col == "最后更新时间" and "投递时间" in df.columns:
                    df[col] = df["投递时间"] + " 00:00:00"  # 默认老数据的更新时间为投递时间
                else:
                    df[col] = ""
        return df
    else:
        return pd.DataFrame(columns=COLUMNS)


def save_data(df):
    # 保存时去掉用于展示的动态计算列，只保存核心数据
    if "距上次变动" in df.columns:
        df = df.drop(columns=["距上次变动"])
    df.to_csv(DATA_FILE, index=False)


# 计算距离上次更新的时间差
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


# 设置页面布局
st.set_page_config(page_title="OfferFlow 个人版", layout="wide")
st.title("🚀 求职投递追踪系统 (Pro版)")

# 加载数据
df = load_data()

# 侧边栏：用于新增投递记录
st.sidebar.header("➕ 新增投递记录")
with st.sidebar.form("add_record_form", clear_on_submit=True):
    company = st.text_input("公司名称*")
    position = st.text_input("岗位*")
    location = st.text_input("工作地点")
    company_type = st.selectbox("企业性质", COMPANY_TYPES)

    # 新增字段
    channel = st.selectbox("投递渠道", CHANNEL_OPTIONS)
    job_link = st.text_input("岗位链接 (如：https://...)")

    apply_date = st.date_input("投递时间", datetime.today())
    status = st.selectbox("当前状态", STATUS_OPTIONS)
    notes = st.text_area("备注 (例如：薪资期望、面试重点等)")

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
            st.sidebar.success(f"成功添加 {company} 的记录！")
            st.sidebar.markdown("---")
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "rb") as f:
                    st.sidebar.download_button("📥 下载最新数据备份", f, file_name="offer_data.csv", mime="text/csv")
            st.rerun()
        else:
            st.sidebar.error("公司名称和岗位不能为空！")

# 主界面：展示和编辑数据
st.subheader("📋 投递状态监控")
if not df.empty:
    # 概览数据看板
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总投递数", len(df))
    col2.metric("流程中", len(df[df["当前状态"].isin(["笔试", "一面", "二面", "技术面", "HR面"])]))
    col3.metric("已拿 Offer 🏆", len(df[df["当前状态"] == "Offer"]))
    col4.metric("感谢信", len(df[df["当前状态"] == "感谢信"]))

    st.markdown("---")
    st.write("💡 **提示：直接在表格中修改状态，系统会自动记录状态变更时间，并将链接转为可点击的格式。**")

    # 动态计算停滞时间并展示
    display_df = df.copy()
    display_df["距上次变动"] = display_df["最后更新时间"].apply(calculate_time_diff)

    # 将“距上次变动”移动到“当前状态”旁边，方便查看
    cols_order = ["公司名称", "岗位", "当前状态", "距上次变动", "工作地点", "企业性质", "投递渠道", "岗位链接",
                  "投递时间", "备注", "最后更新时间"]
    # 确保列顺序
    display_df = display_df[[c for c in cols_order if c in display_df.columns]]

    # 可交互的数据表格
    edited_df = st.data_editor(
        display_df,
        column_config={
            "当前状态": st.column_config.SelectboxColumn(
                "当前状态",
                help="更新求职进度",
                options=STATUS_OPTIONS,
                required=True
            ),
            "企业性质": st.column_config.SelectboxColumn("企业性质", options=COMPANY_TYPES),
            "投递渠道": st.column_config.SelectboxColumn("投递渠道", options=CHANNEL_OPTIONS),
            "岗位链接": st.column_config.LinkColumn(
                "岗位链接",
                help="点击直接跳转到投递页面",
                display_text="🔗 前往查看"  # 让长长的链接变成一个干净的按钮文本
            ),
            "距上次变动": st.column_config.TextColumn(
                "⏱️ 距上次变动",
                disabled=True  # 禁止手动修改，系统自动计算
            ),
            "最后更新时间": None  # 在表格中隐藏这一列，保持界面清爽
        },
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic"
    )

    # 检测数据变化：特别是如果“当前状态”发生改变，自动更新“最后更新时间”
    if not display_df.equals(edited_df):
        # 找出哪些行的状态变了
        status_changed_mask = display_df["当前状态"] != edited_df["当前状态"]
        if status_changed_mask.any():
            # 获取当前精确时间
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 将改变状态的行的更新时间重置为当前时间
            edited_df.loc[status_changed_mask, "最后更新时间"] = now_str
            st.toast("检测到状态变更，计时器已重置！", icon="⏱️")

        save_data(edited_df)
        st.success("✅ 数据已同步！")
        st.rerun()  # 重新运行以刷新计时显示

else:
    st.info("目前还没有投递记录，请在左侧填写并添加你的第一条求职记录！")