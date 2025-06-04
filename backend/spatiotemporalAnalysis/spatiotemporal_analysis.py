import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
import logging
import networkx as nx
from scipy.spatial.distance import euclidean

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SpatiotemporalAnalysis:
    """时空约束分析模块，通过时空合理性约束对记录进行进一步过滤"""

    def __init__(self, campus_map_graph: Optional[nx.Graph] = None, walking_speed: float = 1.4):
        """
        初始化时空约束分析模块

        Args:
            campus_map_graph: 校园地图的图形表示（可选），如果为None则使用欧几里得距离
            walking_speed: 平均步行速度，单位为米/秒，默认1.4m/s
        """
        self.campus_graph = campus_map_graph
        self.walking_speed = walking_speed  # 平均步行速度 (m/s)

    def calculate_travel_time(self,
                              location1: tuple,
                              location2: tuple) -> float:
        """
        计算从一个位置到另一个位置的估计行走时间

        Args:
            location1: 起始位置坐标 (longitude, latitude)
            location2: 目标位置坐标 (longitude, latitude)

        Returns:
            估计的行走时间（秒）
        """
        if self.campus_graph is not None:
            # 如果有校园地图图形，使用最短路径距离
            try:
                # 找到最近的节点
                # 将方法名从 _find_nearest_node 改为 _find_closest_node
                node1 = self._find_closest_node(location1)
                node2 = self._find_closest_node(location2)

                # 计算最短路径距离
                path = nx.shortest_path(self.campus_graph, node1, node2, weight='weight')
                distance = 0
                for i in range(len(path) - 1):
                    distance += self.campus_graph[path[i]][path[i + 1]]['weight']

                # 返回估计的行走时间
                return distance / self.walking_speed

            except (nx.NetworkXNoPath, nx.NodeNotFound, IndexError, ValueError) as e:
                # 如果无法找到路径，使用后备方案
                logging.warning(f"无法使用校园图计算距离: {str(e)}，使用后备距离计算")
                return self._calculate_fallback_distance(location1, location2) / self.walking_speed

        # 如果没有校园图，直接使用欧几里得距离
        return self._calculate_fallback_distance(location1, location2) / self.walking_speed

    def _calculate_fallback_distance(self, location1, location2):
        """计算两点间的欧几里得距离（米）作为后备方案"""
        # 将经纬度转换为近似米单位（简化计算）
        lat1, lon1 = location1[1], location1[0]
        lat2, lon2 = location2[1], location2[0]

        # 使用 Haversine 公式计算地球表面两点间的距离
        R = 6371000  # 地球半径（米）

        # 将经纬度转换为弧度
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)

        # Haversine 公式
        a = np.sin(delta_lat / 2) * np.sin(delta_lat / 2) + \
            np.cos(lat1_rad) * np.cos(lat2_rad) * \
            np.sin(delta_lon / 2) * np.sin(delta_lon / 2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        distance = R * c

        return distance

    def _find_closest_node(self, location: tuple) -> int:
        """
        找到距离给定位置最近的图节点

        Args:
            location: 位置坐标 (longitude, latitude)

        Returns:
            最近节点的ID
        """
        min_distance = float('inf')
        closest_node = None

        for node, data in self.campus_graph.nodes(data=True):
            node_location = (data['longitude'], data['latitude'])
            distance = self._calculate_fallback_distance(location, node_location)

            if distance < min_distance:
                min_distance = distance
                closest_node = node

        if closest_node is None:
            raise ValueError("无法找到最近的节点")

        return closest_node

    def filter_by_spatiotemporal_constraints(self, records):
        """基于时空约束过滤记录"""
        if records.empty:
            return records

        # 打印输入数据的列，确认name字段是否存在
        logger.info(f"输入数据列: {records.columns.tolist()}")
        logger.info(f"样例记录: {records.iloc[0].to_dict() if len(records) > 0 else '无记录'}")

        # 先保存原始的摄像头ID和名称映射关系
        camera_names = {}
        if 'camera_id' in records.columns and 'name' in records.columns:
            for _, row in records.iterrows():
                if pd.notna(row['camera_id']) and pd.notna(row['name']):
                    camera_names[row['camera_id']] = row['name']

        logger.info(f"提取的摄像头名称映射: {camera_names}")

        # 确保记录按时间排序
        sorted_records = records.sort_values('timestamp').reset_index(drop=True)

        # 记录时间戳和位置信息
        timestamps = pd.to_datetime(sorted_records['timestamp'])
        locations = sorted_records.apply(lambda row: (row['location_x'], row['location_y']), axis=1)

        # 创建结果列表
        result_indices = []
        # 初始化第一个记录
        result_indices.append(0)
        prev_timestamp = timestamps.iloc[0]
        prev_location = locations.iloc[0]
        for i in range(1, len(sorted_records)):
            curr_timestamp = timestamps.iloc[i]
            curr_location = locations.iloc[i]
            # 计算时间差（秒）
            time_diff = (curr_timestamp - prev_timestamp).total_seconds()
            # 计算最小所需时间
            min_required_time = self.calculate_travel_time(prev_location, curr_location)
            # 如果时间差大于等于最小所需时间，则该记录是有效的
            if time_diff >= min_required_time:
                result_indices.append(i)
                prev_timestamp = curr_timestamp
                prev_location = curr_location

        # 选择有效的记录 - 使用.copy()创建副本，确保不修改原始记录
        filtered_records = sorted_records.iloc[result_indices].copy()

        # 直接将名称重新应用到过滤后的记录中
        if 'camera_id' in filtered_records.columns:
            filtered_records['name'] = filtered_records['camera_id'].apply(
                lambda x: camera_names.get(x, f"摄像头{x}")
            )

        logger.info(f"过滤后记录列: {filtered_records.columns.tolist()}")
        logger.info(f"过滤后记录示例: {filtered_records.iloc[0].to_dict() if len(filtered_records) > 0 else '无记录'}")

        return filtered_records

    def find_most_likely_trajectory(self,
                                    records: pd.DataFrame,
                                    start_time: Optional[datetime] = None,
                                    end_time: Optional[datetime] = None) -> List[int]:
        """
        找出最可能的学生轨迹

        Args:
            records: 学生记录DataFrame
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）

        Returns:
            最可能轨迹的记录ID列表
        """
        if records.empty:
            return []

        # 时间过滤
        filtered_records = records.copy()
        if start_time is not None:
            filtered_records = filtered_records[filtered_records['timestamp'] >= start_time]
        if end_time is not None:
            filtered_records = filtered_records[filtered_records['timestamp'] <= end_time]

        if filtered_records.empty:
            return []

        # 创建轨迹图
        G = self.create_trajectory_graph(filtered_records)

        if len(G.nodes) == 0:
            return []

        # 找到最早和最晚的节点
        nodes_data = list(G.nodes(data=True))
        sorted_nodes = sorted(nodes_data, key=lambda x: x[1]['timestamp'])
        start_nodes = [node[0] for node in sorted_nodes[:3]]  # 考虑几个可能的起点
        end_nodes = [node[0] for node in sorted_nodes[-3:]]  # 考虑几个可能的终点

        # 找到最可能的路径
        best_path = None
        best_score = -float('inf')

        for start_node in start_nodes:
            for end_node in end_nodes:
                try:
                    # 使用最短路径（考虑概率作为权重）
                    path = nx.dijkstra_path(G, start_node, end_node, weight=lambda u, v, d: 1 - d['probability'])

                    # 计算路径得分
                    path_score = sum(G[path[i]][path[i + 1]]['probability'] for i in range(len(path) - 1))

                    if path_score > best_score:
                        best_score = path_score
                        best_path = path
                except nx.NetworkXNoPath:
                    continue

        if best_path is None:
            logger.warning("No valid trajectory found")
            return []

        # 从路径节点提取记录ID
        record_ids = [G.nodes[node]['record_id'] for node in best_path]
        return record_ids


    def analyze_anomalies(self, records: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        分析轨迹中的异常

        Args:
            records: 学生记录DataFrame

        Returns:
            异常列表，每个异常是一个字典
        """
        anomalies = []

        if records.empty or len(records) <= 1:
            return anomalies

        # 确保按时间排序
        sorted_records = records.sort_values(by='timestamp').reset_index()

        for i in range(1, len(sorted_records)):
            prev_record = sorted_records.iloc[i - 1]
            curr_record = sorted_records.iloc[i]

            # 计算时间差（秒）
            time_diff = (curr_record['timestamp'] - prev_record['timestamp']).total_seconds()

            # 获取位置坐标
            prev_loc = (prev_record['location_x'], prev_record['location_y'])
            curr_loc = (curr_record['location_x'], curr_record['location_y'])

            # 计算估计行走时间
            estimated_travel_time = self.calculate_travel_time(prev_loc, curr_loc)

            # 检查是否有异常
            # 1. 移动速度异常快
            if time_diff < estimated_travel_time * 0.5:  # 速度比预期快一倍以上
                anomalies.append({
                    'type': 'high_speed',
                    'prev_record_idx': prev_record.name,
                    'curr_record_idx': curr_record.name,
                    'time_diff': time_diff,
                    'estimated_travel_time': estimated_travel_time,
                    'speed_ratio': estimated_travel_time / time_diff if time_diff > 0 else float('inf')  # 速度比 = 预期时间 / 实际时间
                })

            elif time_diff > estimated_travel_time * 3:  # 速度比预期慢三倍以上
                anomalies.append({
                    'type': 'low_speed',
                    'prev_record_idx': prev_record.name,
                    'curr_record_idx': curr_record.name,
                    'time_diff': time_diff,
                    'estimated_travel_time': estimated_travel_time,
                    'speed_ratio': time_diff / estimated_travel_time if estimated_travel_time > 0 else float('inf')
                })

        return anomalies
