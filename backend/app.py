import base64
import logging
import os
import traceback
from datetime import datetime, timedelta

import networkx as nx
import numpy as np
import pandas as pd
from flask_socketio import SocketIO
import flask
from flask import Flask, request, jsonify, abort, send_file
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

# 视频文件存储路径
VIDEO_STORAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), './resources/videos')
if not os.path.exists(VIDEO_STORAGE_PATH):
    os.makedirs(VIDEO_STORAGE_PATH)

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
        result = reid_processor.extract_features(
            records,
            algorithm,
            progress_callback,
            save_dir = os.path.join("detecting_results", datetime.now().strftime("%Y%m%d_%H%M%S"))
        )

        # 处理返回结果
        if isinstance(result, dict):
            # 新版本的返回格式，包含记录和帧特征
            features_records = result.get('records', [])
            all_frames_features = result.get('all_frames_features', {})
            query_feature = result.get('query_feature')
        else:
            # 旧版本的返回格式，只有记录列表
            features_records = result
            all_frames_features = {}
            query_feature = None
            # 查找查询特征向量
            for record in features_records:
                if record.get('id') == 'query' and 'feature_vector' in record:
                    query_feature = record['feature_vector']
                    break

        # 处理记录，确保JSON安全
        json_safe_records = []
        for record in features_records:
            json_safe_record = {}
            for key, value in record.items():
                # 跳过图像数据，这些不应该通过JSON返回
                if key in ['image', 'processed_image', 'extracted_frames']:
                    continue
                # 确保feature_vector是列表而非NumPy数组
                elif key == 'feature_vector' and isinstance(value, np.ndarray):
                    json_safe_record[key] = value.tolist()
                # 处理其他NumPy类型
                elif isinstance(value, np.integer):
                    json_safe_record[key] = int(value)
                elif isinstance(value, np.floating):
                    json_safe_record[key] = float(value)
                elif isinstance(value, np.ndarray):
                    json_safe_record[key] = value.tolist()
                else:
                    json_safe_record[key] = value
            json_safe_records.append(json_safe_record)

        # 处理帧特征，确保JSON安全
        json_safe_frames = {}
        for camera_id, frames in all_frames_features.items():
            json_safe_frames[camera_id] = []
            for frame in frames:
                json_safe_frame = {}
                for key, value in frame.items():
                    if key == 'feature_vector' and isinstance(value, np.ndarray):
                        json_safe_frame[key] = value.tolist()
                    elif isinstance(value, np.integer):
                        json_safe_frame[key] = int(value)
                    elif isinstance(value, np.floating):
                        json_safe_frame[key] = float(value)
                    elif isinstance(value, np.ndarray):
                        json_safe_frame[key] = value.tolist()
                    else:
                        json_safe_frame[key] = value
                json_safe_frames[camera_id].append(json_safe_frame)

        # 处理查询特征向量
        json_safe_query = None
        if query_feature is not None:
            if isinstance(query_feature, np.ndarray):
                json_safe_query = query_feature.tolist()
            else:
                json_safe_query = query_feature

        return jsonify({
            'status': 'success',
            'features_records': json_safe_records,
            'all_frames_features': json_safe_frames,
            'query_feature': json_safe_query
        })

    except Exception as e:
        logging.error(f"特征提取错误: {str(e)}")
        return jsonify({'status': 'error', 'message': f'特征提取错误: {str(e)}'})


@app.route('/feature_matching', methods=['POST'])
def feature_matching():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': '缺少请求数据'})

        # 检查数据结构
        if 'features_records' in data:
            # 旧的数据结构，只有记录列表
            features_data = {'records': data['features_records']}
        elif 'records' in data:
            # 新的数据结构已经包含了记录和帧特征
            features_data = data
        else:
            return jsonify({'status': 'error', 'message': '缺少特征记录数据'})

        threshold = data.get('threshold', 0.7)

        def progress_callback(stage, percentage):
            socketio.emit('reid_progress', {'stage': stage, 'percentage': percentage})

        # 执行特征匹配
        reid_processor = ReIDProcessor()
        matched_records = reid_processor.match_features(
            features_data,
            threshold=threshold,
            callback=progress_callback,
            save_dir=os.path.join("matching_results", datetime.now().strftime("%Y%m%d_%H%M%S"))
        )

        # 处理NumPy数组和其他不可JSON序列化的对象
        json_safe_matches = []
        for match in matched_records:
            json_safe_match = {}
            for key, value in match.items():
                # 跳过不应该通过JSON返回的大型数据
                if key in ['image', 'processed_image']:
                    continue
                # 处理嵌套的matched_frames列表
                elif key == 'matched_frames' and isinstance(value, list):
                    json_safe_frames = []
                    for frame in value:
                        json_safe_frame = {}
                        for frame_key, frame_value in frame.items():
                            if isinstance(frame_value, np.integer):
                                json_safe_frame[frame_key] = int(frame_value)
                            elif isinstance(frame_value, np.floating):
                                json_safe_frame[frame_key] = float(frame_value)
                            elif isinstance(frame_value, np.ndarray):
                                json_safe_frame[frame_key] = frame_value.tolist()
                            else:
                                json_safe_frame[frame_key] = frame_value
                        json_safe_frames.append(json_safe_frame)
                    json_safe_match[key] = json_safe_frames
                # 处理NumPy类型
                elif isinstance(value, np.integer):
                    json_safe_match[key] = int(value)
                elif isinstance(value, np.floating):
                    json_safe_match[key] = float(value)
                elif isinstance(value, np.ndarray):
                    json_safe_match[key] = value.tolist()
                else:
                    json_safe_match[key] = value
            json_safe_matches.append(json_safe_match)

        return jsonify({
            'status': 'success',
            'matched_records': json_safe_matches
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


@app.route('/cameras', methods=['GET'])
def get_all_cameras():
    """获取所有摄像头信息"""
    try:
        query = "SELECT camera_id, location_x, location_y, name FROM cameras"
        cameras = db_interface.execute_query(query)
        return jsonify({
            'status': 'success',
            'data': cameras
        })
    except Exception as e:
        logger.error(f"获取摄像头信息失败: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/cameras/<int:camera_id>', methods=['GET'])
def get_camera(camera_id):
    """获取单个摄像头信息"""
    try:
        query = "SELECT camera_id, location_x, location_y, name FROM cameras WHERE camera_id = %s"
        if db_config['type'].lower() == 'sqlite':
            query = query.replace("%s", "?")
        cameras = db_interface.execute_query(query, (camera_id,))
        if cameras:
            return jsonify({
                'status': 'success',
                'data': cameras[0]
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'找不到ID为 {camera_id} 的摄像头'
            }), 404
    except Exception as e:
        logger.error(f"获取摄像头信息失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/cameras', methods=['POST'])
def add_camera():
    """添加新摄像头"""
    try:
        data = request.json
        name = data.get('name')
        location_x = data.get('location_x')
        location_y = data.get('location_y')

        # 参数验证
        if not name or location_x is None or location_y is None:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            }), 400

        # 获取最大的camera_id
        max_id_query = "SELECT MAX(camera_id) as max_id FROM cameras"
        result = db_interface.execute_query(max_id_query)
        new_id = 1  # 默认值
        if result and result[0]['max_id'] is not None:
            new_id = int(result[0]['max_id']) + 1

        # 插入新摄像头
        insert_query = """
        INSERT INTO cameras (camera_id, name, location_x, location_y) 
        VALUES (%s, %s, %s, %s)
        """
        if db_config['type'].lower() == 'sqlite':
            insert_query = insert_query.replace("%s", "?")

        db_interface.execute_query(insert_query, (new_id, name, location_x, location_y))
        db_interface.conn.commit()

        return jsonify({
            'status': 'success',
            'message': '添加摄像头成功',
            'data': {
                'camera_id': new_id,
                'name': name,
                'location_x': location_x,
                'location_y': location_y
            }
        })
    except Exception as e:
        logger.error(f"添加摄像头失败: {e}")
        db_interface.conn.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/cameras/<int:camera_id>', methods=['PUT'])
def update_camera(camera_id):
    """更新摄像头信息"""
    try:
        data = request.json
        name = data.get('name')
        location_x = data.get('location_x')
        location_y = data.get('location_y')

        # 参数验证
        if not name or location_x is None or location_y is None:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            }), 400

        # 检查摄像头是否存在
        check_query = "SELECT camera_id FROM cameras WHERE camera_id = %s"
        if db_config['type'].lower() == 'sqlite':
            check_query = check_query.replace("%s", "?")
        result = db_interface.execute_query(check_query, (camera_id,))
        if not result:
            return jsonify({
                'status': 'error',
                'message': f'找不到ID为 {camera_id} 的摄像头'
            }), 404

        # 更新摄像头信息
        update_query = """
        UPDATE cameras 
        SET name = %s, location_x = %s, location_y = %s 
        WHERE camera_id = %s
        """
        if db_config['type'].lower() == 'sqlite':
            update_query = update_query.replace("%s", "?")

        db_interface.execute_query(update_query, (name, location_x, location_y, camera_id))
        db_interface.conn.commit()

        return jsonify({
            'status': 'success',
            'message': '更新摄像头成功',
            'data': {
                'camera_id': camera_id,
                'name': name,
                'location_x': location_x,
                'location_y': location_y
            }
        })
    except Exception as e:
        logger.error(f"更新摄像头失败: {e}")
        db_interface.conn.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/cameras/<int:camera_id>', methods=['DELETE'])
def delete_camera(camera_id):
    """删除摄像头"""
    try:
        # 检查摄像头是否存在
        check_query = "SELECT camera_id FROM cameras WHERE camera_id = %s"
        if db_config['type'].lower() == 'sqlite':
            check_query = check_query.replace("%s", "?")
        result = db_interface.execute_query(check_query, (camera_id,))
        if not result:
            return jsonify({
                'status': 'error',
                'message': f'找不到ID为 {camera_id} 的摄像头'
            }), 404

        # 删除摄像头
        delete_query = "DELETE FROM cameras WHERE camera_id = %s"
        if db_config['type'].lower() == 'sqlite':
            delete_query = delete_query.replace("%s", "?")

        db_interface.execute_query(delete_query, (camera_id,))
        db_interface.conn.commit()

        return jsonify({
            'status': 'success',
            'message': '删除摄像头成功'
        })
    except Exception as e:
        logger.error(f"删除摄像头失败: {e}")
        db_interface.conn.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/cameras/<int:camera_id>/videos', methods=['GET'])
def get_camera_videos(camera_id):
    """获取指定摄像头特定日期的视频列表"""
    try:
        date = request.args.get('date')
        if not date:
            return jsonify({
                'status': 'error',
                'message': '缺少日期参数'
            }), 400

        # 查询视频
        query = """
        SELECT id, camera_id, date, start_time, end_time, video_path
        FROM camera_videos
        WHERE camera_id = %s AND date = %s
        ORDER BY start_time
        """
        if db_config['type'].lower() == 'sqlite':
            query = query.replace("%s", "?")

        videos = db_interface.execute_query(query, (camera_id, date))

        # 处理时间格式，确保可JSON序列化
        for video in videos:
            # 处理start_time
            if isinstance(video['start_time'], timedelta):
                hours, remainder = divmod(video['start_time'].seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                video['start_time'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            # 处理end_time
            if isinstance(video['end_time'], timedelta):
                hours, remainder = divmod(video['end_time'].seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                video['end_time'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            # 确保视频路径是完整的OSS URL
            if video['video_path'] and not video['video_path'].startswith('http'):
                # 如果数据库中存的是相对路径，则拼接为完整URL
                video['video_path'] = f"https://qingwu-oss.oss-cn-heyuan.aliyuncs.com/lian/{video['video_path']}"

        return jsonify({
            'status': 'success',
            'data': videos
        })
    except Exception as e:
        logger.error(f"获取视频列表失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/videos', methods=['POST'])
def add_video():
    """添加视频记录"""
    try:
        data = request.json
        camera_id = data.get('camera_id')
        date = data.get('date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        video_path = data.get('video_path')

        # 参数验证
        if not camera_id or not date or not start_time or not end_time or not video_path:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            }), 400

        # 检查摄像头是否存在
        check_query = "SELECT camera_id FROM cameras WHERE camera_id = %s"
        if db_config['type'].lower() == 'sqlite':
            check_query = check_query.replace("%s", "?")
        result = db_interface.execute_query(check_query, (camera_id,))
        if not result:
            return jsonify({
                'status': 'error',
                'message': f'找不到ID为 {camera_id} 的摄像头'
            }), 404

        # 插入视频记录
        insert_query = """
        INSERT INTO camera_videos (camera_id, date, start_time, end_time, video_path) 
        VALUES (%s, %s, %s, %s, %s)
        """
        if db_config['type'].lower() == 'sqlite':
            insert_query = insert_query.replace("%s", "?")

        db_interface.execute_query(insert_query, (camera_id, date, start_time, end_time, video_path))
        db_interface.conn.commit()

        return jsonify({
            'status': 'success',
            'message': '添加视频记录成功'
        })
    except Exception as e:
        logger.error(f"添加视频记录失败: {e}")
        db_interface.conn.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/videos/<int:video_id>', methods=['DELETE'])
def delete_video(video_id):
    """删除视频记录"""
    try:
        # 检查视频记录是否存在
        check_query = "SELECT id, video_path FROM camera_videos WHERE id = %s"
        if db_config['type'].lower() == 'sqlite':
            check_query = check_query.replace("%s", "?")
        result = db_interface.execute_query(check_query, (video_id,))
        if not result:
            return jsonify({
                'status': 'error',
                'message': f'找不到ID为 {video_id} 的视频记录'
            }), 404

        # 删除视频文件
        video_path = result[0]['video_path']
        full_path = os.path.join(VIDEO_STORAGE_PATH, video_path)
        if os.path.exists(full_path):
            os.remove(full_path)

        # 删除数据库记录
        delete_query = "DELETE FROM camera_videos WHERE id = %s"
        if db_config['type'].lower() == 'sqlite':
            delete_query = delete_query.replace("%s", "?")

        db_interface.execute_query(delete_query, (video_id,))
        db_interface.conn.commit()

        return jsonify({
            'status': 'success',
            'message': '删除视频记录成功'
        })
    except Exception as e:
        logger.error(f"删除视频记录失败: {e}")
        db_interface.conn.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/video/<path:video_path>')
def serve_video(video_path):
    """提供视频文件"""
    try:
        full_path = os.path.join(VIDEO_STORAGE_PATH, video_path)
        if not os.path.exists(full_path):
            abort(404)
        return send_file(full_path, mimetype='video/mp4')
    except Exception as e:
        logger.error(f"提供视频文件失败: {e}")
        abort(500)


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", debug=True, port=5000, allow_unsafe_werkzeug=True)