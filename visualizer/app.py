import os
import glob
import time
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import altair as alt
from datetime import datetime, timedelta


DATA_DIR = os.environ.get("DATA_DIR", "/Users/xujinliang/Desktop/AndroidPerfMon/data")


def list_csv_files():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "metrics_*.csv")))
    return files


def load_csv(path):
    try:
        df = pd.read_csv(path)
        # parse timestamp if present
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"读取CSV失败: {e}")
        return pd.DataFrame()


def filter_by_time_range(df, time_range_option, custom_start=None, custom_end=None):
    """根据时间范围筛选数据"""
    if df.empty or "timestamp" not in df.columns:
        return df
    
    # 获取最新时间点
    latest_time = df["timestamp"].max()
    
    if time_range_option == "全部数据":
        return df
    elif time_range_option == "最近5分钟":
        start_time = latest_time - timedelta(minutes=5)
    elif time_range_option == "最近15分钟":
        start_time = latest_time - timedelta(minutes=15)
    elif time_range_option == "最近30分钟":
        start_time = latest_time - timedelta(minutes=30)
    elif time_range_option == "最近1小时":
        start_time = latest_time - timedelta(hours=1)
    elif time_range_option == "最近3小时":
        start_time = latest_time - timedelta(hours=3)
    elif time_range_option == "自定义时间":
        if custom_start and custom_end:
            return df[(df["timestamp"] >= custom_start) & (df["timestamp"] <= custom_end)]
        return df
    else:
        return df
    
    return df[df["timestamp"] >= start_time]


def display_data_summary(df):
    """显示数据摘要信息"""
    if df.empty or "timestamp" not in df.columns:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("数据点数", f"{len(df):,}")
    
    with col2:
        start_time = df["timestamp"].min()
        st.metric("开始时间", start_time.strftime("%H:%M:%S"))
    
    with col3:
        end_time = df["timestamp"].max()
        st.metric("结束时间", end_time.strftime("%H:%M:%S"))
    
    with col4:
        duration = (df["timestamp"].max() - df["timestamp"].min()).total_seconds()
        if duration < 60:
            duration_str = f"{duration:.0f}秒"
        elif duration < 3600:
            duration_str = f"{duration/60:.1f}分钟"
        else:
            duration_str = f"{duration/3600:.1f}小时"
        st.metric("时间跨度", duration_str)


def main():
    st.set_page_config(page_title="Android 性能监控", layout="wide")
    st.title("Android 性能监控 - 折线图")

    files = list_csv_files()
    if not files:
        st.warning("未发现数据文件，请先启动采集。")
        st.stop()

    with st.sidebar:
        st.header("⚙️ 配置选项")
        
        # 文件选择
        selected = st.selectbox("📁 数据文件", options=files, index=len(files) - 1)
        
        # 时间范围筛选
        st.subheader("🕐 时间筛选")
        time_options = [
            "全部数据",
            "最近5分钟", 
            "最近15分钟", 
            "最近30分钟", 
            "最近1小时",
            "最近3小时",
            "自定义时间"
        ]
        time_range = st.selectbox("时间范围", options=time_options, index=0)
        
        custom_start = None
        custom_end = None
        
        # 自定义时间选择
        if time_range == "自定义时间":
            st.caption("选择具体时间范围：")
            custom_start = st.time_input("开始时间", value=None)
            custom_end = st.time_input("结束时间", value=None)
        
        # 刷新设置
        st.subheader("🔄 自动刷新")
        refresh_sec = st.number_input("刷新间隔(秒)", min_value=1, max_value=60, value=3)
        
        st.caption("---")
        st.caption("💡 提示：选择时间范围可以聚焦查看特定时段的性能数据")

    st_autorefresh(interval=refresh_sec * 1000, key="autoreload")

    # 加载数据
    df = load_csv(selected)
    if df.empty:
        st.stop()
    
    # 转换自定义时间为datetime（如果需要）
    if time_range == "自定义时间" and custom_start and custom_end:
        today = datetime.now().date()
        custom_start = datetime.combine(today, custom_start)
        custom_end = datetime.combine(today, custom_end)
    
    # 应用时间筛选
    df_filtered = filter_by_time_range(df, time_range, custom_start, custom_end)
    
    if df_filtered.empty:
        st.warning("⚠️ 所选时间范围内没有数据")
        st.stop()
    
    # 显示数据摘要
    display_data_summary(df_filtered)

    # Charts - 使用筛选后的数据
    st.subheader("应用性能")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if "app_cpu_percent" in df_filtered.columns:
            st.markdown("**CPU 占用 (%)**")
            st.line_chart(df_filtered[["timestamp", "app_cpu_percent"]].set_index("timestamp"))
            
        if "fps" in df_filtered.columns:
            st.markdown("**FPS**")
            st.line_chart(df_filtered[["timestamp", "fps"]].set_index("timestamp"))

    with col2:
        if "app_mem_kb" in df_filtered.columns:
            # 转换为 MB 显示
            df_filtered = df_filtered.copy()
            df_filtered["app_mem_mb"] = df_filtered["app_mem_kb"] / 1024
            st.markdown("**内存占用 (MB)**")
            st.line_chart(df_filtered[["timestamp", "app_mem_mb"]].set_index("timestamp"))
            
        if "jank_rate" in df_filtered.columns:
            st.markdown("**卡顿率 (%)**")
            st.line_chart(df_filtered[["timestamp", "jank_rate"]].set_index("timestamp"))

            
if __name__ == "__main__":
    main()

