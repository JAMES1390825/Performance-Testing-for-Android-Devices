import os
import glob
import time
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import altair as alt


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


def main():
    st.set_page_config(page_title="Android 性能监控", layout="wide")
    st.title("Android 性能监控 - 折线图")

    files = list_csv_files()
    if not files:
        st.warning("未发现数据文件，请先启动采集。")
        st.stop()

    with st.sidebar:
        selected = st.selectbox("数据文件", options=files, index=len(files) - 1)
        refresh_sec = st.number_input("刷新间隔(秒)", min_value=1, max_value=60, value=3)
        st.caption("侧边栏可切换最新文件与刷新周期")

    st_autorefresh(interval=refresh_sec * 1000, key="autoreload")

    df = load_csv(selected)
    if df.empty:
        st.stop()

    # Charts
    left, right = st.columns(2)

    with left:
        if "total_cpu_percent" in df.columns:
            st.subheader("总CPU占用(%)")
            st.line_chart(df[["timestamp", "total_cpu_percent"]].set_index("timestamp"))
        if "mem_used_percent" in df.columns:
            st.subheader("内存使用率(%)")
            st.line_chart(df[["timestamp", "mem_used_percent"]].set_index("timestamp"))

    with right:
        if "battery_level" in df.columns:
            st.subheader("电量(%)")
            st.line_chart(df[["timestamp", "battery_level"]].set_index("timestamp"))
        if "battery_temp_c" in df.columns:
            st.subheader("电池温度(℃)")
            st.line_chart(df[["timestamp", "battery_temp_c"]].set_index("timestamp"))

    if "app_cpu_percent" in df.columns or "app_mem_kb" in df.columns:
        st.subheader("应用维度")
        
        if "app_cpu_percent" in df.columns:
            st.subheader("应用CPU占用(%)")
            st.line_chart(df[["timestamp", "app_cpu_percent"]].set_index("timestamp"))
            
        if "app_mem_kb" in df.columns:
            st.subheader("应用内存占用(KB)")
            st.line_chart(df[["timestamp", "app_mem_kb"]].set_index("timestamp"))
            
if __name__ == "__main__":
    main()

