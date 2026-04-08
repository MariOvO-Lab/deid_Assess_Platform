import polars as pl
import hashlib
import random
from collections import defaultdict

class Deidentifier:
    def __init__(self):
        pass
    
    def deidentify(self, data, strategies):
        """
        执行去标识化处理
        :param data: 原始数据
        :param strategies: 字段策略映射
        :return: 去标识化后的数据
        """
        deid_data = data.clone()
        
        # 检查是否需要执行K匿名
        if "k_anonymity" in strategies:
            k_value = strategies.get("k_value", 5)
            qi_columns = strategies.get("qi_columns", [])
            if qi_columns:
                deid_data = self._k_anonymize(deid_data, qi_columns, k_value)
        else:
            # 执行其他去标识化策略
            for column, strategy in strategies.items():
                if column in deid_data.columns:
                    if strategy == "delete":
                        deid_data = deid_data.drop(column)
                    elif strategy == "suppress":
                        deid_data = deid_data.with_columns(
                            pl.lit("[已抑制]").alias(column)
                        )
                    elif strategy == "hash":
                        deid_data = deid_data.with_columns(
                            deid_data[column].map_elements(self._hash_value).alias(column)
                        )
                    elif strategy == "generalize_age":
                        deid_data = deid_data.with_columns(
                            deid_data[column].map_elements(self._generalize_age).alias(column)
                        )
                    elif strategy == "generalize_gender":
                        deid_data = deid_data.with_columns(
                            pl.lit("[性别]").alias(column)
                        )
                    elif strategy == "perturb":
                        deid_data = deid_data.with_columns(
                            deid_data[column].map_elements(self._perturb_value).alias(column)
                        )
        
        return deid_data
    
    def _k_anonymize(self, data, qi_columns, k=5):
        """
        执行K匿名处理
        :param data: 原始数据
        :param qi_columns: 准标识符列
        :param k: K值
        :return: K匿名化后的数据
        """
        # 直接使用polars进行处理，避免使用pandas和pyarrow
        deid_data = data.clone()
        
        # 对每个准标识符列进行泛化
        for col in qi_columns:
            if col in deid_data.columns:
                # 尝试获取列的数据类型
                try:
                    # 检查是否为数值型列
                    is_numeric = deid_data[col].dtype in [pl.Int32, pl.Int64, pl.Float32, pl.Float64]
                    
                    if is_numeric:
                        # 数值型列，使用区间泛化
                        deid_data = deid_data.with_columns(
                            deid_data[col].map_elements(self._generalize_numeric).alias(col)
                        )
                    else:
                        # 类别型列，使用更粗的分类
                        deid_data = deid_data.with_columns(
                            deid_data[col].map_elements(self._generalize_categorical).alias(col)
                        )
                except:
                    # 如果类型检查失败，使用类别型泛化
                    deid_data = deid_data.with_columns(
                        deid_data[col].map_elements(self._generalize_categorical).alias(col)
                    )
        
        # 检查等价类大小，确保满足K匿名（最多迭代10次）
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            # 计算等价类
            # 使用polars的groupby操作
            if qi_columns:
                try:
                    # 尝试使用groupby计算等价类大小
                    eq_sizes = deid_data.groupby(qi_columns).agg(pl.count())
                    
                    # 检查是否所有等价类大小都 >= k
                    if eq_sizes.shape[0] > 0:
                        min_size = eq_sizes.select(pl.min("count")).item()
                        if min_size >= k:
                            break
                except:
                    # 如果groupby失败，直接退出循环
                    break
            
            # 如果不满足，进一步泛化
            for col in qi_columns:
                if col in deid_data.columns:
                    try:
                        # 检查是否为数值型列
                        is_numeric = deid_data[col].dtype in [pl.Int32, pl.Int64, pl.Float32, pl.Float64]
                        
                        if is_numeric:
                            # 进一步泛化数值列
                            deid_data = deid_data.with_columns(
                                deid_data[col].map_elements(lambda x: self._generalize_numeric(x, 2)).alias(col)
                            )
                        else:
                            # 进一步泛化类别列
                            deid_data = deid_data.with_columns(
                                deid_data[col].map_elements(lambda x: self._generalize_categorical(x, 2)).alias(col)
                            )
                    except:
                        # 如果类型检查失败，使用类别型泛化
                        deid_data = deid_data.with_columns(
                            deid_data[col].map_elements(lambda x: self._generalize_categorical(x, 2)).alias(col)
                        )
            
            iteration += 1
        
        return deid_data
    
    def _hash_value(self, value):
        """
        对值进行哈希处理
        """
        if value is None:
            return value
        return hashlib.md5(str(value).encode()).hexdigest()
    
    def _generalize_age(self, age, level=1):
        """
        年龄泛化
        """
        if age is None:
            return age
        try:
            age = int(age)
            if level == 0:
                return str(age)
            elif level == 1:
                low = (age // 10) * 10
                return f"{low}-{low+9}"
            elif level == 2:
                low = (age // 20) * 20
                return f"{low}-{low+19}"
            else:
                return "*"
        except:
            return age
    
    def _generalize_numeric(self, value, level=1):
        """
        数值泛化
        """
        if value is None:
            return value
        try:
            value = float(value)
            if level == 1:
                # 泛化为10的倍数区间
                low = (int(value) // 10) * 10
                return f"{low}-{low+9}"
            elif level == 2:
                # 泛化为20的倍数区间
                low = (int(value) // 20) * 20
                return f"{low}-{low+19}"
            else:
                return "*"
        except:
            return value
    
    def _generalize_categorical(self, value, level=1):
        """
        类别泛化
        """
        if value is None:
            return value
        if level == 1:
            # 简单泛化，返回首字母或更粗的分类
            return str(value)[0] if str(value) else value
        else:
            return "*"
    
    def _perturb_value(self, value):
        """
        数值扰动
        """
        if value is None:
            return value
        try:
            value = float(value)
            # 添加随机扰动，范围为原值的±5%
            perturbation = value * random.uniform(-0.05, 0.05)
            return round(value + perturbation, 2)
        except:
            return value
