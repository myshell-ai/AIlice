import math

def TokenEstimatorOAI(conversations) -> int:
    ret = 0
    for c in conversations:
        ret += 4
        ret += len(c['msg']) // 4
        for a in c['attachments']:
            if "image" == a['type']:
                ret += EstimateImageTokens(a['content'].width, a['content'].height)
            elif "video" == a['type']:
                ret += EstimateImageTokens(a['content'].width, a['content'].height) * 10
    return ret

def EstimateImageTokens(width: int, height: int):
    if width > 2048 or height > 2048:
        aspect_ratio = width / height
        if aspect_ratio > 1:
            width, height = 2048, int(2048 / aspect_ratio)
        else:
            width, height = int(2048 * aspect_ratio), 2048
            
    if width >= height and height > 768:
        width, height = int((768 / height) * width), 768
    elif height > width and width > 768:
        width, height = 768, int((768 / width) * height)

    tiles_width = math.ceil(width / 512)
    tiles_height = math.ceil(height / 512)
    total_tokens = 85 + 170 * (tiles_width * tiles_height)
    return total_tokens