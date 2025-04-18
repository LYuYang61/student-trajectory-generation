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
                              location1: Tuple[float, float],
                              location2: Tuple[float, float]) -> float:
        """
        计算从一个位置到另一个位置的估计行走时间

        Args:
            location1: 起始位置坐标 (x, y)
            location2: 目标位置坐标 (x, y)

        Returns:
            估计的行走时间（秒）
        """
        if self.campus_graph is not None:
            # 如果有校园地图图形，使用最短路径距离
            try:
                closest_node1 = self._find_closest_node(location1)
                closest_node2 = self._find_closest_node(location2)
                path_length = nx.shortest_path_length(
                    self.campus_graph,
                    source=closest_node1,
                    target=closest_node2,
                    weight='distance'
                )
                return path_length / self.walking_speed
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                # 如果找不到路径，回退到欧几里得距离
                logger.warning(f"No path found between {location1} and {location2}, using Euclidean distance")

        # 使用欧几里得距离
        distance = euclidean(location1, location2)
        return distance / self.walking_speed

    def _find_closest_node(self, location: Tuple[float, float]) -> str:
        """
        在图中找到最接近给定位置的节点

        Args:
            location: 位置坐标 (x, y)

        Returns:
            最接近的节点ID
        """
        min_dist = float('inf')
        closest_node = None

        for node in self.campus_graph.nodes:
            node_pos = self.campus_graph.nodes[node]['pos']
            dist = euclidean(location, node_pos)
            if dist < min_dist:
                min_dist = dist
                closest_node = node

        return closest_node

    def filter_by_spatiotemporal_constraints(self,
                                             records: pd.DataFrame,
                                             time_threshold_multiplier: float = 1.5) -> pd.DataFrame:
        """
        使用时空约束过滤记录

        Args:
            records: 包含时间戳和位置的记录DataFrame
            time_threshold_multiplier: 时间阈值乘数，考虑到可能的延迟

        Returns:
            时空合理的记录DataFrame
        """
        if records.empty or len(records) <= 1:
            return records

        if not all(col in records.columns for col in ['timestamp', 'location_x', 'location_y']):
            logger.warning("Records missing required columns for spatiotemporal analysis")
            return records

        # 确保按时间排序
        sorted_records = records.sort_values(by='timestamp').reset_index(drop=True)
        valid_indices = [0]  # 第一条记录总是有效的

        for i in range(1, len(sorted_records)):
            prev_idx = valid_indices[-1]
            prev_record = sorted_records.iloc[prev_idx]
            curr_record = sorted_records.iloc[i]

            # 计算时间差（秒）
            time_diff = (curr_record['timestamp'] - prev_record['timestamp']).total_seconds()

            # 获取位置坐标
            prev_loc = (prev_record['location_x'], prev_record['location_y'])
            curr_loc = (curr_record['location_x'], curr_record['location_y'])

            # 计算估计行走时间
            estimated_travel_time = self.calculate_travel_time(prev_loc, curr_loc)

            # 检查时间差是否合理（考虑阈值乘数）
            if time_diff >= estimated_travel_time / time_threshold_multiplier:
                valid_indices.append(i)
            else:
                logger.info(f"Record at index {i} filtered out due to spatiotemporal constraint violation")

        # 返回时空合理的记录
        return sorted_records.iloc[valid_indices]

    def create_trajectory_graph(self, records: pd.DataFrame) -> nx.DiGraph:
        """
        创建轨迹图，表示可能的学生移动

        Args:
            records: 学生记录DataFrame

        Returns:
            有向图，表示可能的移动路径
        """
        G = nx.DiGraph()

        if records.empty or len(records) <= 1:
            return G

        if not all(col in records.columns for col in ['timestamp', 'location_x', 'location_y', 'camera_id']):
            logger.warning("Records missing required columns for trajectory graph creation")
            return G

        # 按摄像头和时间分组记录
        for camera_id, group in records.groupby('camera_id'):
            camera_records = group.sort_values(by='timestamp')

            # 为每个摄像头添加节点
            for idx, row in camera_records.iterrows():
                node_id = f"cam_{camera_id}_{idx}"
                G.add_node(node_id,
                           camera_id=camera_id,
                           timestamp=row['timestamp'],
                           location=(row['location_x'], row['location_y']),
                           record_id=idx)

        # 添加可能的边
        nodes = list(G.nodes(data=True))
        for i, (node1, node1_data) in enumerate(nodes):
            for node2, node2_data in nodes[i + 1:]:
                # 不同摄像头之间才需要考虑约束
                if node1_data['camera_id'] != node2_data['camera_id']:
                    time_diff = (node2_data['timestamp'] - node1_data['timestamp']).total_seconds()

                    # 计算估计行走时间
                    estimated_travel_time = self.calculate_travel_time(
                        node1_data['location'],
                        node2_data['location']
                    )

                    # 如果时间合理，添加有向边
                    if time_diff > 0 and time_diff >= estimated_travel_time / 2:  # 允许一定程度的加速
                        G.add_edge(node1, node2,
                                   time_diff=time_diff,
                                   estimated_travel_time=estimated_travel_time,
                                   probability=min(1.0, estimated_travel_time / time_diff))

        return G

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

    def build_campus_graph_from_data(self,
                                     camera_locations: pd.DataFrame,
                                     path_data: List[Dict[str, Any]] = None) -> nx.Graph:
        """
        从摄像头位置和路径数据构建校园地图图形

        Args:
            camera_locations: 摄像头位置DataFrame
            path_data: 路径数据列表，每个元素是一个字典 {'from': camera_id1, 'to': camera_id2, 'distance': 实际距离}

        Returns:
            校园地图图形
        """
        G = nx.Graph()

        # 添加摄像头节点
        for _, cam in camera_locations.iterrows():
            G.add_node(f"cam_{cam['camera_id']}",
                       pos=(cam['location_x'], cam['location_y']),
                       name=cam.get('name', f"Camera {cam['camera_id']}"))

        # 如果提供了路径数据，添加边
        if path_data:
            for path in path_data:
                from_id = f"cam_{path['from']}"
                to_id = f"cam_{path['to']}"

                if from_id in G and to_id in G:
                    # 使用提供的实际距离
                    G.add_edge(from_id, to_id, distance=path['distance'])
        else:
            # 否则，连接所有摄像头，使用欧几里得距离
            nodes = list(G.nodes(data=True))
            for i, (node1, node1_data) in enumerate(nodes):
                for node2, node2_data in nodes[i + 1:]:
                    dist = euclidean(node1_data['pos'], node2_data['pos'])
                    G.add_edge(node1, node2, distance=dist)

        self.campus_graph = G
        return G

    def get_trajectory_segments(self, records: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        获取轨迹段

        Args:
            records: 学生记录DataFrame

        Returns:
            轨迹段列表，每个元素是一个字典
        """
        if records.empty or len(records) <= 1:
            return []

        # 确保按时间排序
        sorted_records = records.sort_values(by='timestamp').reset_index(drop=True)

        segments = []
        for i in range(len(sorted_records) - 1):
            start_record = sorted_records.iloc[i]
            end_record = sorted_records.iloc[i + 1]

            # 如果摄像头不同，表示一个轨迹段
            if start_record['camera_id'] != end_record['camera_id']:
                segments.append({
                    'start_record_id': start_record.name,
                    'end_record_id': end_record.name,
                    'start_camera': start_record['camera_id'],
                    'end_camera': end_record['camera_id'],
                    'start_time': start_record['timestamp'],
                    'end_time': end_record['timestamp'],
                    'time_diff': (end_record['timestamp'] - start_record['timestamp']).total_seconds(),
                    'start_location': (start_record['location_x'], start_record['location_y']),
                    'end_location': (end_record['location_x'], end_record['location_y'])
                })

        return segments