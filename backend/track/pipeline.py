import yaml
from backend.track.person_tracker import PersonTracker

def run_pipeline(video_path, params_path='D:/lyycode02/student-trajectory-generation/backend/resources/configs/params.yaml'):
    with open(params_path, "r") as file:
        params = yaml.safe_load(file)

    tracker = PersonTracker(
        model_path=params['model_path'],
        tracker_config=params['tracker_config'],
        conf=params['conf'],
        device=params['device'],
        iou=params['iou'],
        img_size=params['img_size']
    )

    tracker.track_people(source=video_path, show=params['show'])