import polars as pl

class Evaluator:
    def __init__(self):
        pass
    
    def evaluate(self, data, classified_fields, qi_columns=None):
        """
        评估去标识化效果
        :param data: 去标识化后的数据
        :param classified_fields: 字段分类
        :param qi_columns: 准标识符列（用于K匿名评估）
        :return: 评估结果
        """
        results = {}
        
        # 计算唯一记录比例
        unique_ratio = self._calculate_unique_ratio(data)
        results["唯一记录比例"] = f"{unique_ratio:.2%}"
        
        # 计算等价类分布
        eq_class_stats = self._calculate_equivalence_classes(data, qi_columns)
        results["等价类数量"] = eq_class_stats["count"]
        results["平均等价类大小"] = f"{eq_class_stats['mean']:.2f}"
        results["最小等价类大小"] = eq_class_stats["min"]
        results["最大等价类大小"] = eq_class_stats["max"]
        
        # 计算重识别风险基础评分
        reid_risk = self._calculate_reidentification_risk(data, classified_fields, qi_columns)
        results["重识别风险基础评分"] = f"{reid_risk:.2f}"
        
        # 计算可用性损失
        availability_loss = self._calculate_availability_loss(data, classified_fields)
        results["可用性损失"] = f"{availability_loss:.2%}"
        
        return results
    
    def _calculate_unique_ratio(self, data):
        """
        计算唯一记录比例
        """
        total_rows = len(data)
        if total_rows == 0:
            return 0
        
        # 计算唯一行的数量
        unique_rows = len(data.unique())
        return unique_rows / total_rows
    
    def _calculate_equivalence_classes(self, data, qi_columns=None):
        """
        计算等价类分布
        :param data: 数据
        :param qi_columns: 准标识符列（用于K匿名评估）
        """
        if len(data) == 0:
            return {"count": 0, "mean": 0, "min": 0, "max": 0}
        
        # 确定分组列
        if qi_columns and all(col in data.columns for col in qi_columns):
            # 使用准标识符列分组
            group_columns = qi_columns
        else:
            # 否则使用所有列分组
            group_columns = data.columns
        
        # 按分组列分组，计算每组大小
        try:
            grouped = data.group_by(group_columns).agg(pl.count())
            class_sizes = grouped["count"].to_list()
            
            if not class_sizes:
                return {"count": 0, "mean": 0, "min": 0, "max": 0}
            
            return {
                "count": len(class_sizes),
                "mean": sum(class_sizes) / len(class_sizes),
                "min": min(class_sizes),
                "max": max(class_sizes)
            }
        except:
            # 如果分组失败，返回默认值
            return {"count": 0, "mean": 0, "min": 0, "max": 0}
    
    def _calculate_reidentification_risk(self, data, classified_fields, qi_columns=None):
        """
        计算重识别风险基础评分
        :param data: 数据
        :param classified_fields: 字段分类
        :param qi_columns: 准标识符列（用于K匿名评估）
        """
        if len(data) == 0:
            return 0
        
        # 基于唯一记录比例和等价类大小计算风险
        unique_ratio = self._calculate_unique_ratio(data)
        eq_class_stats = self._calculate_equivalence_classes(data, qi_columns)
        
        # 风险评分公式：唯一记录比例越高，风险越高；等价类平均大小越小，风险越高
        risk_score = (unique_ratio * 0.7) + ((1 / max(eq_class_stats["mean"], 1)) * 0.3)
        
        # 归一化到0-100分
        return min(risk_score * 100, 100)
    
    def _calculate_availability_loss(self, data, classified_fields):
        """
        计算可用性损失
        """
        if len(data) == 0:
            return 1
        
        # 基于被处理字段的比例和处理方式计算可用性损失
        processed_fields = 0
        total_fields = len(data.columns)
        
        if total_fields == 0:
            return 1
        
        for column in data.columns:
            # 检查字段是否被处理（简化处理，实际应根据具体策略评估）
            if classified_fields.get(column) in ["direct", "quasi", "sensitive"]:
                processed_fields += 1
        
        # 简单计算：处理的字段比例越高，可用性损失越大
        return processed_fields / total_fields
