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
import json
import re

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
PROJECT_ROOT = Path(__file__).resolve().parent
SKILL_PATH = PROJECT_ROOT / "skills" / "consumer-insight-skill" / "SKILL.md"
SCHEMA_DIR = PROJECT_ROOT / "schemas"
INSIGHT_FIELDS = [
    "sentiment",
    "need",
    "pain_point",
    "scenario",
    "purchase_barrier",
    "evidence",
    "confidence",
]


def load_skill_rules():
    """读取消费者洞察 Skill，作为页面运行时的规则来源。"""
    if not SKILL_PATH.exists():
        return ""
    return SKILL_PATH.read_text(encoding="utf-8")


def load_insight_schema():
    """读取 schemas 目录中的消费者洞察 JSON Schema。"""
    candidates = [SCHEMA_DIR / "consumer_insight.schema.json"]
    candidates.extend(sorted(SCHEMA_DIR.rglob("*.json")))
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
    return {}


def _first_match(text, patterns):
    """返回原文中第一个命中的最小片段，确保 evidence 可追溯。"""
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def _insight_for_review(review_id, review_text):
    """按 Skill 标签字典对单条 review_text 做可审计的确定性编码。"""
    original = "" if review_text is None else str(review_text)
    text = original.strip()
    unknown = "unknown"
    if not text or not re.search(r"\w|[^\W\d_]", text, flags=re.UNICODE):
        return {
            "review_id": str(review_id), "sentiment": unknown, "need": unknown,
            "pain_point": unknown, "scenario": unknown, "purchase_barrier": unknown,
            "evidence": unknown, "confidence": "low",
        }

    positive = _first_match(text, [r"非常满意", r"很满意", r"喜欢", r"舒服", r"清晰", r"安静", r"推荐", r"很好", r"不错", r"excellent", r"great"])
    negative = _first_match(text, [r"失望", r"糟糕", r"不好", r"难受", r"不舒服", r"太贵", r"贵", r"断连", r"掉线", r"漏音", r"杂音", r"耗电快", r"不耐用", r"坏了", r"差", r"差劲"])
    if positive and negative:
        sentiment = "mixed"
    elif negative:
        sentiment = "negative"
    elif positive:
        sentiment = "positive"
    elif _first_match(text, [r"一般", r"还行", r"普通", r"没什么特别"]):
        sentiment = "neutral"
    else:
        sentiment = unknown

    needs = [
        ("降噪", [r"降噪", r"安静", r"noise\s*cancel"]), ("佩戴舒适", [r"舒适", r"舒服", r"夹耳", r"硌耳"]),
        ("续航", [r"续航", r"电池", r"电量", r"耗电"]), ("音质", [r"音质", r"低音", r"高音", r"声音"]),
        ("通话", [r"通话", r"麦克风", r"语音"]), ("连接稳定", [r"连接", r"断连", r"掉线", r"蓝牙"]),
        ("便携", [r"便携", r"轻便", r"折叠", r"小巧"]), ("性价比", [r"性价比", r"值得", r"价格"]),
        ("外观", [r"外观", r"颜值", r"好看", r"颜色"]),
    ]
    need, need_evidence = unknown, None
    for label, patterns in needs:
        need_evidence = _first_match(text, patterns)
        if need_evidence:
            need = label
            break

    scenarios = [("通勤", [r"通勤", r"地铁", r"公交" ]), ("学习", [r"学习", r"图书馆"]), ("办公", [r"办公", r"办公室", r"工作"]), ("运动", [r"运动", r"跑步", r"健身"]), ("旅行", [r"旅行", r"飞机", r"旅途"]), ("通话", [r"通话", r"会议"]), ("居家", [r"家里", r"居家", r"在家"])]
    scenario, scenario_evidence = unknown, None
    for label, patterns in scenarios:
        scenario_evidence = _first_match(text, patterns)
        if scenario_evidence:
            scenario = label
            break

    barrier_patterns = [("价格", [r"太贵", r"贵", r"价格高", r"买不起"]), ("舒适度担忧", [r"担心.*舒服", r"怕.*硌", r"舒适度"]), ("质量担忧", [r"担心.*质量", r"不耐用", r"容易坏"]), ("功能不足", [r"功能不够", r"没有.*功能", r"缺少"]), ("售后担忧", [r"售后", r"保修"])]
    barrier, barrier_evidence = "无", None
    for label, patterns in barrier_patterns:
        barrier_evidence = _first_match(text, patterns)
        if barrier_evidence:
            barrier = label
            break

    pain = _first_match(text, [r"不舒服", r"夹耳", r"硌耳", r"断连", r"掉线", r"漏音", r"杂音", r"耗电快", r"续航短", r"太贵", r"价格高", r"不耐用", r"容易坏"])
    pain_point = pain if pain else ("none" if sentiment in {"positive", "neutral"} else unknown)
    evidence = next((candidate for candidate in [pain, negative, positive, need_evidence, scenario_evidence, barrier_evidence] if candidate), unknown)
    confidence = "high" if evidence != unknown and (positive or negative or need_evidence or scenario_evidence) else ("medium" if evidence != unknown else "low")
    return {"review_id": str(review_id), "sentiment": sentiment, "need": need, "pain_point": pain_point, "scenario": scenario, "purchase_barrier": barrier, "evidence": evidence, "confidence": confidence}


def analyze_reviews(dataframe):
    """使用 review_text 生成逐条、可下载的固定字段洞察结果。"""
    if "review_text" not in dataframe.columns:
        raise ValueError("CSV 必须包含 review_text 列。")
    results = []
    for index, row in dataframe.iterrows():
        review_id = row.get("review_id", f"row-{index + 1}")
        if pd.isna(review_id) or str(review_id).strip() == "":
            review_id = f"row-{index + 1}"
        results.append(_insight_for_review(review_id, row.get("review_text")))
    return results


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

    # 消费者洞察使用上传文件中的原始 review_text，不经过筛选或数值清洗。
    if "review_text" in dataframe.columns:
        st.subheader("消费者洞察分析")
        st.caption("依据 skills/consumer-insight-skill/SKILL.md 与 schemas/consumer_insight.schema.json 编码；evidence 始终来自原始 review_text。")
        # 在页面加载时读取规则和 schema，便于部署后规则文件变更立即生效。
        skill_rules = load_skill_rules()
        insight_schema = load_insight_schema()
        if not skill_rules:
            st.warning("未找到消费者洞察 Skill 文件，将使用内置规则。")
        if not insight_schema:
            st.warning("未找到消费者洞察 JSON Schema。")
        if st.session_state.get("consumer_insight_source") != source_name:
            st.session_state.pop("consumer_insights", None)
            st.session_state.consumer_insight_source = source_name
        run_insights = st.button(
            "运行消费者洞察分析",
            type="primary",
            disabled=uploaded_file is None or dataframe.empty,
            key="run_consumer_insights",
            help="请先上传包含 review_text 的 reviews_300.csv。" if uploaded_file is None else None,
        )
        if run_insights:
            with st.spinner("正在分析 review_text…"):
                try:
                    st.session_state.consumer_insights = analyze_reviews(dataframe)
                    st.session_state.consumer_insight_source = source_name
                except ValueError as exc:
                    st.error(str(exc))
        insights = st.session_state.get("consumer_insights")
        if insights:
            st.success(f"已生成 {len(insights):,} 条消费者洞察。")
            st.json(insights)
            st.download_button(
                "下载 JSON 结果",
                data=json.dumps(insights, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="consumer_insights.json",
                mime="application/json",
                key="download_consumer_insights",
            )

        # reviews_300.csv 通常没有营销聚合所需的 brand/price/rating，仍继续展示原始数据预览。
        missing_columns = validate_columns(dataframe)
        if missing_columns:
            st.subheader("数据预览")
            st.dataframe(dataframe, use_container_width=True, hide_index=True)
            return

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
