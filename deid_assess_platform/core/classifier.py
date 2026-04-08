import re
import polars as pl

class Classifier:
    def __init__(self):
        # 直接标识符规则
        self.direct_patterns = [
            r'姓名', r'name', r'fullname',
            r'身份证', r'idcard', r'identity', r'id_number',
            r'手机号', r'phone', r'mobile', r'cellphone',
            r'邮箱', r'email', r'mail',
            r'地址', r'address',
            r'银行卡', r'bank', r'card',
            r'护照', r'passport',
            r'社保', r'social', r'insurance',
            r'驾照', r'driver', r'license'
        ]
        
        # 准标识符规则
        self.quasi_patterns = [
            r'年龄', r'age',
            r'性别', r'gender', r'sex',
            r'出生日期', r'birth', r'dob',
            r'邮编', r'zip', r'postal',
            r'地区', r'region', r'area',
            r'职业', r'occupation', r'job',
            r'教育', r'education', r'school'
        ]
        
        # 敏感属性规则
        self.sensitive_patterns = [
            r'健康', r'health', r'medical',
            r'疾病', r'disease', r'illness',
            r'诊断', r'diagnosis',
            r'治疗', r'treatment',
            r'用药', r'medicine', r'drug',
            r'基因', r'gene',
            r'生物', r'biometric',
            r'收入', r'income', r'salary',
            r'财务', r'finance', r'financial',
            r'宗教', r'religion',
            r'政治', r'political',
            r'民族', r'ethnicity', r'race'
        ]
    
    def classify(self, data):
        classified_fields = {}
        
        for column in data.columns:
            classification = self._classify_column(column, data[column])
            classified_fields[column] = classification
        
        return classified_fields
    
    def _classify_column(self, column_name, series):
        # 先基于列名匹配
        column_lower = column_name.lower()
        
        # 检查直接标识符
        for pattern in self.direct_patterns:
            if re.search(pattern.lower(), column_lower):
                return "direct"
        
        # 检查准标识符
        for pattern in self.quasi_patterns:
            if re.search(pattern.lower(), column_lower):
                return "quasi"
        
        # 检查敏感属性
        for pattern in self.sensitive_patterns:
            if re.search(pattern.lower(), column_lower):
                return "sensitive"
        
        # 基于样本值进行进一步判断
        sample = series.head(10).to_list()
        
        # 检查身份证号格式
        id_card_pattern = r'^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[0-9Xx]$'
        if any(re.match(id_card_pattern, str(value)) for value in sample if str(value)):
            return "direct"
        
        # 检查手机号格式
        phone_pattern = r'^1[3-9]\d{9}$'
        if any(re.match(phone_pattern, str(value)) for value in sample if str(value)):
            return "direct"
        
        # 检查邮箱格式
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if any(re.match(email_pattern, str(value)) for value in sample if str(value)):
            return "direct"
        
        # 默认分类为非敏感
        return "non"
