
def LoadTXTFile(path: str) -> str:
    ret = ""
    with open(path,'r') as file:
        ret += file.read()
    return ret

def serialize(obj):
    if hasattr(obj, "ToJson"):
        return obj.ToJson()
    else:
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")