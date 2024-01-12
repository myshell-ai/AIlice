import re

def sentences_split(paragraph):
    for sent in re.findall(u'[^?。；，\.\?\;\,]+[?。；，\.\?\;\,]?', paragraph, flags=re.U):
        yield sent

def paragraph_generator(text):
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    for paragraph in paragraphs:
        yield paragraph