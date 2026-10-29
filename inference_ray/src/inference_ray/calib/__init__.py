"""Self-calibration of a static camera's lens distortion from the pitch markings.

Ported from trak (``trak/calib``, commit 55c018c), the prior-free ``trak-distortion-solve`` with its default
options: an angular-polynomial lens and one plane homography fitted to the markings detected around the
projection of the clicked keypoints, re-detected each round with the better lens. Not ported: the camera
geometry and goal frames, per-marking weights, the detector guide and the lens check.

* ``lens``: ``AngularLensModel`` (``r_u = tan(undist_poly(r_d))``) and the ``PinholeLens`` the rounds start from;
* ``camera``: pinhole camera + lens, ``CameraModel``;
* ``pitch``: the soccer pitch model and its markings as lines / conics;
* ``detection``: white marking points found perpendicular to the projected markings;
* ``pose``: focal length and pose from the clicks under any lens;
* ``solver``: the anchored lens fit, the rounds (``self_calibrate``) and the physical gauge.

Frames: trak's pitch frame throughout (metres, origin at the center mark, x along the pitch, y down in the
schematic, z down); ``pitch.corner_to_pitch`` converts from sportvid's (origin at the lower-left corner, y up).
Pixels: content-frame px with pixel centers at integers (OpenCV).
"""
