from typing import Protocol

import numpy as np


class MediaFrameSource(Protocol):
    def read_sample(self) -> np.ndarray | None: ...

    def close(self) -> None: ...
