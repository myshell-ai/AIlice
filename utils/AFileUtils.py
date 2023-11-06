
def LoadTXTFile(path: str) -> str:
    ret = ""
    with open(path,'r') as file:
        ret += file.read()
    return ret