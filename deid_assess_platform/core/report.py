from docx import Document
from docx.shared import Inches
import datetime
import os

class ReportGenerator:
    def __init__(self):
        self.template_path = "templates/report_template.docx"
    
    def generate(self, evaluation_results):
        """
        生成评估报告
        :param evaluation_results: 评估结果
        :return: 报告文件路径
        """
        # 创建文档
        doc = Document()
        
        # 添加标题
        doc.add_heading('去标识化及匿名化评估报告', 0)
        
        # 添加报告生成时间
        doc.add_paragraph(f'报告生成时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        
        # 添加评估结果部分
        doc.add_heading('评估结果', level=1)
        
        # 添加评估指标表格
        table = doc.add_table(rows=1, cols=2)
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = '评估指标'
        hdr_cells[1].text = '结果'
        
        for key, value in evaluation_results.items():
            row_cells = table.add_row().cells
            row_cells[0].text = key
            row_cells[1].text = str(value)
        
        # 添加结论部分
        doc.add_heading('结论', level=1)
        
        # 基于评估结果生成结论
        reid_risk = float(evaluation_results.get('重识别风险基础评分', '0').replace('%', ''))
        availability_loss = float(evaluation_results.get('可用性损失', '0').replace('%', ''))
        
        if reid_risk < 30:
            risk_level = '低'
        elif reid_risk < 70:
            risk_level = '中'
        else:
            risk_level = '高'
        
        if availability_loss < 30:
            availability_level = '高'
        elif availability_loss < 70:
            availability_level = '中'
        else:
            availability_level = '低'
        
        conclusion = f"本次去标识化处理后的重识别风险等级为{risk_level}，数据可用性等级为{availability_level}。"
        doc.add_paragraph(conclusion)
        
        # 保存报告
        report_dir = "reports"
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
        
        report_filename = f"{report_dir}/deid_evaluation_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        doc.save(report_filename)
        
        return report_filename
