# 去标识化及匿名化评估工具开发文档

## 1. 项目背景与目标

本工具旨在为企业提供一套**去标识化（De-identification）与匿名化（Anonymization）评估平台**，帮助数据处理团队快速完成数据隐私合规评估工作。

**核心价值**：
- 自动化识别数据中的直接标识符、准标识符和敏感属性
- 支持多种去标识化策略的配置与执行
- 对去标识化效果进行量化评估（重识别风险、可用性损失等）
- 生成合规评估报告

**当前阶段**：首版MVP（Minimum Viable Product），目标是让**核心闭环快速跑通**，后续再迭代高级功能。

## 2. 首版交付目标（MVP范围）

### 必须完成的核心闭环（P0）
- 数据接入：支持CSV、Excel、JSON、Parquet等本地文件导入
- 字段识别与分类：自动检测 + 人工修正
- 去标识化策略配置与执行：删除、泛化、抑制、分桶、扰动、简单K-匿名等
- 效果评估：直接标识符残留检查、等价类分布、唯一记录比例、重识别风险基础评分、可用性损失
- 报告导出：基础Word/PDF报告，包含关键指标和结论

### 二期暂不实现的功能（P1）
- 对抗性测试
- 不可复原性核验
- 完整证据中心与审计审批流
- 数据库/对象存储等复杂数据源接入

## 3. 推荐首版技术栈

- **桌面界面**：**PySide6**（Qt for Python）—— 成熟、表格支持好、打包exe方便
- **数据处理引擎**：**Polars**（首选，高性能） + **pandas**（兼容）
- **后端/服务**：纯Python核心引擎（可嵌入FastAPI本地服务）
- **存储**：**SQLite**（单机版）
- **报告生成**：**python-docx** + **docx2pdf**
- **图表可视化**：**matplotlib** / **plotly**
- **打包工具**：**PyInstaller**

**整体架构**：PySide6 主界面 + Python 核心引擎（单进程调用，首版优先简化）。

## 4. 项目文件夹结构
```text
deid_assess_platform/
├── main.py                 # 启动入口
├── requirements.txt
├── build/
│   └── build_exe.bat
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   └── components/
│       ├── __init__.py
│       ├── data_table.py
│       └── wizard.py
├── core/
│   ├── __init__.py
│   ├── models.py
│   ├── classifier.py       # 字段识别
│   ├── deidentify.py       # 去标识化执行
│   ├── evaluate.py         # 效果评估
│   └── report.py           # 报告生成
├── data/
│   └── projects.db
├── config/
│   ├── __init__.py
│   └── rules.json          # 识别规则
├── templates/
│   └── report_template.docx
└── utils/
    ├── __init__.py
    └── logger.py
```

## 5. 核心模块说明

### 5.1 字段识别（classifier.py）
- 基于规则匹配列名（姓名、身份证、手机号等）
- 结合样本值简单判断
- 输出字段分类：direct / quasi / sensitive / non

### 5.2 去标识化执行（deidentify.py）
- 支持策略：delete/suppress、generalize、hash 等
- 可针对不同字段类型应用相应处理

### 5.3 效果评估（evaluate.py）
- 唯一记录比例
- 等价类大小分布与平均值
- 重识别风险基础评分
- 可用性损失计算

### 5.4 报告生成（report.py）
- 使用python-docx自动填充模板
- 输出包含评估指标和结论的Word文档

## 6. 详细代码实现

（以下为首版完整可运行代码，已在文档中整合）

### requirements.txt
```txt
PySide6==6.7.2
polars==1.9.0
pandas==2.2.2
python-docx==1.1.2
matplotlib==3.9.2
plotly==5.24.1