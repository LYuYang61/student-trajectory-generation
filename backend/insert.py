import os
import configparser
import time
import json
import logging
import pymysql
import schedule
import requests
import oss2
import configparser
from datetime import datetime, timedelta
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = "./resources/configs/oss.ini"


def load_config():
    """从配置文件加载配置"""
    config = configparser.ConfigParser()

    # 检查配置文件是否存在
    if not os.path.exists(CONFIG_FILE):
        # 创建默认配置文件
        config['OSS'] = {
            'access_key_id': '',
            'access_key_secret': '',
            'endpoint': '',
            'bucket_name': '',
            'prefix': ''
        }

        config['LOCAL'] = {
            'log_folder': './resources/logs',
            'processed_files_record': './processed_files.json'
        }

        config['DATABASE'] = {
            'host': 'localhost',
            'user': 'root',
            'password': '123456',
            'database': 'trajectory',
            'charset': 'utf8mb4'
        }

        # 写入配置文件
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        logger.info(f"已创建默认配置文件: {CONFIG_FILE}")
    else:
        # 读取现有配置文件
        config.read(CONFIG_FILE)
        logger.info(f"已加载配置文件: {CONFIG_FILE}")

    return config


# 加载配置
config = load_config()

# 阿里云OSS配置
OSS_ACCESS_KEY_ID = config['OSS']['access_key_id']
OSS_ACCESS_KEY_SECRET = config['OSS']['access_key_secret']
OSS_ENDPOINT = config['OSS']['endpoint']
OSS_BUCKET_NAME = config['OSS']['bucket_name']
OSS_PREFIX = config['OSS']['prefix']

# 本地存储路径
LOCAL_LOG_FOLDER = config['LOCAL']['log_folder']
PROCESSED_FILES_RECORD = config['LOCAL']['processed_files_record']

# 数据库配置
DB_CONFIG = {
    'host': config['DATABASE']['host'],
    'user': config['DATABASE']['user'],
    'password': config['DATABASE']['password'],
    'database': config['DATABASE']['database'],
    'charset': config['DATABASE']['charset']
}


def ensure_directory_exists(directory):
    """确保目录存在，如不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"创建目录: {directory}")


def load_processed_files():
    """加载已处理文件列表"""
    ensure_directory_exists(os.path.dirname(PROCESSED_FILES_RECORD))
    if os.path.exists(PROCESSED_FILES_RECORD):
        with open(PROCESSED_FILES_RECORD, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_processed_files(processed_files):
    """保存已处理文件列表"""
    with open(PROCESSED_FILES_RECORD, 'w', encoding='utf-8') as f:
        json.dump(processed_files, f, ensure_ascii=False, indent=2)


def get_oss_client():
    """获取OSS客户端"""
    auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
    return bucket


def list_oss_files():
    """列出OSS上指定前缀的所有文件"""
    bucket = get_oss_client()
    file_list = []

    # 列出指定前缀的所有文件
    for obj in oss2.ObjectIterator(bucket, prefix=OSS_PREFIX):
        if obj.key.endswith('.json'):
            file_list.append(obj.key)

    return file_list


def download_file_from_oss(oss_key, local_path):
    """从OSS下载文件到本地"""
    try:
        bucket = get_oss_client()
        bucket.get_object_to_file(oss_key, local_path)
        logger.info(f"成功下载文件: {oss_key} 到 {local_path}")
        return True
    except Exception as e:
        logger.error(f"下载文件 {oss_key} 失败: {str(e)}")
        return False


def process_json_to_db(json_file_path):
    """处理JSON文件并插入数据库"""
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as file:
        records = json.load(file)

    # 如果没有记录，直接返回
    if not records:
        logger.info("JSON文件中没有记录")
        return

    selected_record = None

    # 1. 从头查找第一个name不为unknown的记录
    for record in records:
        if record.get('name') and record['name'].lower() != 'unknown' and record['name'].lower() != 'unkown':
            selected_record = record
            logger.info(f"找到name不为unknown的记录: {record['name']}")
            break

    # 2. 如果没找到，查找第一个bag为true的记录
    if not selected_record:
        for record in records:
            if record.get('bag', '').lower() == 'true':
                selected_record = record
                logger.info("未找到有效name，选择第一个bag为true的记录")
                break

    # 3. 如果仍未找到，选择中间记录
    if not selected_record:
        middle_index = len(records) // 2
        selected_record = records[middle_index]
        logger.info("未找到有效name或bag为true的记录，选择中间记录")

    # 连接数据库
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 获取camera_id
        camera_id = int(selected_record['cameraid'].replace('camera', ''))

        # 根据camera_id从cameras表查询location_x和location_y
        cursor.execute("SELECT location_x, location_y, name FROM cameras WHERE camera_id = %s", (camera_id,))
        camera_data = cursor.fetchone()

        if not camera_data:
            logger.warning(f"未找到camera_id为{camera_id}的记录")
            conn.close()
            return

        location_x, location_y, camera_name = camera_data

        # 处理student_id
        student_id = None
        name = selected_record.get('name', '').lower()

        # 对于name不为unknown的记录，设置student_id为202121+后四位
        if name and name != 'unknown' and name != 'unkown':
            # 检查name格式是否为"lyy-8247"这样包含数字的格式
            if '-' in name and name.split('-')[1].isdigit():
                student_id = "202121" + name.split('-')[1][-4:].zfill(4)
            else:
                # 如果格式不匹配，尝试提取任何数字
                import re
                digits = re.findall(r'\d+', name)
                if digits:
                    student_id = "202121" + digits[0][-4:].zfill(4)

        timestamp = datetime.strptime(selected_record['time'], '%Y-%m-%d %H:%M:%S')

        # 处理背包、雨伞和自行车的值
        has_backpack = 1 if selected_record.get('bag', '').lower() == 'true' else 0
        has_umbrella = 1 if selected_record.get('umbrella', '').lower() == 'true' else 0
        has_bicycle = 1 if selected_record.get('bicycle', '').lower() == 'true' else 0

        # 获取服装颜色
        clothing_color = selected_record.get('cloth_color', '')

        # 设置默认置信度为0.5
        confidence_east = confidence_south = confidence_west = confidence_north = 0.5

        # 准备student_records插入SQL
        sql_student_records = """
        INSERT INTO student_records
        (student_id, camera_id, timestamp, location_x, location_y, has_backpack,
        has_umbrella, has_bicycle, confidence_east, confidence_south,
        confidence_west, confidence_north, clothing_color)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(sql_student_records,
                       (student_id, camera_id, timestamp, location_x, location_y,
                        has_backpack, has_umbrella, has_bicycle,
                        confidence_east, confidence_south, confidence_west, confidence_north,
                        clothing_color))

        # 为camera_videos准备数据
        record_date = timestamp.date()
        # 为开始时间取整点
        start_time = timestamp.replace(minute=0, second=0)
        # 结束时间为开始时间加2小时
        end_time = (start_time + timedelta(hours=2)).time()
        start_time = start_time.time()

        # 视频路径为文件名的基础部分
        base_filename = os.path.basename(json_file_path)

        # 构建视频URL
        video_path = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{OSS_PREFIX}/{os.path.splitext(base_filename)[0]}.mp4_simplified.mp4"
        tracking_video_path = ""

        # 准备camera_videos插入SQL
        sql_camera_videos = """
        INSERT INTO camera_videos
        (camera_id, date, start_time, end_time, video_path, tracking_video_path)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor.execute(sql_camera_videos,
                       (camera_id, record_date, start_time, end_time, video_path, tracking_video_path))

        # 提交事务
        conn.commit()
        logger.info(f"成功插入数据：student_records表和camera_videos表")
        logger.info(
            f"插入student_records: student_id={student_id}, camera_id={camera_id}, location_x={location_x}, location_y={location_y}")
        logger.info(
            f"插入camera_videos: camera_id={camera_id}, date={record_date}, start_time={start_time}, end_time={end_time}")

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"插入数据时出错: {e}")
    finally:
        if conn:
            conn.close()


def sync_oss_task():
    """同步OSS中的新JSON文件并处理"""
    logger.info("开始同步OSS文件...")

    ensure_directory_exists(LOCAL_LOG_FOLDER)
    processed_files = load_processed_files()

    # 列出OSS中的文件
    oss_files = list_oss_files()
    logger.info(f"OSS上发现 {len(oss_files)} 个JSON文件")

    # 找出未处理的文件
    new_files = [f for f in oss_files if f not in processed_files]
    logger.info(f"发现 {len(new_files)} 个新JSON文件需要处理")

    for oss_key in new_files:
        # 构建本地文件路径
        local_filename = os.path.basename(oss_key)
        local_file_path = os.path.join(LOCAL_LOG_FOLDER, local_filename)

        # 下载文件
        if download_file_from_oss(oss_key, local_file_path):
            # 处理文件并插入数据库
            try:
                process_json_to_db(local_file_path)
                # 添加到已处理列表
                processed_files.append(oss_key)
                save_processed_files(processed_files)
                logger.info(f"文件 {oss_key} 处理完成")
            except Exception as e:
                logger.error(f"处理文件 {oss_key} 时出错: {str(e)}")

    logger.info("OSS文件同步完成")


def main():
    """主函数：设置定时任务并开始执行"""
    logger.info("启动OSS文件同步服务")

    # 确保目录存在
    ensure_directory_exists(LOCAL_LOG_FOLDER)

    # 首次立即执行一次
    sync_oss_task()

    # 设置定时任务，每5分钟执行一次
    schedule.every(5).minutes.do(sync_oss_task)

    # 持续运行定时任务
    logger.info("设置完成，每5分钟将检查一次OSS文件")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()