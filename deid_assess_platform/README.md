# 去标识化及匿名化评估工具

## 项目简介

本工具旨在为企业提供一套**去标识化（De-identification）与匿名化（Anonymization）评估平台**，帮助数据处理团队快速完成数据隐私合规评估工作。

## 核心功能

- 数据接入：支持CSV、Excel、JSON、Parquet等本地文件导入
- 字段识别与分类：自动检测 + 人工修正
- 去标识化策略配置与执行：删除、泛化、抑制、分桶、扰动、简单K-匿名等
- 效果评估：直接标识符残留检查、等价类分布、唯一记录比例、重识别风险基础评分、可用性损失
- 报告导出：基础Word/PDF报告，包含关键指标和结论

## 技术栈

- **桌面界面**：PySide6（Qt for Python）
- **数据处理引擎**：Polars（高性能） + pandas（兼容）
- **后端/服务**：纯Python核心引擎
- **存储**：SQLite（单机版）
- **报告生成**：python-docx + docx2pdf
- **图表可视化**：matplotlib / plotly
- **打包工具**：PyInstaller

## 项目结构

```
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

## 安装与运行

### 1. 安装依赖

```bash
# 在项目根目录执行
pip install -r requirements.txt
```

### 2. 运行应用

```bash
# 在项目根目录执行
python main.py
```

### 3. 打包成可执行文件

```bash
# 在 build 目录执行
build_exe.bat
```

## 使用流程

1. **数据导入**：点击「导入文件」按钮，选择要处理的数据文件
2. **字段识别**：点击「自动识别字段」按钮，系统会自动分类字段类型，可手动修正
3. **去标识化**：为每个字段选择合适的去标识化策略，点击「执行去标识化」按钮
4. **效果评估**：点击「评估效果」按钮，系统会计算各项评估指标
5. **报告生成**：点击「生成报告」按钮，系统会生成评估报告并保存

## 注意事项

- 本工具为MVP版本，仅实现核心功能
- 支持的文件格式：CSV、Excel、JSON、Parquet
- 建议处理的数据量不超过10万行，以保证性能
- 报告生成功能需要安装 python-docx 库

## 后续规划

- 对抗性测试
- 不可复原性核验
- 完整证据中心与审计审批流
- 数据库/对象存储等复杂数据源接入
- 更丰富的去标识化策略
- 更详细的评估指标和报告
