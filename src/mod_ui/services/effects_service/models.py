"""
Data models for the Effects Service
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class EffectAddRequest(BaseModel):
    """Request to add an effect to the pedalboard"""

    uri: str
    x: float = 0.0
    y: float = 0.0


class EffectAddResponse(BaseModel):
    """Response from adding an effect"""

    success: bool
    instance: Optional[str] = None
    plugin_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class EffectRemoveRequest(BaseModel):
    """Request to remove an effect from the pedalboard"""

    instance: str


class EffectRemoveResponse(BaseModel):
    """Response from removing an effect"""

    success: bool
    error: Optional[str] = None


class EffectGetRequest(BaseModel):
    """Request to get effect information"""

    uri: str
    cached: bool = True


class EffectGetResponse(BaseModel):
    """Response with effect information"""

    success: bool
    plugin_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class EffectListRequest(BaseModel):
    """Request to list all available effects"""

    pass


class EffectListResponse(BaseModel):
    """Response with list of all available effects"""

    success: bool
    plugins: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class EffectBulkRequest(BaseModel):
    """Request for bulk effect operations"""

    operation: str
    effects: List[Dict[str, Any]]


class EffectBulkResponse(BaseModel):
    """Response from bulk effect operations"""

    success: bool
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class EffectParameterSetRequest(BaseModel):
    """Request to set effect parameter"""

    instance: str
    symbol: str
    value: Union[float, int, str, bool]


class EffectParameterSetResponse(BaseModel):
    """Response from setting effect parameter"""

    success: bool
    error: Optional[str] = None


class EffectParameterAddressRequest(BaseModel):
    """Request to address effect parameter"""

    instance: str
    symbol: str
    addressing_data: Dict[str, Any]


class EffectParameterAddressResponse(BaseModel):
    """Response from addressing effect parameter"""

    success: bool
    addressing_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class EffectConnectRequest(BaseModel):
    """Request to connect effect ports"""

    port_from: str
    port_to: str


class EffectConnectResponse(BaseModel):
    """Response from connecting effect ports"""

    success: bool
    error: Optional[str] = None


class EffectDisconnectRequest(BaseModel):
    """Request to disconnect effect ports"""

    port_from: str
    port_to: str


class EffectDisconnectResponse(BaseModel):
    """Response from disconnecting effect ports"""

    success: bool
    error: Optional[str] = None


class EffectPresetLoadRequest(BaseModel):
    """Request to load effect preset"""

    instance: str
    uri: str
    bundle: str


class EffectPresetLoadResponse(BaseModel):
    """Response from loading effect preset"""

    success: bool
    error: Optional[str] = None


class EffectPresetSaveRequest(BaseModel):
    """Request to save effect preset"""

    instance: str
    uri: str
    bundle: str
    label: str
    replace: bool = False


class EffectPresetSaveResponse(BaseModel):
    """Response from saving effect preset"""

    success: bool
    bundle_path: Optional[str] = None
    error: Optional[str] = None


class EffectPresetDeleteRequest(BaseModel):
    """Request to delete effect preset"""

    instance: str
    uri: str
    bundle: str


class EffectPresetDeleteResponse(BaseModel):
    """Response from deleting effect preset"""

    success: bool
    error: Optional[str] = None


class EffectImageRequest(BaseModel):
    """Request for effect image"""

    uri: str
    image_type: str  # "screenshot" or "thumbnail"


class EffectImageResponse(BaseModel):
    """Response with effect image data"""

    success: bool
    image_path: Optional[str] = None
    content_type: Optional[str] = None
    error: Optional[str] = None


class EffectFileRequest(BaseModel):
    """Request for effect file"""

    uri: str
    filename: str


class EffectFileResponse(BaseModel):
    """Response with effect file data"""

    success: bool
    file_path: Optional[str] = None
    content_type: Optional[str] = None
    error: Optional[str] = None
