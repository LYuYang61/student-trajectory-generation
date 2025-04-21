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
                'name': row.get('name', f"摄像头{row.get('camera_id', 0)}"),
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
    data = request.json
    records = pd.DataFrame(data.get('records'))

    # 调用时空约束分析
    filtered_records = spatiotemporal_analyzer.filter_by_spatiotemporal_constraints(records)

    # 返回时空约束过滤后的结果
    return jsonify({
        'status': 'success',
        'data': filtered_records.to_dict('records')
    })


@app.route('/reid', methods=['POST'])
def perform_reid():
    """执行ReID重识别处理"""
    data = request.json
    records = pd.DataFrame(data.get('records'))
    algorithm = data.get('algorithm', 'osnet')
    threshold = data.get('threshold', 70)

    # 进度通知函数
    def progress_callback(stage, percentage):
        socketio.emit('reid_progress', {
            'stage': stage,
            'percentage': percentage
        })

    print(f"开始执行ReID处理，算法: {algorithm}, 阈值: {threshold}")

    # 调用ReID处理
    reid_results = reid_processor.process(
        records,
        algorithm=algorithm,
        threshold=threshold / 100,
        callback=progress_callback
    )

    # 构建轨迹
    trajectory = spatiotemporal_analyzer.find_most_likely_trajectory(reid_results)

    # 格式化结果，确保所有字段都是JSON可序列化的
    reid_dict = reid_results.to_dict('records')

    # 打印重要信息
    print("====== ReID 处理结果 ======")
    print(f"处理记录数: {len(reid_results)}")
    print(f"找到轨迹点数: {len(trajectory)}")

    for record in reid_dict[:5]:  # 只打印前5条记录的详细信息
        print(f"记录ID: {record.get('id')}, 摄像头: {record.get('camera_id')}, "
              f"时间: {record.get('timestamp')}, 置信度: {record.get('confidence'):.2f}, "
              f"视频路径: {record.get('video_path')}")

    # 返回重识别和轨迹结果
    return jsonify({
        'status': 'success',
        'reid_results': reid_dict,
        'trajectory': trajectory
    })


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