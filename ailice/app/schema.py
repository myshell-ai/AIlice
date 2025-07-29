import copy
from typing import Any, Dict, List, Literal, Optional, Union, Annotated
from pydantic import BaseModel, Field, model_validator, field_validator


def build_settings_schema(config):
    return {
        "type": "tabs",
        "activeTab": "agent-models",
        "tabs": [
            {
                "id": "agent-models",
                "title": "Agent Models",
                "content": build_agent_models_schema(config["agentModelConfig"], config["models"])
            },
            {
                "id": "model-providers",
                "title": "Model Providers",
                "content": build_providers_schema(config["models"])
            },
            {
                "id": "inference",
                "title": "Inference",
                "content": build_inference_schema(config["temperature"], config["contextWindowRatio"])
            }
        ]
    }


def build_agent_models_schema(agent_model_config, models):
    model_options = get_all_model_options(models)
    
    rows = []
    for agent, model in agent_model_config.items():
        rows.append({
            "cells": [
                agent,
                {
                    "type": "formGroup",
                    "label": "",
                    "id": f"agent-model-{agent}",
                    "inputType": "select",
                    "value": model,
                    "path": ["agentModelConfig", agent],
                    "options": model_options,
                    "disabled": False
                },
                {
                    "type": "button",
                    "text": "Remove",
                    "className": "remove-button",
                    "disabled": False,
                    "onClick": f"removeAgentType('{agent}')"
                }
            ]
        })
    
    
    defaultLLM = agent_model_config.get("DEFAULT", "openrouter:qwen-2.5-72b-instruct" if (len(model_options) == 0) or ("openrouter:qwen-2.5-72b-instruct" in model_options) else model_options[0])
    
    return {
        "type": "section",
        "title": "Agent Model Configuration",
        "description": '''Configure which model each agent type should use. \nNote: Set up the provider's API key in "Model Providers" first to use their models.''',
        "disabled": False,
        "content": [
            {
                "type": "button",
                "text": "Add Agent Type",
                "className": "add-button",
                "icon": "+",
                "disabled": False,
                "onClick": f"addNewAgentType('{defaultLLM}')"
            },
            {
                "type": "table",
                "columns": ["Agent Type", "Model", "Actions"],
                "disabled": False,
                "rows": rows
            }
        ]
    }


def build_providers_schema(models):
    content = [
        {
            "type": "button",
            "text": "Add Provider",
            "className": "add-button",
            "icon": "+",
            "disabled": True,
            "onClick": "addNewProvider()"
        }
    ]
    
    for provider_name, provider_config in models.items():
        buildin_providers = ["openrouter", "apipie", "anthropic", "oai", "mistral", "deepseek", "groq"]
        isDefault = (provider_name == "default")
        disabled = provider_name in buildin_providers

        provider_card = {
            "type": "card",
            "id": f"provider-{provider_name}",
            "title": provider_name,
            "removable": not (disabled or isDefault),
            "collapsible": True,
            "disabled": False,
            "onRemove": f"removeProvider('{provider_name}')",
            "content": [
                {
                    "type": "formRow",
                    "disabled": False,
                    "content": [
                        {
                            "type": "formGroup",
                            "id": f"provider-{provider_name}-wrapper",
                            "label": "Model Wrapper",
                            "inputType": "select",
                            "value": provider_config["modelWrapper"],
                            "path": ["models", provider_name, "modelWrapper"],
                            "options": [
                                {"value": "AModelChatGPT", "label": "openai"}
                            ],
                            "disabled": isDefault
                        }] +
                        ([{
                            "type": "formGroup",
                            "id": f"provider-{provider_name}-apikey",
                            "label": "API Key",
                            "inputType": "password",
                            "value": provider_config["apikey"],
                            "path": ["models", provider_name, "apikey"],
                            "disabled": isDefault
                        }] if "apikey" in provider_config else []) +
                        ([{
                            "type": "formGroup",
                            "id": f"provider-{provider_name}-baseurl",
                            "label": "Base URL",
                            "inputType": "text",
                            "value": provider_config["baseURL"],
                            "path": ["models", provider_name, "baseURL"],
                            "disabled": isDefault
                        }] if "baseURL" in provider_config else [])
                },
                #build_models_section(provider_name, provider_config["modelList"], disabled or isDefault)
            ]
        }
        content.append(provider_card)
    
    return {
        "type": "section",
        "title": "Model Providers Configuration",
        "description": "Configure API keys for model providers.",
        "disabled": False,
        "content": content
    }


def build_models_section(provider_name, model_list, disabled):
    content = [
        {
            "type": "button",
            "text": "Add Model",
            "className": "add-button",
            "icon": "+",
            "disabled": True,
            "onClick": f"addNewModel('{provider_name}')"
        }
    ]
    
    for model_name, model_config in model_list.items():
        model_card = {
            "type": "card",
            "id": f"model-{provider_name}-{model_name}",
            "title": model_name,
            "removable": not disabled,
            "collapsible": True,
            "disabled": False,
            "onRemove": f"removeModel('{provider_name}', '{model_name}')",
            "content": [
                {
                    "type": "formRow",
                    "disabled": False,
                    "content": [
                        {
                            "type": "formGroup",
                            "id": f"model-{provider_name}-{model_name}-formatter",
                            "label": "Formatter",
                            "inputType": "select",
                            "value": model_config["formatter"],
                            "path": ["models", provider_name, "modelList", model_name, "formatter"],
                            "options": [
                                {"value": "AFormatterGPT", "path": [], "label": "chat only"},
                                {"value": "AFormatterGPTVision", "path": [], "label": "vision"}
                            ],
                            "disabled": disabled
                        },
                        {
                            "type": "formGroup",
                            "id": f"model-{provider_name}-{model_name}-contextwindow",
                            "label": "Context Window",
                            "inputType": "number",
                            "value": model_config["contextWindow"],
                            "path": ["models", provider_name, "modelList", model_name, "contextWindow"],
                            "disabled": disabled
                        }
                    ]
                },
                {
                    "type": "checkbox",
                    "id": f"model-{provider_name}-{model_name}-systemasuser",
                    "label": "System As User",
                    "checked": model_config["systemAsUser"],
                    "disabled": disabled
                }
            ]
        }
        content.append(model_card)
    
    return {
        "type": "section",
        "id": f"provider-{provider_name}-models-section",
        "title": "Models",
        "disabled": False,
        "content": content
    }


def build_inference_schema(temperature, context_window_ratio):
    disabled=False
    return {
        "type": "section",
        "title": "Inference Settings",
        "description": "Configure inference parameters for the AI model.",
        "disabled": disabled,
        "content": [
            {
                "type": "range",
                "id": "inference-temperature",
                "label": "Temperature",
                "min": "0",
                "max": "2",
                "step": "0.1",
                "value": temperature,
                "path": ["temperature"],
                "disabled": disabled,
                "tooltip": "Controls randomness: Lower values make the model more deterministic, higher values make it more creative."
            },
            {
                "type": "range",
                "id": "inference-contextratio",
                "label": "Context Window Ratio",
                "min": "0",
                "max": "1",
                "step": "0.05",
                "value": context_window_ratio,
                "path": ["contextWindowRatio"],
                "disabled": disabled,
                "tooltip": "Determines how much of the context window is used for the conversation history. Value between 0 and 1."
            }
        ]
    }


def get_all_model_options(models):
    model_options = []
    
    for provider_name, provider in models.items():
        if (provider.get("apikey", None) in ["", None]):
            continue
        for model_name in provider["modelList"].keys():
            model_id = f"{provider_name}:{model_name}"
            model_options.append({
                "value": model_id,
                "label": model_id
            })
    
    return sorted(model_options, key=lambda x: x["value"])

class PatchOperation(BaseModel):
    op: Literal["replace", "add", "remove"] = Field(description="patch operation type.")
    path: List[Union[str, int]] = Field(description="target path represented in a list.")
    value: Optional[Any] = Field(None, description="new value. optional for 'remove' op.")

    @field_validator("path")
    @classmethod
    def validate_path_not_empty(cls, path: List[Union[str, int]]) -> List[Union[str, int]]:
        if not path:
            raise ValueError("The patch path should not be empty.")
        return path

    @model_validator(mode='after')
    def validate_value_for_operation(self) -> 'PatchOperation':
        if self.op in ["replace", "add"] and self.value is None:
            raise ValueError(f"'{self.op}'The operation requires the 'value' field to be provided.")
        return self


class ConfigPatchSet(BaseModel):
    patches: List[PatchOperation] = Field(description="List of patches to apply.")


def validate_patches(patches: List[Dict[str, Any]]) -> List[PatchOperation]:
    validated = ConfigPatchSet(patches=patches)
    return validated.patches

def check_path(path: List[Union[str, int]], allowed_path: List[Union[str, int]]) -> bool:
    def match_key(key, pattern):
        if isinstance(key, str) and isinstance(pattern, str):
            return (key == pattern) or ("*" == pattern)
        if isinstance(key, int) and isinstance(pattern, int):
            return (key == pattern) or (-1 == pattern)
        if isinstance(pattern, list):
            return any([match_key(key, p) for p in pattern])
        else:
            raise ValueError(f"Invalid type in path: {key}")
    if not match_key(path[0], allowed_path[0]):
        return False
    if (len(allowed_path) == 1):
        return True
    if (len(path) == 1) and (len(allowed_path) > 1):
        return False
    return check_path(path[1:], allowed_path[1:])

def apply_patches(config: Dict[str, Any], validated_patches: List[PatchOperation]) -> Dict[str, Any]:
    config_copy = copy.deepcopy(config)
    
    for patch in validated_patches:
        op = patch.op
        path = patch.path
        value = patch.value
        
        target = config_copy
        parent = None
        last_key = None
        
        for i, key in enumerate(path[:-1]):
            parent = target
            last_key = key
            
            if isinstance(target, dict) and key in target:
                target = target[key]
            elif isinstance(target, list) and isinstance(key, int) and 0 <= key < len(target):
                target = target[key]
            else:
                raise ValueError(f"Invalid path: {path[:i+1]}")
        
        if op == "replace":
            if isinstance(target, dict) and path[-1] in target:
                target[path[-1]] = value
            elif isinstance(target, list) and isinstance(path[-1], int) and 0 <= path[-1] < len(target):
                target[path[-1]] = value
            else:
                raise ValueError(f"Unable to replace value of path {path}, target does not exist.")
                
        elif op == "add":
            if isinstance(target, dict):
                target[path[-1]] = value
            elif isinstance(target, list) and isinstance(path[-1], int) and 0 <= path[-1] <= len(target):
                target.insert(path[-1], value)
            else:
                raise ValueError(f"Cannot add to path {path}, invalid target.")
                
        elif op == "remove":
            if isinstance(target, dict) and path[-1] in target:
                del target[path[-1]]
            elif isinstance(target, list) and isinstance(path[-1], int) and 0 <= path[-1] < len(target):
                del target[path[-1]]
            else:
                raise ValueError(f"Unable to delete item at path {path}, target does not exist.")
    
    return config_copy