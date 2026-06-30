import os
import tempfile
import pytest
from PIL import Image

from app.api.v1.endpoints.agent import merge_image_and_mask

def test_merge_image_and_mask():
    # Create temporary original image (100x100 RGB, solid green)
    orig_img = Image.new("RGB", (100, 100), color=(0, 255, 0))
    
    # Create temporary mask image (100x100 L/grayscale, left half black, right half white)
    # White = masked region (inpainting), Black = unmasked region
    mask_img = Image.new("L", (100, 100), color=0)
    for x in range(50, 100):
        for y in range(100):
            mask_img.putpixel((x, y), 255)
            
    with tempfile.TemporaryDirectory() as tmpdir:
        orig_path = os.path.join(tmpdir, "original.png")
        mask_path = os.path.join(tmpdir, "mask.png")
        output_path = os.path.join(tmpdir, "merged.png")
        
        orig_img.save(orig_path)
        mask_img.save(mask_path)
        
        # Merge them
        merge_image_and_mask(orig_path, mask_path, output_path)
        
        # Verify merged result
        assert os.path.exists(output_path)
        merged_img = Image.open(output_path)
        
        # Check mode and size
        assert merged_img.mode == "RGBA"
        assert merged_img.size == (100, 100)
        
        # Verify alpha values:
        # Left half (unmasked, mask=0) -> alpha should be 255 (opaque)
        # Right half (masked, mask=255) -> alpha should be 0 (transparent)
        left_pixel = merged_img.getpixel((25, 50))
        assert left_pixel[3] == 255 # Alpha channel is the 4th element
        
        right_pixel = merged_img.getpixel((75, 50))
        assert right_pixel[3] == 0
