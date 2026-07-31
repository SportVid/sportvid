import json
import numpy as np
import numpy.typing as npt
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NDArrayData:
    name: str
    shape: list[int] = field(default_factory=list)
    dtype: str = ""
    data: bytes = b""

    @classmethod
    def from_array(cls, name: str, arr: npt.NDArray[Any]) -> "NDArrayData":
        arr = np.ascontiguousarray(arr)
        return cls(
            name=name,
            shape=list(arr.shape),
            dtype=str(arr.dtype),
            data=arr.tobytes(),
        )

    def to_array(self) -> npt.NDArray[Any]:
        arr = np.frombuffer(self.data, dtype=np.dtype(self.dtype))
        return arr.reshape(self.shape)