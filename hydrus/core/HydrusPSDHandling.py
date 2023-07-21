import struct
import typing

from PIL import Image as PILImage

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusImageHandling

try:
    
    from psd_tools import PSDImage
    from psd_tools.constants import ChannelID, Tag, ColorMode, Resource
    
    PSD_TOOLS_OK = False
    
except:
    
    PSD_TOOLS_OK = False


def MergedPILImageFromPSD(path: str) -> PILImage:
    
    psd = PSDImage.open(path)

    pil_image = psd.topil()

    no_alpha = psd._record.layer_and_mask_information.layer_info is not None and psd._record.layer_and_mask_information.layer_info.layer_count > 0

    if(HydrusImageHandling.PILImageHasTransparency(pil_image) and no_alpha):
        # merged image from psd-tools has transparency when it shouldn't
        # see https://github.com/psd-tools/psd-tools/issues/369
        # and https://github.com/psd-tools/psd-tools/pull/370

        # I think it's fine to convert to RGB in all cases since eventually
        # that has to happen for the thumbnail anyway.
        pil_image = pil_image.convert("RGB")

    return pil_image


def GenerateThumbnailBytesFromPSDPath(path: str, target_resolution: typing.Tuple[int, int], clip_rect = None) -> bytes:
    
    if not PSD_TOOLS_OK:
        
        raise Exception( 'psd_tools unavailable' )

    pil_image = MergedPILImageFromPSD(path)

    if clip_rect is not None:
        
        pil_image = HydrusImageHandling.ClipPILImage( pil_image, clip_rect )
        
    
    thumbnail_pil_image = pil_image.resize( target_resolution, PILImage.ANTIALIAS )
    
    thumbnail_bytes = HydrusImageHandling.GenerateThumbnailBytesPIL( thumbnail_pil_image )
    
    return thumbnail_bytes



def GetPSDResolution(path: str):

    if not PSD_TOOLS_OK:

        return GetPSDResolutionFallback(path)

    psd = PSDImage.open(path)

    resolution = (psd.width, psd.height)

    return resolution

def GetPSDResolutionFallback(path: str):
    
    with open( path, 'rb' ) as f:
        
        f.seek( 14 )
        
        height_bytes = f.read( 4 )
        width_bytes = f.read( 4 )
        
    
    height: int = struct.unpack( '>L', height_bytes )[0]
    width: int = struct.unpack( '>L', width_bytes )[0]
    
    return ( width, height )
    
