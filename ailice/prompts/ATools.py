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