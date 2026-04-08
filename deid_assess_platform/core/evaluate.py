import polars as pl
import logging
import math
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class Evaluator:
    def __init__(self):
        pass

    def evaluate(
        self,
        original_df: pl.DataFrame,
        deid_df: pl.DataFrame,
        classified_fields: Union[Dict, List[Dict[str, Any]]],
        qi_columns: Optional[List[str]] = None,
        k_meta: Optional[Dict] = None,
        k_target: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        评估去标识化效果（已优化等价类展示格式）
        """
        if original_df.height == 0 or deid_df.height == 0:
            logger.warning("输入数据为空，无法评估")
            return {"summary": "数据为空，无法评估", "error": True}

        # 确定QI列并过滤实际存在的列
        if not qi_columns:
            qi_columns = self._auto_detect_qi(deid_df, classified_fields)
        valid_qi = [col for col in qi_columns if col in deid_df.columns]
        if not valid_qi:
            logger.warning("没有有效的准标识符列，使用前3列作为兜底")
            valid_qi = list(deid_df.columns[:3])

        results = {
            "original_rows": original_df.height,
            "deid_rows": deid_df.height,
            "original_columns": original_df.width,
            "deid_columns": deid_df.width,
            "qi_columns": valid_qi,
        }

        # 1. 等价类统计（核心指标 + 格式化展示）
        eq_stats = self._calculate_equivalence_classes(deid_df, valid_qi)
        results.update({
            "等价类数量": eq_stats["count"],
            "平均等价类大小": round(eq_stats["mean"], 2),
            "最小等价类大小": eq_stats["min"],
            "最大等价类大小": eq_stats["max"],
            "实际K值": eq_stats["min"],
        })
        
        if eq_stats.get("smallest_classes"):
            results["前5个最小等价类"] = eq_stats["smallest_classes"]
            results["前5个最小等价类_格式化"] = eq_stats.get("smallest_classes_formatted", "")

        # 2. K-匿名达标情况 + 违规等价类（新增格式化）
        if k_target is not None:
            results["K匿名达标"] = eq_stats["min"] >= k_target
            if eq_stats["min"] < k_target:
                violating = [cls for cls in eq_stats.get("smallest_classes", []) 
                           if int(cls.get("size", 0)) < k_target]
                results["违规等价类"] = violating[:10]
                results["违规等价类_格式化"] = self._format_classes(violating[:10], valid_qi, prefix="违规等价类")

        if k_meta:
            results["K匿名元信息"] = k_meta

        # 3. 重识别风险
        reid_risk = self._calculate_reidentification_risk(deid_df, valid_qi)
        results["重识别风险上界"] = round(reid_risk, 4)

        # 4. 归一化确定性惩罚 (NCP)
        ncp = self._compute_normalized_certainty_penalty(deid_df, valid_qi)
        results["归一化确定性惩罚(NCP)"] = round(ncp, 4)

        # 5. 信息损失比率
        info_loss = self._calculate_information_loss_ratio(original_df, deid_df, valid_qi)
        results["信息损失比率"] = round(info_loss, 4)

        # 6. 可用性损失
        availability_loss = self._calculate_availability_loss(
            original_df, deid_df, classified_fields, info_loss
        )
        results["可用性损失"] = f"{availability_loss:.2%}"

        # 7. 综合匿名强度评分
        strength_score = self._compute_strength_score(eq_stats["min"], ncp, eq_stats)
        results["综合匿名强度评分"] = round(strength_score, 2)

        # 总结
        risk_level = "高" if reid_risk > 0.3 else "中" if reid_risk > 0.1 else "低"
        results["summary"] = (
            f"实际K值: {eq_stats['min']} | "
            f"重识别风险: {risk_level} ({reid_risk:.4f}) | "
            f"NCP: {ncp:.4f} | "
            f"强度评分: {results['综合匿名强度评分']:.1f}/100"
        )

        if k_target and not results.get("K匿名达标", True):
            results["warning"] = f"未达到目标K={k_target}，最小等价类大小仅为 {eq_stats['min']}。建议调整泛化策略或增大K值。"

        return results

    # ==================== 核心计算方法 ====================

    def _auto_detect_qi(self, df: pl.DataFrame, classified_fields: Union[Dict, List]) -> List[str]:
        qi = []
        for col in df.columns:
            is_quasi = False
            if isinstance(classified_fields, dict):
                if classified_fields.get(col) == "quasi":
                    is_quasi = True
            else:
                for f in classified_fields:
                    if f.get("name") == col and f.get("detected_class") == "quasi":
                        is_quasi = True
                        break
            if is_quasi:
                qi.append(col)
        return qi or list(df.columns[:3])

    def _calculate_equivalence_classes(self, data: pl.DataFrame, qi_columns: List[str]) -> Dict:
        """安全的等价类统计 + 前5最小等价类（新增格式化字符串）"""
        if data.height == 0 or not qi_columns:
            return {
                "count": 0, "mean": 0.0, "min": 0, "max": 0,
                "smallest_classes": [], "smallest_classes_formatted": ""
            }

        try:
            grouped = (
                data.group_by(qi_columns)
                .agg(pl.count().alias("class_size"))
            )
            if grouped.height == 0:
                return {
                    "count": 0, "mean": 0.0, "min": 0, "max": 0,
                    "smallest_classes": [], "smallest_classes_formatted": ""
                }

            sizes = grouped.select("class_size")
            
            # 获取前5个最小等价类（原始结构）
            smallest_classes = []
            if grouped.height > 0:
                sorted_groups = grouped.sort("class_size")
                for i in range(min(5, sorted_groups.height)):
                    row = sorted_groups.row(i, named=True)
                    class_info = {
                        "size": int(row["class_size"]),
                        "values": {col: str(row.get(col, "")) for col in qi_columns}
                    }
                    smallest_classes.append(class_info)

            # 新增：格式化字符串，便于UI直接显示
            formatted = self._format_classes(smallest_classes, qi_columns, prefix="最小等价类")

            return {
                "count": grouped.height,
                "mean": float(sizes.mean().item()),
                "min": int(sizes.min().item()),
                "max": int(sizes.max().item()),
                "smallest_classes": smallest_classes,
                "smallest_classes_formatted": formatted
            }
        except Exception as e:
            logger.error(f"等价类计算失败 (qi_columns={qi_columns}): {e}")
            return {
                "count": 0, "mean": 0.0, "min": 0, "max": 0,
                "smallest_classes": [], "smallest_classes_formatted": "计算失败"
            }

    def _format_classes(self, classes: List[Dict], qi_columns: List[str], prefix: str = "等价类") -> str:
        """将等价类列表格式化为易读的多行字符串"""
        if not classes:
            return f"无{prefix}"

        lines = []
        for idx, cls in enumerate(classes, 1):
            size = cls.get("size", 0)
            values = cls.get("values", {})
            value_str = " | ".join([f"{col}: {values.get(col, '')}" for col in qi_columns])
            lines.append(f"{idx:2d}. 大小: {size}")
            lines.append(f"     {value_str}")
            lines.append("")  # 空行分隔

        return "\n".join(lines).strip()

    def _calculate_reidentification_risk(self, deid_df: pl.DataFrame, qi_columns: List[str]) -> float:
        if deid_df.height == 0 or not qi_columns:
            return 0.0
        try:
            grouped = deid_df.group_by(qi_columns).agg(pl.count().alias("class_size"))
            eq_sizes = grouped["class_size"]
            if len(eq_sizes) == 0:
                return 0.0
            return (1.0 / eq_sizes).mean()
        except Exception as e:
            logger.error(f"重识别风险计算失败: {e}")
            return 0.0

    def _compute_normalized_certainty_penalty(self, df: pl.DataFrame, qi_columns: List[str]) -> float:
        if not qi_columns:
            return 0.0
        ncp_total = 0.0
        for col in qi_columns:
            if col not in df.columns:
                continue
            try:
                series = df[col].cast(pl.Utf8)
                is_range = series.str.contains(r"^\d+-\d+$")
                if is_range.sum() > 0:
                    splits = series.filter(is_range).str.split_exact("-", 1)
                    low = splits.struct.field("field_0").cast(pl.Int64)
                    high = splits.struct.field("field_1").cast(pl.Int64)
                    widths = high - low
                    if widths.len() > 0:   # 统一使用 .len()
                        avg_width = widths.mean().item()
                        global_range = 100
                        ncp_total += avg_width / max(global_range, 1)
                else:
                    global_card = df[col].n_unique()
                    if global_card <= 1:
                        continue
                    group_card = (
                        df.group_by(qi_columns)
                        .agg(pl.col(col).n_unique().alias("g_card"))["g_card"]
                    )
                    ncp_total += (group_card / global_card).mean()
            except Exception as col_e:
                logger.debug(f"NCP 计算列 {col} 时跳过: {col_e}")
                continue
        return ncp_total / len(qi_columns) if qi_columns else 0.0

    def _calculate_information_loss_ratio(self, orig_df: pl.DataFrame, deid_df: pl.DataFrame, qi_columns: List[str]) -> float:
        if not qi_columns:
            return 0.0
        try:
            total_orig = sum(orig_df[col].n_unique() for col in qi_columns if col in orig_df.columns)
            total_deid = sum(deid_df[col].n_unique() for col in qi_columns if col in deid_df.columns)
            if total_orig == 0:
                return 0.0
            return (total_orig - total_deid) / total_orig
        except Exception as e:
            logger.error(f"信息损失比率计算失败: {e}")
            return 0.0

    def _calculate_availability_loss(
        self,
        original_df: pl.DataFrame,
        deid_df: pl.DataFrame,
        classified_fields: Union[Dict, List],
        info_loss: float
    ) -> float:
        orig_cols = original_df.width
        deid_cols = deid_df.width
        column_loss = (orig_cols - deid_cols) / max(orig_cols, 1)

        processed = 0
        total_fields = 0
        if isinstance(classified_fields, dict):
            for column, cls in classified_fields.items():
                if column in deid_df.columns and cls in ["direct", "quasi", "sensitive"]:
                    processed += 1
                total_fields += 1
        else:
            for f in classified_fields:
                if f.get("name") in deid_df.columns and f.get("detected_class") in ["direct", "quasi", "sensitive"]:
                    processed += 1
                total_fields += 1

        field_loss = processed / max(total_fields, 1)
        return min(0.6 * column_loss + 0.3 * info_loss + 0.1 * field_loss, 1.0)

    def _compute_strength_score(self, actual_k: int, ncp: float, eq_stats: Dict) -> float:
        k_score = min(math.log1p(actual_k) / math.log1p(100), 1.0) * 40 if actual_k > 0 else 0
        ncp_score = (1.0 - min(ncp, 1.0)) * 30
        cv = eq_stats.get("std", 0) / max(eq_stats.get("mean", 1), 1) if eq_stats.get("mean", 0) > 0 else 0
        balance_score = max(0.0, 1.0 - cv / 5.0) * 30
        return k_score + ncp_score + balance_score