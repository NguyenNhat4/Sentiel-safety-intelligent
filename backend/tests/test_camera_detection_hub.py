import asyncio

from backend.app.services.camera_detection_hub import CameraDetectionHub


def test_hub_routes_only_requested_cameras_and_keeps_latest_under_backpressure():
    async def scenario():
        hub = CameraDetectionHub(queue_size=1)
        subscription = hub.subscribe({"cam_1"})
        hub.publish({"camera_id": "cam_2", "frame_id": 1})
        hub.publish({"camera_id": "cam_1", "frame_id": 1})
        hub.publish({"camera_id": "cam_1", "frame_id": 2})
        await asyncio.sleep(0)
        payload = await asyncio.wait_for(subscription.queue.get(), timeout=0.1)
        subscription.close()
        return payload, hub.subscriber_count

    payload, subscriber_count = asyncio.run(scenario())
    assert payload == {"camera_id": "cam_1", "frame_id": 2}
    assert subscriber_count == 0
