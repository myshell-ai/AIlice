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


def FindRelatedRecords(prompt: str, num: int, storage, collection) -> list:
    res = storage.Query(collection, prompt, num)
    return [json.loads(r[0]) for r in res]

def FindRecordsByConstrains(constrains: list[tuple[str,str]], num: int, storage, collection) -> list:
    res = [json.loads(r) for r in storage.Search(collection, [v for k,v in constrains], num)]
    return [r for r in res if all([(k in r) and (v == r[k]) for k,v in constrains])]