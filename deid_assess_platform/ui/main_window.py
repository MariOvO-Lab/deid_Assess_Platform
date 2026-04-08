from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QLabel, QTableWidget, QTableWidgetItem, QComboBox, QGridLayout, QGroupBox, QCheckBox, QMessageBox
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
        self.data = None
        self.classified_fields = {}
        self.deid_strategies = {}
        self.evaluation_results = {}
        self.qi_columns = []  # 存储准标识符列
    
    def setup_data_tab(self):
        layout = QVBoxLayout()
        self.data_tab.setLayout(layout)
        
        # 导入按钮
        import_layout = QHBoxLayout()
        self.import_btn = QPushButton("导入文件")
        self.import_btn.clicked.connect(self.import_file)
        import_layout.addWidget(self.import_btn)
        self.file_label = QLabel("未选择文件")
        import_layout.addWidget(self.file_label)
        layout.addLayout(import_layout)
        
        # 数据预览表格
        self.data_table = QTableWidget()
        layout.addWidget(self.data_table)
    
    def import_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "数据文件 (*.csv *.xlsx *.json *.parquet)"
        )
        if file_path:
            self.file_label.setText(file_path)
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
                    self.file_label.setText("不支持的文件格式")
                    return
                
                # 显示数据预览
                self.update_data_table()
            except Exception as e:
                self.file_label.setText(f"读取失败: {str(e)}")
    
    def update_data_table(self):
        if self.data is not None:
            # 不限制预览行数，显示完整数据
            preview_data = self.data
            rows, cols = preview_data.shape
            
            # 限制显示行数，避免性能问题
            display_rows = min(1000, rows)
            preview_data = self.data.head(display_rows)
            
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
        if self.data is None:
            return
        
        classifier = Classifier()
        self.classified_fields = classifier.classify(self.data)
        
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
            # 默认选中准标识符和敏感属性
            if classification in ["quasi", "sensitive"]:
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
            self.deid_data = deidentifier.deidentify(self.data, strategies)
            
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
        
        # 评估按钮
        evaluate_btn = QPushButton("评估效果")
        evaluate_btn.clicked.connect(self.evaluate)
        layout.addWidget(evaluate_btn)
        
        # 评估结果
        self.evaluate_group = QGroupBox("评估结果")
        self.evaluate_group_layout = QVBoxLayout()
        self.evaluate_group.setLayout(self.evaluate_group_layout)
        layout.addWidget(self.evaluate_group)
    
    def evaluate(self):
        if self.deid_data is None:
            return
        
        evaluator = Evaluator()
        self.evaluation_results = evaluator.evaluate(self.deid_data, self.classified_fields, self.qi_columns)
        
        # 显示评估结果
        for i in reversed(range(self.evaluate_group_layout.count())):
            self.evaluate_group_layout.itemAt(i).widget().deleteLater()
        
        for key, value in self.evaluation_results.items():
            label = QLabel(f"{key}: {value}")
            self.evaluate_group_layout.addWidget(label)
    
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
