"""Streamlit 营销数据分析工具

功能：
1. 上传 CSV，或在未上传时读取 app.py 同目录下的 marketing_data.csv。
2. 校验必需字段：brand、price、rating。
3. 按品牌计算 price 和 rating 平均值，空值不参与计算。
4. 使用柱状图展示各品牌平均 rating。
5. 支持按品牌筛选数据，筛选只影响页面视图，不修改原始数据。
6. 兼容 rating、sales 等字段存在空值的 CSV。
"""

from pathlib import Path

import pandas as pd
import streamlit as st


# 页面基础设置
st.set_page_config(
    page_title="营销数据分析工具",
    page_icon="📊",
    layout="wide",
)

# 第一阶段要求保留的必需字段。
REQUIRED_COLUMNS = ["brand", "price", "rating"]
DEFAULT_CSV_PATH = Path(__file__).resolve().parent / "marketing_data.csv"


def load_csv(uploaded_file):
    """读取上传的 CSV 或项目目录中的默认 CSV。

    读取异常会转换为页面提示，并返回 None，避免程序直接崩溃。
    """
    try:
        if uploaded_file is not None:
            # 上传组件返回的对象可以直接传给 pandas.read_csv。
            return pd.read_csv(uploaded_file)

        if DEFAULT_CSV_PATH.exists():
            return pd.read_csv(DEFAULT_CSV_PATH)

        return None
    except UnicodeDecodeError:
        st.error("CSV 文件编码读取失败，请将文件保存为 UTF-8 编码后重试。")
    except pd.errors.EmptyDataError:
        st.error("CSV 文件为空，请上传包含表头和数据的有效文件。")
    except pd.errors.ParserError as exc:
        st.error(f"CSV 文件格式解析失败，请检查分隔符或引号设置。详细信息：{exc}")
    except OSError as exc:
        st.error(f"读取 CSV 文件时发生错误：{exc}")
    return None


def validate_columns(dataframe):
    """校验必需字段，并清理列名首尾空格。"""
    # 只清理列名，不修改数据单元格内容。
    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    return [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]


def prepare_analysis_data(dataframe):
    """创建用于分析的副本，安全处理数值字段中的空值或非数字内容。

    原始上传 DataFrame 不会被修改。无法转换为数字的值会变成 NaN，
    pandas 的 mean() 会自动忽略 NaN，因此不会导致程序崩溃。
    """
    analysis_data = dataframe.copy()

    # 将空字符串先视为空值，再将异常文本转为 NaN。
    for column in ["price", "rating"]:
        analysis_data[column] = pd.to_numeric(
            analysis_data[column].replace(r"^\s*$", pd.NA, regex=True),
            errors="coerce",
        )

    # 品牌为空时用展示标签替代，便于分组和下拉筛选；不回写原始数据。
    analysis_data["brand"] = analysis_data["brand"].fillna("（空品牌）").astype(str).str.strip()
    analysis_data.loc[analysis_data["brand"] == "", "brand"] = "（空品牌）"
    return analysis_data


def calculate_brand_summary(analysis_data):
    """按品牌计算平均价格和平均评分，空值不参与计算。"""
    summary = (
        analysis_data.groupby("brand", dropna=False)[["price", "rating"]]
        .mean()
        .reset_index()
        .rename(
            columns={
                "brand": "品牌",
                "price": "平均价格",
                "rating": "平均评分",
            }
        )
        .sort_values("品牌")
    )
    return summary


def main():
    """渲染 Streamlit 页面。"""
    st.title("营销数据分析工具")
    st.caption("上传营销数据，查看品牌价格与评分概览")

    st.subheader("1. 上传 CSV 文件")
    uploaded_file = st.file_uploader(
        "请选择营销数据 CSV 文件",
        type=["csv"],
        help="文件必须包含 brand、price、rating；product 和 sales 为可选字段。",
    )

    dataframe = load_csv(uploaded_file)
    if dataframe is None:
        if uploaded_file is None:
            st.info("请上传 CSV 文件，或将 marketing_data.csv 放在 app.py 所在目录。")
        return

    source_name = uploaded_file.name if uploaded_file is not None else DEFAULT_CSV_PATH.name
    st.success(f"已读取文件：{source_name}（{len(dataframe):,} 行，{len(dataframe.columns):,} 列）")

    st.subheader("2. 字段校验")
    missing_columns = validate_columns(dataframe)
    if missing_columns:
        missing_text = "、".join(missing_columns)
        required_text = "、".join(REQUIRED_COLUMNS)
        st.error(
            f"字段校验失败：缺少必需字段【{missing_text}】。\n\n"
            f"必须包含的字段：{required_text}。"
        )
        st.write("当前文件中的字段：", "、".join(map(str, dataframe.columns)) or "（无字段）")
        return

    st.success("字段校验通过：brand、price、rating 均已存在。")

    # 只在副本上做类型转换和空品牌处理，确保原始上传数据保持不变。
    analysis_data = prepare_analysis_data(dataframe)

    st.subheader("3. 品牌筛选")
    brand_options = ["全部品牌"] + sorted(analysis_data["brand"].unique().tolist())
    selected_brand = st.selectbox("选择品牌", options=brand_options)

    if selected_brand == "全部品牌":
        filtered_data = analysis_data
    else:
        # 布尔筛选只生成当前视图，不修改 analysis_data 或原始 dataframe。
        filtered_data = analysis_data[analysis_data["brand"] == selected_brand].copy()

    st.caption(f"当前视图显示 {len(filtered_data):,} 行数据。")

    st.subheader("4. 品牌平均值")
    summary = calculate_brand_summary(filtered_data)
    display_summary = summary.copy()
    display_summary["平均价格"] = display_summary["平均价格"].round(2)
    display_summary["平均评分"] = display_summary["平均评分"].round(2)
    st.dataframe(display_summary, use_container_width=True, hide_index=True)

    st.subheader("5. 各品牌平均评分")
    chart_data = summary[["品牌", "平均评分"]].dropna(subset=["平均评分"])
    if chart_data.empty:
        st.info("当前视图没有可用于计算平均评分的有效 rating 数据。")
    else:
        # Streamlit 柱状图使用品牌作为索引，展示每个品牌的平均评分。
        st.bar_chart(chart_data.set_index("品牌"), y="平均评分")

    st.subheader("6. 数据预览")
    # 这里展示筛选后的视图；原始上传文件仍保留在 dataframe 中且未被修改。
    st.dataframe(filtered_data, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
