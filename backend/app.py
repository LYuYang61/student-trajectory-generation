import base64
import logging
import os
from datetime import datetime

import networkx as nx
import pandas as pd
from flask_socketio import SocketIO
import flask
from flask import Flask, request, jsonify
from sqlalchemy.testing import db

from backend.dbInterface.db_interface import DatabaseInterface
from backend.queryFilter.query_filter import QueryFilter
from backend.reidentification.reidentification import ReIDProcessor
from backend.spatiotemporalAnalysis.spatiotemporal_analysis import SpatiotemporalAnalysis
from backend.track.pipeline import run_pipeline
from flask_cors import CORS, cross_origin

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = Flask(__name__)
CORS(app, supports_credentials=True, resource={r'/*': {'origins': '*'}})
socketio = SocketIO(app, cors_allowed_origins="*")  # 允许任何来源的连接
detection_running = True


# 初始化各模块
# 确保 db_interface 初始化
db_config = {
    'type': 'mysql',
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'trajectory',
}

# 首先初始化数据库接口
db_interface = DatabaseInterface(db_config)
# 使用初始化后的数据库接口创建查询过滤器
query_filter = QueryFilter(db_interface)
reid_processor = ReIDProcessor()
campus_map = nx.Graph()  # 可以从文件或数据库加载校园地图
spatiotemporal_analyzer = SpatiotemporalAnalysis(campus_map)

# Paths for saving result images and videos
image_result_path = "./results/images/results.jpg"
video_result_path = "./results/videos/results.mp4"

@app.route('/')
def hello_world():
    return 'Hello World'

@app.route('/stopDetection', methods=['POST'])
def stop_detection():
    global detection_running
    detection_running = False
    socketio.emit('detection_stopped', {'status': 'stopped'})
    return 'Detection stopped', 200

@app.route('/trackByVideo', methods=['POST'])
def track_by_video():
    file = request.files.get('file')
    if file:
        video_path = os.path.join('uploads', file.filename)
        file.save(video_path)
        run_pipeline(video_path)
        # Returns the video for inline display
        return flask.send_file(video_result_path, mimetype='video/mp4')
    return 'No file uploaded', 400


@app.route('/filter', methods=['POST'])
def filter_records():
    try:
        data = request.get_json()
        student_id = data.get('studentId')

        # 解析时间范围
        start_time_str = data.get('startTime')
        end_time_str = data.get('endTime')
        time_range = None
        # 如果提供了时间范围，则解析
        if start_time_str and end_time_str:
            # 解析本地时间，添加东八区时区信息
            start_time = datetime.fromisoformat(start_time_str)
            # 如果没有时区信息，添加东八区时区
            if start_time.tzinfo is None:
                from datetime import timezone
                from zoneinfo import ZoneInfo
                start_time = start_time.replace(tzinfo=ZoneInfo("Asia/Shanghai"))

            end_time = datetime.fromisoformat(end_time_str)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=ZoneInfo("Asia/Shanghai"))

            time_range = (start_time, end_time)

        # 解析属性
        features = data.get('attributes', {})

        # 调用过滤器
        filter_results = query_filter.filter_process(
            student_id=student_id,
            features=features,
            time_range=time_range,
            camera_ids=None
        )

        # 转换为JSON友好格式
        results = []
        for _, row in filter_results['sorted_records'].iterrows():  # 使用已排序的记录
            record = {
                'id': int(row.get('id', 0)),
                'student_id': row.get('student_id', ''),
                'camera_id': int(row.get('camera_id', 0)),
                'timestamp': row.get('timestamp', '').strftime("%Y-%m-%d %H:%M:%S"),  # 格式化时间戳
                'name': row.get('name', ''),
                'has_backpack': bool(row.get('has_backpack', False)),
                'has_umbrella': bool(row.get('has_umbrella', False)),
                'has_bicycle': bool(row.get('has_bicycle', False))
            }
            results.append(record)

        return jsonify({'status': 'success', 'data': results})
    except Exception as e:
        logger.error(f"过滤记录时发生错误: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/spatiotemporal', methods=['POST'])
def analyze_spatiotemporal():
    """进行时空约束分析"""
    try:
        data = request.json
        if not data or 'records' not in data:
            return jsonify({'status': 'error', 'message': '缺少必要的记录数据'}), 400

        # 将前端传来的记录转换为DataFrame
        records_data = data.get('records', [])
        if not records_data:
            return jsonify({'status': 'success', 'data': []}), 200

        # 转换为DataFrame并处理时间戳
        records_df = pd.DataFrame(records_data)

        # 输出原始数据结构，用于调试
        logger.info(f"前端传入的记录结构: {records_df.columns.tolist()}")
        logger.info(f"前端传入的记录样例: {records_df.iloc[0].to_dict() if len(records_df) > 0 else '无记录'}")

        if 'timestamp' in records_df.columns:
            records_df['timestamp'] = pd.to_datetime(records_df['timestamp'])

        # 确保包含位置信息
        if not all(col in records_df.columns for col in ['location_x', 'location_y']):
            # 尝试通过camera_id获取位置信息
            if 'camera_id' in records_df.columns:
                cameras = db_interface.get_camera_locations()
                records_df = pd.merge(
                    records_df,
                    cameras[['camera_id', 'location_x', 'location_y', 'name']],
                    on='camera_id',
                    how='left',
                    suffixes=('', '_camera')  # 避免使用_x和_y后缀
                )

                # 如果原始数据没有name列，则使用摄像头的name
                if 'name' not in records_df.columns and 'name_camera' in records_df.columns:
                    records_df['name'] = records_df['name_camera']
                    records_df.drop('name_camera', axis=1, inplace=True, errors='ignore')

            else:
                return jsonify({
                    'status': 'error',
                    'message': '记录缺少位置信息或摄像头ID'
                }), 400

        # 调用时空约束分析
        filtered_records = spatiotemporal_analyzer.filter_by_spatiotemporal_constraints(records_df)

        # 如果过滤后记录没有name字段，尝试重新关联摄像头信息
        if 'camera_id' in filtered_records.columns and (
                'name' not in filtered_records.columns or filtered_records['name'].isnull().any()):
            cameras = db_interface.get_camera_locations()
            camera_dict = cameras.set_index('camera_id')['name'].to_dict()

            # 直接应用camera_id对应的name，而不是使用merge
            filtered_records['name'] = filtered_records['camera_id'].apply(
                lambda x: camera_dict.get(x, f"摄像头{x}")
            )

            # 清理多余列
            for col in filtered_records.columns:
                if col.endswith('_x') or col.endswith('_y'):
                    filtered_records.drop(col, axis=1, inplace=True, errors='ignore')

            logger.info("重新关联摄像头名称信息")

        # 将结果转换为JSON友好的格式
        result = []
        for _, row in filtered_records.iterrows():
            # 确保所有字段都存在，提供默认值
            record = {
                'id': int(row.get('id', 0)),
                'student_id': row.get('student_id', ''),
                'camera_id': int(row.get('camera_id', 0)),
                'timestamp': row.get('timestamp', '').strftime("%Y-%m-%d %H:%M:%S"),
                'name': str(row.get('name', f"摄像头{row.get('camera_id', 0)}")),  # 确保名称是字符串
                'has_backpack': bool(row.get('has_backpack', False)),
                'has_umbrella': bool(row.get('has_umbrella', False)),
                'has_bicycle': bool(row.get('has_bicycle', False)),
                'location_x': float(row.get('location_x', 0.0)),
                'location_y': float(row.get('location_y', 0.0))
            }
            result.append(record)

        # 输出处理后的结果样例，用于调试
        logger.info(f"返回的结果数量: {len(result)}")
        if result:
            logger.info(f"结果样例: {result[0]}")

        # 返回时空约束过滤后的结果
        return jsonify({
            'status': 'success',
            'data': result
        })

    except Exception as e:
        logger.error(f"时空约束分析错误: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# 特征提取端点
@app.route('/feature_extraction', methods=['POST'])
def feature_extraction():
    try:
        data = request.get_json()
        if not data or 'records' not in data:
            return jsonify({'status': 'error', 'message': '缺少记录数据'})

        records = data['records']
        algorithm = data.get('algorithm', 'mgn')

        def progress_callback(stage, percentage):
            socketio.emit('reid_progress', {'stage': stage, 'percentage': percentage})

        # 执行特征提取
        reid_processor = ReIDProcessor()
        features_records = reid_processor.extract_features(records, algorithm, progress_callback)

        return jsonify({
            'status': 'success',
            'features_records': features_records
        })

    except Exception as e:
        logging.error(f"特征提取错误: {str(e)}")
        return jsonify({'status': 'error', 'message': f'特征提取错误: {str(e)}'})


# 特征匹配端点
@app.route('/feature_matching', methods=['POST'])
def feature_matching():
    try:
        data = request.get_json()
        if not data or 'features_records' not in data:
            return jsonify({'status': 'error', 'message': '缺少特征记录数据'})

        features_records = data['features_records']
        threshold = data.get('threshold', 0.7)

        def progress_callback(stage, percentage):
            socketio.emit('reid_progress', {'stage': stage, 'percentage': percentage})

        # 执行特征匹配
        reid_processor = ReIDProcessor()
        matched_records = reid_processor.match_features(
            features_records,
            threshold=0.7,
            callback=progress_callback,
            save_dir="matching_results"
        )

        return jsonify({
            'status': 'success',
            'matched_records': matched_records
        })

    except Exception as e:
        logging.error(f"特征匹配错误: {str(e)}")
        return jsonify({'status': 'error', 'message': f'特征匹配错误: {str(e)}'})


# 保留原有端点以保持向后兼容性
@app.route('/reid', methods=['POST'])
def reid():
    try:
        data = request.get_json()
        if not data or 'records' not in data:
            return jsonify({'status': 'error', 'message': '缺少记录数据'})

        records = data['records']
        algorithm = data.get('algorithm', 'mgn')
        threshold = data.get('threshold', 0.7)

        def progress_callback(stage, percentage):
            socketio.emit('reid_progress', {'stage': stage, 'percentage': percentage})

        # 执行重识别
        reid_processor = ReIDProcessor()
        features_records = reid_processor.extract_features(records, algorithm, progress_callback)
        matched_records = reid_processor.match_features(features_records, threshold, progress_callback)

        return jsonify({
            'status': 'success',
            'matched_records': matched_records
        })

    except Exception as e:
        logging.error(f"重识别错误: {str(e)}")
        return jsonify({'status': 'error', 'message': f'重识别错误: {str(e)}'})

@app.route('/trajectory', methods=['POST'])
def get_trajectory():
    """获取完整的轨迹数据"""
    data = request.json
    record_ids = data.get('recordIds', [])

    # 根据记录ID获取详细信息
    trajectory_data = query_filter.get_records_by_ids(record_ids)

    # 获取轨迹段
    segments = spatiotemporal_analyzer.get_trajectory_segments(trajectory_data)

    # 获取异常点
    anomalies = spatiotemporal_analyzer.analyze_anomalies(trajectory_data)

    return jsonify({
        'status': 'success',
        'trajectory_data': trajectory_data.to_dict('records'),
        'segments': segments,
        'anomalies': anomalies
    })

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", debug=True, port=5000, allow_unsafe_werkzeug=True)