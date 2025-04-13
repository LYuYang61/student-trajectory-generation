import os
from flask_socketio import SocketIO
import flask
from flask import Flask, request
from backend.track.pipeline import run_pipeline
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app, supports_credentials=True, resource={r'/*': {'origins': '*'}})
socketio = SocketIO(app)
detection_running = True

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

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", debug=True, port=5000, allow_unsafe_werkzeug=True)