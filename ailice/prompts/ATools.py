import json

def ConstructOptPrompt(func, low:int, high: int, maxLen: int) -> str:
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
    return prompt, n


def FindRecords(prompt: str, constrains: list[tuple[str,str]], num: int, storage, collection) -> list:
    constrains = [] if None == constrains else constrains
    res = [json.loads(r) for r,_ in storage.Query(collection=collection, clue=prompt, keywords=[v for k,v in constrains], num_results=num*2)]
    res = [r for r in res if all([(k in r) and (v == r[k]) for k,v in constrains])]
    return res[:num] if num > 0 else res