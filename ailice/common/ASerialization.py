import ast
import json
import inspect
import inspect
import typing
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

TYPE_NAMESPACE = {
    'bool': bool,
    'int': int,
    'float': float,
    'complex': complex,
    'str': str,
    'bytes': bytes,
    'bytearray': bytearray,
    'None': None,
    'tuple': tuple,
    'list': list,
    'dict': dict,
    'set': set,
    'Optional': typing.Optional,
    'Union': typing.Union,
    'Any': typing.Any,
    'Callable': typing.Callable,
    'TypeVar': typing.TypeVar,
    'Generic': typing.Generic
}

def SignatureFromString(sig_str: str) -> inspect.Signature:
    funcDefNode = ast.parse(f"def f{sig_str}:\n    pass", mode='exec').body[0]
    
    def BuildArg(arg, kind):
        annotation = BuildTypeFromAST(arg.annotation, TYPE_NAMESPACE) if arg.annotation else inspect.Parameter.empty
        return inspect.Parameter(name=arg.arg, kind=kind, annotation=annotation)

    parameters = []
    for arg in funcDefNode.args.args:
        parameters.append(BuildArg(arg, inspect.Parameter.POSITIONAL_OR_KEYWORD))

    if funcDefNode.args.vararg:
        parameters.append(BuildArg(funcDefNode.args.vararg, inspect.Parameter.VAR_POSITIONAL))
    
    if funcDefNode.args.kwarg:
        parameters.append(BuildArg(funcDefNode.args.kwarg, inspect.Parameter.VAR_KEYWORD))
    
    defaults = funcDefNode.args.defaults
    if defaults:
        offset = len(parameters) - len(defaults)
        for i, default in enumerate(defaults):
            try:
                defaultValue = ast.literal_eval(default)
            except (ValueError, SyntaxError):
                defaultValue = inspect.Parameter.empty
                
            parameters[offset + i] = parameters[offset + i].replace(default=defaultValue)
    
    returnAnnotation = BuildTypeFromAST(funcDefNode.returns, TYPE_NAMESPACE) if funcDefNode.returns else inspect.Parameter.empty
    return inspect.Signature(parameters=parameters, return_annotation=returnAnnotation)


def BuildTypeFromAST(node, namespace):
    if isinstance(node, ast.Name):
        return namespace.get(node.id, typing.Any)
    
    elif isinstance(node, ast.Subscript):
        container = BuildTypeFromAST(node.value, namespace)
        
        args = node.slice
        if isinstance(args, ast.Tuple):
            type_args = [BuildTypeFromAST(arg, namespace) for arg in args.elts]
            return container[tuple(type_args)]
        else:
            type_arg = BuildTypeFromAST(args, namespace)
            return container[type_arg]
    
    elif isinstance(node, ast.Tuple):
        return tuple(BuildTypeFromAST(elt, namespace) for elt in node.elts)
    
    elif isinstance(node, ast.Constant) and node.value is None:
        return None
    
    else:
        return typing.Any

def AnnotationsFromSignature(signature: inspect.Signature) -> dict:
    annotations = {}
    
    for param_name, param in signature.parameters.items():
        if param.annotation is not inspect.Parameter.empty:
            annotations[param_name] = param.annotation
    
    if signature.return_annotation is not inspect.Parameter.empty:
        annotations['return'] = signature.return_annotation
    return annotations
