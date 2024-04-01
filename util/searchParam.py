import json

class SearchParam:
    def __init__(self, param_File):
        with open(param_File) as f:
            variables = json.load(f)
        for key, value in variables.items():
            setattr(self, key, value)