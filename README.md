# 营销数据分析工具
## 实验介绍
基于Streamlit实现的CSV营销数据分析工具，支持必填字段校验、分组统计、可视化与品牌筛选，兼容带空值的数据。
### 功能清单
1. CSV上传，校验必填字段：brand、price、rating
2. 按brand分组，计算price、rating均值，空值不参与计算
3. 绘制各品牌平均rating柱状图
4. 品牌下拉筛选，只改变视图，不改动原始数据

## 测试文件说明
- marketing_data.csv：字段完整的正常测试数据
- marketing_data_missing_rating.csv：缺少rating字段，用于校验失败测试
- null_value.csv：字段完整，包含空值，测试空值容错

## 启动命令