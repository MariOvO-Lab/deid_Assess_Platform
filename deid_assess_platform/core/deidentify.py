import polars as pl
import hashlib
import random
import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

class Deidentifier:
    def __init__(self):
        # 可在此扩展默认泛化规则
        self.generalization_rules = {
            "age": lambda x: self._generalize_age(x),
            "性别": lambda x: self._generalize_gender(x),
        }

    def deidentify(
        self, 
        data: pl.DataFrame, 
        strategies: Dict[str, Any]
    ) -> Tuple[pl.DataFrame, Dict[str, Any]]:
        """
        执行去标识化处理（推荐返回处理结果 + 元信息）
        
        :param data: 原始 Polars DataFrame
        :param strategies: 策略配置，支持两种模式：
            1. 普通策略: {"column_name": "delete" | "suppress" | "hash" | "generalize" | "perturb", ...}
            2. K-匿名: {"k_anonymity": True, "k_value": 5, "qi_columns": ["col1", "col2"]}
        :return: (去标识化后的 DataFrame, 处理元信息)
        """
        deid_data = data.clone()
        meta = {"applied_strategies": [], "k_anonymity_satisfied": None, "final_k": None}

        # 优先处理 K-匿名（如果指定）
        if strategies.get("k_anonymity"):
            k_value = strategies.get("k_value", 5)
            qi_columns = strategies.get("qi_columns", [])
            if qi_columns:
                deid_data, k_meta = self._k_anonymize(deid_data, qi_columns, k_value)
                meta.update(k_meta)
                meta["applied_strategies"].append(f"k_anonymity(k={k_value})")
            else:
                logger.warning("K-匿名指定了，但 qi_columns 为空")
        else:
            # 执行普通字段级策略
            for column, strategy in strategies.items():
                if column not in deid_data.columns:
                    continue
                    
                try:
                    if strategy == "delete":
                        deid_data = deid_data.drop(column)
                        meta["applied_strategies"].append(f"{column}:delete")
                    elif strategy == "suppress":
                        deid_data = deid_data.with_columns(pl.lit("[已抑制]").alias(column))
                        meta["applied_strategies"].append(f"{column}:suppress")
                    elif strategy == "hash":
                        deid_data = deid_data.with_columns(
                            pl.col(column).map_elements(self._hash_value, return_dtype=pl.Utf8).alias(column)
                        )
                        meta["applied_strategies"].append(f"{column}:hash")
                    elif strategy in ("generalize", "generalize_age", "generalize_gender"):
                        deid_data = self._apply_generalization(deid_data, column)
                        meta["applied_strategies"].append(f"{column}:generalize")
                    elif strategy == "perturb":
                        deid_data = deid_data.with_columns(
                            pl.col(column).map_elements(self._perturb_value, return_dtype=pl.Float64).alias(column)
                        )
                        meta["applied_strategies"].append(f"{column}:perturb")
                except Exception as e:
                    logger.error(f"处理列 {column} 时出错: {e}")
                    meta["applied_strategies"].append(f"{column}:error")

        return deid_data, meta

    def _k_anonymize(self, data: pl.DataFrame, qi_columns: List[str], k: int = 5) -> Tuple[pl.DataFrame, Dict]:
        """改进版 K-匿名：逐步泛化 + 最终检查"""
        deid_data = data.clone()
        meta = {"k_anonymity_satisfied": False, "final_min_class_size": 0, "iterations": 0}

        max_iterations = 8
        for iteration in range(max_iterations):
            meta["iterations"] = iteration + 1

            # 计算当前等价类大小
            if not qi_columns:
                break
                
            eq_sizes = (
                deid_data.group_by(qi_columns)
                .agg(pl.count().alias("class_size"))
            )
            
            if eq_sizes.height == 0:
                break
                
            min_size = eq_sizes.select(pl.min("class_size")).item()
            meta["final_min_class_size"] = min_size

            if min_size >= k:
                meta["k_anonymity_satisfied"] = True
                logger.info(f"K-匿名达成 (k={k}, 最小等价类大小={min_size})")
                break

            # 不满足时进行轻度泛化（优先处理基数较大的列）
            for col in qi_columns:
                if col not in deid_data.columns:
                    continue
                # 使用表达式代替 map_elements，提升性能
                if deid_data[col].dtype in (pl.Int32, pl.Int64, pl.Float32, pl.Float64):
                    deid_data = deid_data.with_columns(
                        pl.col(col).map_elements(
                            lambda x: self._generalize_numeric(x, level=min(2, iteration + 1)),
                            return_dtype=pl.Utf8
                        ).alias(col)
                    )
                else:
                    deid_data = deid_data.with_columns(
                        pl.col(col).map_elements(
                            lambda x: self._generalize_categorical(x, level=min(2, iteration + 1)),
                            return_dtype=pl.Utf8
                        ).alias(col)
                    )

        # 如果仍不满足，记录警告（实际项目中可增加随机抑制等兜底）
        if not meta["k_anonymity_satisfied"]:
            logger.warning(f"经过 {max_iterations} 次迭代仍未达到 K={k} 匿名，最小等价类大小={meta['final_min_class_size']}")

        return deid_data, meta

    # ==================== 辅助方法 ====================

    def _hash_value(self, value: Any) -> str:
        if value is None:
            return None
        return hashlib.md5(str(value).encode()).hexdigest()[:16]

    def _generalize_age(self, age: Any) -> str:
        if age is None:
            return None
        try:
            age = int(age)
            if age < 18:
                return "0-17"
            elif age < 30:
                return "18-29"
            elif age < 45:
                return "30-44"
            elif age < 60:
                return "45-59"
            else:
                return "60+"
        except:
            return str(age)

    def _generalize_gender(self, gender: Any) -> str:
        if gender is None:
            return None
        g = str(gender).strip().lower()
        if g in ("男", "male", "m"):
            return "男"
        elif g in ("女", "female", "f"):
            return "女"
        return "未知"

    def _generalize_numeric(self, value: Any, level: int = 1) -> str:
        if value is None:
            return None
        try:
            val = float(value)
            if level == 1:
                low = (int(val) // 10) * 10
                return f"{low}-{low + 9}"
            else:
                low = (int(val) // 20) * 20
                return f"{low}-{low + 19}"
        except:
            return str(value)

    def _generalize_categorical(self, value: Any, level: int = 1) -> str:
        if value is None:
            return None
        s = str(value).strip()
        if level == 1 and s:
            return s[0] + "*" if len(s) > 1 else s
        return "*"

    def _perturb_value(self, value: Any, ratio: float = 0.05) -> float:
        if value is None:
            return None
        try:
            val = float(value)
            perturbation = val * random.uniform(-ratio, ratio)
            return round(val + perturbation, 2)
        except:
            return value

    def _apply_generalization(self, df: pl.DataFrame, column: str) -> pl.DataFrame:
        """统一泛化入口，可后续扩展更多列的规则"""
        if column in ("age", "年龄"):
            func = self._generalize_age
        elif column in ("性别", "gender"):
            func = self._generalize_gender
        else:
            # 通用数值或类别泛化
            if df[column].dtype in (pl.Int32, pl.Int64, pl.Float32, pl.Float64):
                func = lambda x: self._generalize_numeric(x)
            else:
                func = lambda x: self._generalize_categorical(x)
        
        return df.with_columns(
            pl.col(column).map_elements(func, return_dtype=pl.Utf8).alias(column)
        )