from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QLabel, QTableWidget, QTableWidgetItem, QComboBox, QGridLayout, QGroupBox, QCheckBox, QMessageBox, QScrollArea, QTextEdit
from PySide6.QtCore import Qt
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.classifier import Classifier
from core.deidentify import Deidentifier
from core.evaluate import Evaluator
from core.report import ReportGenerator
import polars as pl

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("去标识化及匿名化评估工具")
        self.setGeometry(100, 100, 1200, 800)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)
        
        # 创建标签页
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        
        # 数据导入标签
        self.data_tab = QWidget()
        self.tabs.addTab(self.data_tab, "数据导入")
        self.setup_data_tab()
        
        # 字段识别标签
        self.classify_tab = QWidget()
        self.tabs.addTab(self.classify_tab, "字段识别")
        self.setup_classify_tab()
        
        # 去标识化标签
        self.deid_tab = QWidget()
        self.tabs.addTab(self.deid_tab, "去标识化")
        self.setup_deid_tab()
        
        # 评估标签
        self.evaluate_tab = QWidget()
        self.tabs.addTab(self.evaluate_tab, "效果评估")
        self.setup_evaluate_tab()
        
        # 报告标签
        self.report_tab = QWidget()
        self.tabs.addTab(self.report_tab, "报告生成")
        self.setup_report_tab()
        
        # 数据存储
        self.data = None  # 原始数据
        self.deid_data = None  # 去标识化后的数据（无论是平台生成的还是用户上传的）
        self.uploaded_deid_data = None  # 用户上传的去标识化数据
        self.classified_fields = {}
        self.deid_strategies = {}
        self.evaluation_results = {}
        self.qi_columns = []  # 存储准标识符列
        self.k_meta = None  # K-匿名元信息
    
    def setup_data_tab(self):
        layout = QVBoxLayout()
        self.data_tab.setLayout(layout)
        
        # 原始数据导入
        original_layout = QHBoxLayout()
        self.import_original_btn = QPushButton("导入原始文件")
        self.import_original_btn.clicked.connect(self.import_original_file)
        original_layout.addWidget(self.import_original_btn)
        self.original_file_label = QLabel("未选择文件")
        original_layout.addWidget(self.original_file_label)
        layout.addLayout(original_layout)
        
        # 匿名化数据导入
        deid_layout = QHBoxLayout()
        self.import_deid_btn = QPushButton("导入匿名化文件")
        self.import_deid_btn.clicked.connect(self.import_deid_file)
        deid_layout.addWidget(self.import_deid_btn)
        self.deid_file_label = QLabel("未选择文件")
        deid_layout.addWidget(self.deid_file_label)
        layout.addLayout(deid_layout)
        
        # 数据预览表格
        self.data_table = QTableWidget()
        layout.addWidget(self.data_table)
    
    def import_original_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择原始文件", "", "数据文件 (*.csv *.xlsx *.json *.parquet)"
        )
        if file_path:
            self.original_file_label.setText(file_path)
            # 读取文件
            try:
                if file_path.endswith('.csv'):
                    self.data = pl.read_csv(file_path)
                elif file_path.endswith('.xlsx'):
                    self.data = pl.read_excel(file_path)
                elif file_path.endswith('.json'):
                    self.data = pl.read_json(file_path)
                elif file_path.endswith('.parquet'):
                    self.data = pl.read_parquet(file_path)
                else:
                    self.original_file_label.setText("不支持的文件格式")
                    return
                
                # 显示数据预览
                self.update_data_table(data=self.data)
            except Exception as e:
                self.original_file_label.setText(f"读取失败: {str(e)}")
    
    def import_deid_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择匿名化文件", "", "数据文件 (*.csv *.xlsx *.json *.parquet)"
        )
        if file_path:
            self.deid_file_label.setText(file_path)
            # 读取文件
            try:
                if file_path.endswith('.csv'):
                    self.uploaded_deid_data = pl.read_csv(file_path)
                elif file_path.endswith('.xlsx'):
                    self.uploaded_deid_data = pl.read_excel(file_path)
                elif file_path.endswith('.json'):
                    self.uploaded_deid_data = pl.read_json(file_path)
                elif file_path.endswith('.parquet'):
                    self.uploaded_deid_data = pl.read_parquet(file_path)
                else:
                    self.deid_file_label.setText("不支持的文件格式")
                    return
                
                # 显示数据预览
                self.update_data_table(data=self.uploaded_deid_data)
            except Exception as e:
                self.deid_file_label.setText(f"读取失败: {str(e)}")
    
    def update_data_table(self, data=None):
        # 如果没有提供数据，使用原始数据
        preview_data = data if data is not None else self.data
        
        if preview_data is not None:
            # 不限制预览行数，显示完整数据
            rows, cols = preview_data.shape
            
            # 限制显示行数，避免性能问题
            display_rows = min(1000, rows)
            preview_data = preview_data.head(display_rows)
            
            self.data_table.setRowCount(display_rows)
            self.data_table.setColumnCount(cols)
            self.data_table.setHorizontalHeaderLabels(preview_data.columns)
            
            for i in range(display_rows):
                for j in range(cols):
                    value = preview_data[i, j]
                    self.data_table.setItem(i, j, QTableWidgetItem(str(value)))
    
    def setup_classify_tab(self):
        layout = QVBoxLayout()
        self.classify_tab.setLayout(layout)
        
        # 分类按钮
        classify_btn = QPushButton("自动识别字段")
        classify_btn.clicked.connect(self.classify_fields)
        layout.addWidget(classify_btn)
        
        # 字段分类表格
        self.classify_table = QTableWidget()
        layout.addWidget(self.classify_table)
    
    def classify_fields(self):
        # 优先使用原始数据进行字段分类
        classify_data = self.data
        
        if classify_data is None:
            return
        
        classifier = Classifier()
        self.classified_fields = classifier.classify(classify_data)
        
        # 显示分类结果
        cols = list(self.classified_fields.keys())
        rows = 1
        
        self.classify_table.setRowCount(rows)
        self.classify_table.setColumnCount(len(cols))
        self.classify_table.setHorizontalHeaderLabels(cols)
        
        for j, col in enumerate(cols):
            combo = QComboBox()
            combo.addItems(["direct", "quasi", "sensitive", "non"])
            combo.setCurrentText(self.classified_fields[col])
            combo.currentTextChanged.connect(lambda text, col=col: self.update_classification(col, text))
            self.classify_table.setCellWidget(0, j, combo)
        
        # 更新准标识符列表
        self.update_qi_list()
    
    def update_classification(self, column, classification):
        self.classified_fields[column] = classification
        # 更新准标识符列表
        self.update_qi_list()
    
    def update_qi_list(self):
        """
        更新准标识符选择列表
        """
        if not self.classified_fields:
            return
        
        # 清除现有列表
        self.qi_list_widget.setRowCount(0)
        
        # 添加字段和复选框
        for field, classification in self.classified_fields.items():
            row_position = self.qi_list_widget.rowCount()
            self.qi_list_widget.insertRow(row_position)
            
            # 添加字段名
            self.qi_list_widget.setItem(row_position, 0, QTableWidgetItem(field))
            
            # 添加复选框
            checkbox = QCheckBox()
            # 默认只选中准标识符，不选中敏感属性
            if classification == "quasi":
                checkbox.setChecked(True)
            else:
                checkbox.setChecked(False)
            self.qi_list_widget.setCellWidget(row_position, 1, checkbox)
    
    def setup_deid_tab(self):
        layout = QVBoxLayout()
        self.deid_tab.setLayout(layout)
        
        # K匿名配置
        k_anon_group = QGroupBox("K匿名配置")
        k_anon_layout = QVBoxLayout()
        k_anon_group.setLayout(k_anon_layout)
        
        # K值输入
        k_layout = QHBoxLayout()
        k_label = QLabel("K值:")
        self.k_value_input = QComboBox()
        self.k_value_input.addItems(["2", "3", "4", "5", "6", "7", "8", "9", "10"])
        self.k_value_input.setCurrentText("5")
        k_layout.addWidget(k_label)
        k_layout.addWidget(self.k_value_input)
        k_anon_layout.addLayout(k_layout)
        
        # 准标识符选择
        qi_layout = QVBoxLayout()
        qi_label = QLabel("准标识符:")
        qi_layout.addWidget(qi_label)
        self.qi_list_widget = QTableWidget()
        self.qi_list_widget.setColumnCount(2)
        self.qi_list_widget.setHorizontalHeaderLabels(["字段", "是否选择"])
        qi_layout.addWidget(self.qi_list_widget)
        k_anon_layout.addLayout(qi_layout)
        
        layout.addWidget(k_anon_group)
        
        # 执行按钮
        execute_btn = QPushButton("执行去标识化")
        execute_btn.clicked.connect(self.execute_deid)
        layout.addWidget(execute_btn)
        
        # 结果预览
        self.deid_result_table = QTableWidget()
        layout.addWidget(self.deid_result_table)
    
    def execute_deid(self):
        try:
            # 检查数据是否已导入
            if self.data is None:
                QMessageBox.warning(self, "警告", "请先导入数据文件！")
                return
            
            # 检查是否已进行字段分类
            if not self.classified_fields:
                QMessageBox.warning(self, "警告", "请先进行字段分类！")
                return
            
            # 收集K匿名配置
            k_value = int(self.k_value_input.currentText())
            qi_columns = []
            
            # 收集选中的准标识符
            for i in range(self.qi_list_widget.rowCount()):
                checkbox = self.qi_list_widget.cellWidget(i, 1)
                if checkbox.isChecked():
                    field_name = self.qi_list_widget.item(i, 0).text()
                    qi_columns.append(field_name)
            
            # 保存准标识符列
            self.qi_columns = qi_columns
            
            # 检查是否选择了准标识符
            if not qi_columns:
                QMessageBox.warning(self, "警告", "请至少选择一个准标识符！")
                return
            
            # 构建策略
            strategies = {
                "k_anonymity": True,
                "k_value": k_value,
                "qi_columns": qi_columns
            }
            
            # 执行去标识化
            deidentifier = Deidentifier()
            self.deid_data, self.k_meta = deidentifier.deidentify(self.data, strategies)
            
            # 显示结果预览
            if self.deid_data is not None:
                # 不限制预览行数，显示完整数据
                preview_data = self.deid_data
                rows, cols = preview_data.shape
                
                # 限制显示行数，避免性能问题
                display_rows = min(1000, rows)
                preview_data = self.deid_data.head(display_rows)
                
                self.deid_result_table.setRowCount(display_rows)
                self.deid_result_table.setColumnCount(cols)
                self.deid_result_table.setHorizontalHeaderLabels(preview_data.columns)
                
                for i in range(display_rows):
                    for j in range(cols):
                        value = preview_data[i, j]
                        self.deid_result_table.setItem(i, j, QTableWidgetItem(str(value)))
                
                # 显示成功消息
                QMessageBox.information(self, "成功", f"去标识化完成！处理了 {rows} 行数据，K值为 {k_value}。")
            else:
                QMessageBox.warning(self, "警告", "去标识化失败！")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行去标识化时发生错误：\n{str(e)}")
    
    def setup_evaluate_tab(self):
        layout = QVBoxLayout()
        self.evaluate_tab.setLayout(layout)
        
        # 评估按钮（放在顶部）
        evaluate_btn = QPushButton("评估效果")
        evaluate_btn.clicked.connect(self.evaluate)
        layout.addWidget(evaluate_btn)
        
        # 创建可滚动区域（关键修复）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(400)  # 给足够初始高度
        
        # 评估结果 GroupBox
        self.evaluate_group = QGroupBox("评估结果")
        self.evaluate_group_layout = QVBoxLayout()
        self.evaluate_group.setLayout(self.evaluate_group_layout)
        
        scroll.setWidget(self.evaluate_group)
        layout.addWidget(scroll)
        
    def evaluate(self):
       # 获取目标K值
        k_target = None
        try:
            if hasattr(self, 'k_value_input'):
                k_target = int(self.k_value_input.currentText())
        except (AttributeError, ValueError):
            pass

        # 收集准标识符（确保直接上传匿名化文件时也能正确获取）
        if hasattr(self, 'qi_list_widget'):
            qi_columns = []
            for i in range(self.qi_list_widget.rowCount()):
                checkbox = self.qi_list_widget.cellWidget(i, 1)
                if checkbox.isChecked():
                    field_name = self.qi_list_widget.item(i, 0).text()
                    qi_columns.append(field_name)
            self.qi_columns = qi_columns

        # 执行评估
        if self.data is not None and self.uploaded_deid_data is not None:
            evaluator = Evaluator()
            self.evaluation_results = evaluator.evaluate(
                self.data, 
                self.uploaded_deid_data, 
                self.classified_fields, 
                self.qi_columns,
                k_target=k_target
            )
        elif self.deid_data is not None:
            evaluator = Evaluator()
            self.evaluation_results = evaluator.evaluate(
                self.deid_data, 
                self.deid_data, 
                self.classified_fields, 
                self.qi_columns, 
                getattr(self, 'k_meta', None),
                k_target=k_target
            )
        else:
            QMessageBox.warning(self, "警告", "请先完成数据导入和去标识化！")
            return

        # 清空旧结果
        for i in reversed(range(self.evaluate_group_layout.count())):
            self.evaluate_group_layout.itemAt(i).widget().deleteLater()

        # 逐个显示评估结果（优化等价类展示）
        for key, value in self.evaluation_results.items():
            # 跳过不需要显示的字段
            if key in ["前5个最小等价类_格式化", "违规等价类_格式化", "original_rows", "deid_rows", "original_columns", "deid_columns"]:
                continue
                
            if key in ["前5个最小等价类", "违规等价类"] and isinstance(value, list):
                # 创建标题标签
                title_label = QLabel(f"<b>{key}：</b>")
                self.evaluate_group_layout.addWidget(title_label)

                if not value:
                    none_label = QLabel("（无符合条件的等价类）")
                    self.evaluate_group_layout.addWidget(none_label)
                    continue

                # 创建表格显示等价类
                table = QTableWidget()
                table.setRowCount(len(value))
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(["排名", "等价类大小", "准标识符取值组合"])

                for row_idx, cls in enumerate(value):
                    # 排名
                    table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))

                    # 大小
                    table.setItem(row_idx, 1, QTableWidgetItem(str(cls.get("size", 0))))

                    # 值组合 —— 优化为多行清晰格式
                    values = cls.get("values", {})
                    value_lines = []
                    for col in self.qi_columns:   # 使用当前有效的 qi_columns
                        val = values.get(col, "")
                        value_lines.append(f"{col}: {val}")
                    value_str = "\n".join(value_lines)

                    item = QTableWidgetItem(value_str)
                    item.setTextAlignment(0x0001 | 0x0080)  # 左对齐 + 垂直居中
                    table.setItem(row_idx, 2, item)

                # 表格样式优化
                table.resizeColumnsToContents()
                table.setMinimumWidth(850)
                table.setColumnWidth(0, 60)   # 排名
                table.setColumnWidth(1, 100)  # 大小
                table.setColumnWidth(2, 650)  # 值组合（给足够宽度）
                table.setWordWrap(True)       # 关键：允许自动换行
                table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 垂直滚动
                table.verticalHeader().setDefaultSectionSize(60)  # 增大行高，让多行更清晰

                self.evaluate_group_layout.addWidget(table)

            else:
                # 普通指标（保持单行显示）
                if isinstance(value, (int, float)):
                    display_value = f"{value:.4f}" if isinstance(value, float) else str(value)
                else:
                    display_value = str(value)
                label = QLabel(f"<b>{key}：</b> {display_value}")
                self.evaluate_group_layout.addWidget(label)

        # 底部间距
        spacer = QWidget()
        spacer.setMinimumHeight(20)
        self.evaluate_group_layout.addWidget(spacer)
    
    def setup_report_tab(self):
        layout = QVBoxLayout()
        self.report_tab.setLayout(layout)
        
        # 生成报告按钮
        report_btn = QPushButton("生成报告")
        report_btn.clicked.connect(self.generate_report)
        layout.addWidget(report_btn)
        
        # 报告状态
        self.report_label = QLabel("未生成报告")
        layout.addWidget(self.report_label)
    
    def generate_report(self):
        if not self.evaluation_results:
            return
        
        generator = ReportGenerator()
        report_path = generator.generate(self.evaluation_results)
        
        if report_path:
            self.report_label.setText(f"报告已生成: {report_path}")
