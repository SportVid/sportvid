"""Every API endpoint that takes an object ID, with a valid request against alice's world.

kind: "read" endpoints may be used by researchers on other users' videos, "write"
endpoints only by the owner and admins (backend/permissions.py).
"""
import json
from dataclasses import dataclass
from typing import Callable

GET, POST_JSON, POST_FORM = "get", "post_json", "post_form"


@dataclass(frozen=True)
class Endpoint:
    path: str
    method: str
    payload: Callable
    kind: str

    @property
    def id(self):
        return self.path

    def call(self, client, world):
        data = self.payload(world)
        if self.method == GET:
            response = client.get(f"/{self.path}", data)
        elif self.method == POST_JSON:
            response = client.post(f"/{self.path}", json.dumps(data), content_type="application/json")
        else:
            response = client.post(f"/{self.path}", data)
        return response, data


def h(obj):
    return obj.id.hex


ENDPOINTS = [
    # ---------- reads
    Endpoint("timeline/list", GET, lambda w: {"video_id": h(w.video)}, "read"),
    Endpoint("timeline/segment/annotation/list", GET, lambda w: {"video_id": h(w.video)}, "read"),
    Endpoint("cluster/timeline/item/fetch", GET, lambda w: {"video_id": h(w.video)}, "read"),
    Endpoint("cluster/item/fetch", GET, lambda w: {"video_id": h(w.video)}, "read"),
    Endpoint("video/analysis/get", GET, lambda w: {"video_id": h(w.video)}, "read"),
    Endpoint("plugin/list", GET, lambda w: {"video_id": h(w.video)}, "read"),
    Endpoint("plugin/run/result/list", GET, lambda w: {"video_id": h(w.video), "plugin_run_id": h(w.plugin_run)}, "read"),
    Endpoint("plugin/run/result/kpi/chunk", GET, lambda w: {"video_id": h(w.video), "tracking_data_id": h(w.tracking_data)}, "read"),
    Endpoint("tracking_data/pos_data/chunk", GET, lambda w: {"video_id": h(w.video), "tracking_data_id": h(w.tracking_data)}, "read"),
    Endpoint("annotation/shortcut/list", GET, lambda w: {"video_id": h(w.video)}, "read"),
    Endpoint("video/export", POST_FORM, lambda w: {"video_id": h(w.video), "format": "merged_csv"}, "read"),
    # ---------- timelines
    Endpoint("timeline/duplicate", POST_JSON, lambda w: {"id": h(w.timeline), "name": "copy"}, "write"),
    Endpoint("timeline/create", POST_JSON, lambda w: {"video_id": h(w.video), "name": "new"}, "write"),
    Endpoint("timeline/rename", POST_JSON, lambda w: {"id": h(w.timeline), "name": "renamed"}, "write"),
    Endpoint("timeline/changevisualization", POST_JSON, lambda w: {"id": h(w.timeline), "visualization": "SCALAR_LINE"}, "write"),
    Endpoint("timeline/setparent", POST_JSON, lambda w: {"timelineId": h(w.timeline), "parentId": None}, "write"),
    Endpoint("timeline/setcollapse", POST_JSON, lambda w: {"timelineId": h(w.timeline), "collapse": True}, "write"),
    Endpoint("timeline/setorder", POST_JSON, lambda w: {"order": [h(w.timeline)]}, "write"),
    Endpoint("timeline/delete", POST_JSON, lambda w: {"id": h(w.timeline)}, "write"),
    Endpoint("timeline/import/eaf", POST_FORM, lambda w: {"video_id": h(w.video)}, "write"),
    # ---------- segments
    Endpoint("timeline/segment/annotate", POST_JSON, lambda w: {"timeline_segment_ids": [h(w.segment)], "annotations": [{"name": "x", "color": "#fff"}]}, "write"),
    Endpoint("timeline/segment/annotate/range", POST_JSON, lambda w: {"timeline_id": h(w.timeline), "start": 1.0, "end": 2.0, "annotations": []}, "write"),
    Endpoint("timeline/segment/merge", POST_JSON, lambda w: {"timeline_segment_ids": [h(w.segment), h(w.segment2)]}, "write"),
    Endpoint("timeline/segment/split", POST_JSON, lambda w: {"timeline_segment_id": h(w.segment), "time": 2.0}, "write"),
    Endpoint("timeline/segment/annotation/create", POST_JSON, lambda w: {"timeline_segment_id": h(w.segment), "annotation_id": h(w.annotation2)}, "write"),
    Endpoint("timeline/segment/annotation/toggle", POST_JSON, lambda w: {"timeline_segment_id": h(w.segment), "annotation_id": h(w.annotation)}, "write"),
    Endpoint("timeline/segment/annotation/delete", POST_JSON, lambda w: {"timeline_segment_annotation_id": h(w.segment_annotation)}, "write"),
    # ---------- annotations and shortcuts
    Endpoint("annotation/create", POST_JSON, lambda w: {"name": "new", "video_id": h(w.video), "category_id": h(w.category)}, "write"),
    Endpoint("annotation/update", POST_JSON, lambda w: {"annotation_id": h(w.annotation), "name": "renamed", "category_id": h(w.category)}, "write"),
    Endpoint("annotation/category/create", POST_JSON, lambda w: {"name": "newcat", "video_id": h(w.video)}, "write"),
    Endpoint("annotation/shortcut/update", POST_JSON, lambda w: {"video_id": h(w.video), "annotation_shortcuts": [{"id": h(w.annotation), "keys": ["b"]}]}, "write"),
    Endpoint("shortcut/create", POST_JSON, lambda w: {"key": "k", "video_id": h(w.video)}, "write"),
    Endpoint("annotation/shortcut/create", POST_JSON, lambda w: {"annotation_id": h(w.annotation2), "keys": ["c"], "video_id": h(w.video)}, "write"),
    # ---------- tracking results (bounding boxes)
    Endpoint("position_data/bboxes/edit", POST_JSON, lambda w: {"object_tracker_run_id": h(w.plugin_run), "bbox_id": "0-1", "new_player_id": 7, "new_team_id": 3}, "write"),
    Endpoint("position_data/bboxes/replace", POST_JSON, lambda w: {"object_tracker_run_id": h(w.plugin_run), "bboxes": {"0": [[1, 3, 0, 0, 1, 1]]}}, "write"),
    Endpoint("position_data/bboxes/delete", POST_JSON, lambda w: {"object_tracker_run_id": h(w.plugin_run), "bbox_id": "0-1"}, "write"),
    # ---------- calibration
    Endpoint("calibration_assets/create", POST_JSON, lambda w: {"name": "cal2", "video_id": h(w.video)}, "write"),
    Endpoint("calibration_assets/update", POST_JSON, lambda w: {"id": h(w.calibration), "name": "renamed"}, "write"),
    Endpoint("calibration_assets/delete", POST_JSON, lambda w: {"id": h(w.calibration)}, "write"),
    # ---------- clusters
    Endpoint("cluster/timeline/item/create", POST_JSON, lambda w: {"video_id": h(w.video), "plugin_run": h(w.plugin_run), "name": "c3", "type": "A"}, "write"),
    Endpoint("cluster/timeline/item/delete", POST_JSON, lambda w: {"id": h(w.cluster2)}, "write"),
    Endpoint("cluster/timeline/item/rename", POST_JSON, lambda w: {"cti_id": h(w.cluster), "name": "renamed"}, "write"),
    Endpoint("cluster/timeline/item/merge", POST_JSON, lambda w: {"from_id": h(w.cluster), "to_id": h(w.cluster2)}, "write"),
    Endpoint("cluster/item/delete", POST_JSON, lambda w: {"item_ids": [h(w.cluster_item)], "cluster_id": h(w.cluster)}, "write"),
    Endpoint("cluster/item/move", POST_JSON, lambda w: {"item_ids": [h(w.cluster_item)], "new_cluster_id": h(w.cluster2)}, "write"),
    # ---------- video analysis state
    Endpoint("video/analysis/setselectedshots", POST_JSON, lambda w: {"video_id": h(w.video), "timeline_id": h(w.timeline)}, "write"),
    Endpoint("video/analysis/setselectedplaceclustering", POST_JSON, lambda w: {"video_id": h(w.video), "plugin_run_id": h(w.plugin_run)}, "write"),
    Endpoint("video/analysis/setselectedfaceclustering", POST_JSON, lambda w: {"video_id": h(w.video), "plugin_run_id": h(w.plugin_run)}, "write"),
    # ---------- tracking data and plugin runs
    Endpoint("tracking_data/rename", POST_JSON, lambda w: {"id": h(w.tracking_data), "name": "renamed"}, "write"),
    Endpoint("plugin/run/new", POST_JSON, lambda w: {"plugin": "object_tracker", "video_id": h(w.video), "parameters": {}}, "write"),
]
