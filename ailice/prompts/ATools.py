import json

def ConstructOptPrompt(func, low:int, high: int, maxLen: int) -> tuple[str, int, int]:
    prompt = None
    n = None
    while low <= high:
        mid = (low + high) // 2
        p, length = func(mid)
        if length < maxLen:
            n = mid
            prompt = p
            low = mid + 1
        else:
            high = mid - 1
    return prompt, n, length


def FindRecords(prompt: str, selector, num: int, storage, collection) -> list:
    selector = (lambda x: True) if None == selector else selector
    res = []
    l = num
    while (num < 0) or (len(res) < num):
        l = l * 2
        rs = [json.loads(r) for r,_ in storage.Query(collection=collection, clue=prompt, num_results=l)]
        res = [r for r in rs if selector(r)]
        if (num < 0) or (len(rs) < l):
            break
            
    return res[:num] if num > 0 else res