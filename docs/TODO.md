

- How to manage asset files (model checkpoints, template images, etc.)?
- Create a `pyproject.toml` file for `backend/backend` to manage formatting and linting configurations.
- wrapper function for decode/auth for all relevant requests: See `backend/backend/views/calibration_assets.py`: Move to `backend/backend/utils/decode_and_authentificate.py`
- autocompile protobuf grpc  https://github.com/ray-project/ray/commit/f5fbe8b67805ad45148dc5dca88d49448aabceda
