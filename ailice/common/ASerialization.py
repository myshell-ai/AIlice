import json
from ailice.common.ADataType import AImage, AImageLocation, AVideo, AVideoLocation

class AJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, AImage):
            return {"_type": "AImage", "value": obj.ToJson()}
        elif isinstance(obj, AImageLocation):
            return {"_type": "AImageLocation", "value": obj.ToJson()}
        elif isinstance(obj, AVideo):
            return {"_type": "AVideo", "value": obj.ToJson()}
        elif isinstance(obj, AVideoLocation):
            return {"_type": "AVideoLocation", "value": obj.ToJson()}
        else:
            return super(AJSONEncoder, self).default(obj)

class AJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if "_type" not in obj:
            return obj
        type = obj["_type"]
        if type == "AImage":
            return AImage.FromJson(obj["value"])
        elif type == 'AImageLocation':
            return AImageLocation.FromJson(obj["value"])
        elif type == 'AVideo':
            return AVideo.FromJson(obj["value"])
        elif type == 'AVideoLocation':
            return AVideoLocation.FromJson(obj["value"])
        return obj