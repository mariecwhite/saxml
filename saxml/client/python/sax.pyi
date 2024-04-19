from typing import Any, Callable, List, Optional

from typing import overload

class AdminOptions:
    timeout: float
    def __init__(self) -> None: ...
    def __copy__(self) -> AdminOptions: ...
    def __deepcopy__(self, arg0: dict) -> AdminOptions: ...

class AudioModel:
    def __init__(self, *args, **kwargs) -> None: ...
    @overload
    def Recognize(self, id: str, options: ModelOptions = ...) -> list[tuple[str,float]]: ...
    @overload
    def Recognize(self, audio_bytes: str, options: ModelOptions = ...) -> list[tuple[str,float]]: ...

class CustomModel:
    def __init__(self, *args, **kwargs) -> None: ...
    @overload
    def Custom(self, request: bytes, method_name: str, options: ModelOptions = ...) -> bytes: ...
    @overload
    def Custom(self, request: bytes, method_name: str, options: ModelOptions = ...) -> bytes: ...

class LanguageModel:
    def __init__(self, *args, **kwargs) -> None: ...
    def Embed(self, text: str, options: ModelOptions = ...) -> list[float]: ...
    def Generate(self, text: str, options: ModelOptions = ...) -> list[tuple[str,float]]: ...
    def GenerateStream(self, text: str, callback: Callable, options: ModelOptions = ...) -> None: ...
    def Gradient(self, prefix: str, suffix: str, options: ModelOptions = ...) -> tuple[list[float],dict[str,list[float]]]: ...
    def Score(self, prefix: str, suffix: list[str], options: ModelOptions = ...) -> list[float]: ...

class Model:
    @overload
    def __init__(self, arg0: str, arg1: Options) -> None: ...
    @overload
    def __init__(self, arg0: str) -> None: ...
    def AM(self) -> AudioModel: ...
    def CM(self) -> CustomModel: ...
    def LM(self) -> LanguageModel: ...
    def MM(self) -> MultimodalModel: ...
    def VM(self) -> VisionModel: ...

class ModelDetail:
    def __init__(self, *args, **kwargs) -> None: ...
    @property
    def active_replicas(self) -> int: ...
    @property
    def ckpt(self) -> str: ...
    @property
    def max_replicas(self) -> int: ...
    @property
    def model(self) -> str: ...
    @property
    def overrides(self) -> dict[str,str]: ...

class ModelOptions:
    def __init__(self) -> None: ...
    def GetExtraInput(self, arg0: str) -> float: ...
    def GetTimeout(self) -> float: ...
    def SetExtraInput(self, arg0: str, arg1: float) -> None: ...
    def SetExtraInputString(self, arg0: str, arg1: str) -> None: ...
    def SetExtraInputTensor(self, arg0: str, arg1: list[float]) -> None: ...
    def SetTimeout(self, arg0: float) -> None: ...
    def ToDebugString(self) -> str: ...
    def ToProto(self, *args, **kwargs) -> Any: ...
    def __copy__(self) -> ModelOptions: ...
    def __deepcopy__(self, arg0: dict) -> ModelOptions: ...

class ModelServerTypeStat:
    def __init__(self, *args, **kwargs) -> None: ...
    @property
    def chip_topology(self) -> str: ...
    @property
    def chip_type(self) -> str: ...
    @property
    def num_replicas(self) -> int: ...

class MultimodalModel:
    def __init__(self, *args, **kwargs) -> None: ...
    def Embed(self, *args, **kwargs) -> Any: ...
    def Generate(self, *args, **kwargs) -> Any: ...
    def Score(self, *args, **kwargs) -> Any: ...

class Options:
    fail_fast: bool
    num_conn: int
    proxy_addr: str
    def __init__(self) -> None: ...
    def __copy__(self) -> Options: ...
    def __deepcopy__(self, arg0: dict) -> Options: ...

class VisionModel:
    def __init__(self, *args, **kwargs) -> None: ...
    def Classify(self, image_bytes: str, options: ModelOptions = ...) -> list[tuple[str,float]]: ...
    def Detect(self, image_bytes: str, text: list[str] = ..., boxes: list[tuple[float,float,float,float]] = ..., options: ModelOptions = ...) -> list[tuple[float,float,float,float,bytes,float,tuple[int,int,bytes]]]: ...
    def Embed(self, image: str, options: ModelOptions = ...) -> list[float]: ...
    def ImageToImage(self, text: str, options: ModelOptions = ...) -> list[tuple[bytes,float]]: ...
    def ImageToText(self, image_bytes: str, text: str = ..., options: ModelOptions = ...) -> list[tuple[bytes,float]]: ...
    def TextAndImageToImage(self, text: str, image_bytes: str, options: ModelOptions = ...) -> list[tuple[bytes,float]]: ...
    def TextToImage(self, text: str, options: ModelOptions = ...) -> list[tuple[bytes,float]]: ...
    def VideoToText(self, image_frames: list[str], text: str = ..., options: ModelOptions = ...) -> list[tuple[bytes,float]]: ...

def List(id: str, options: AdminOptions = ...) -> tuple[str,str,int]: ...
def ListAll(id: str, options: AdminOptions = ...) -> list[str]: ...
def ListDetail(id: str, options: AdminOptions = ...) -> ModelDetail: ...
def Publish(id: str, model_path: str, checkpoint_path: str, num_replicas: int, overrides: Optional[dict[str,str]] = ..., options: AdminOptions = ...) -> None: ...
def StartDebugPort(arg0: int) -> None: ...
def Stats(id: str, options: AdminOptions = ...) -> list[ModelServerTypeStat]: ...
def Unpublish(id: str, options: AdminOptions = ...) -> None: ...
def Update(id: str, model_path: str, checkpoint_path: str, num_replicas: int, options: AdminOptions = ...) -> None: ...
def WaitForReady(id: str, num_replicas: int, options: AdminOptions = ...) -> None: ...
