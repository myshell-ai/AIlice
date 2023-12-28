import datasets
from datasets import GeneratorBasedBuilder, DatasetInfo, SplitGenerator, Split
from datasets.features import Features, Value, Sequence
from pathlib import Path
import simplejson as json


class MyDataset(GeneratorBasedBuilder):
    VERSION = datasets.Version("1.0.0")
    
    def _info(self):
        return DatasetInfo(
            description="AIlice trace dataset",
            features=Features({
                "conversations": Sequence({
                    "role": Value("string"),
                    "msg": Value("string"),
                }),
            }),
            supervised_keys=None,
        )
    
    def _split_generators(self, dl_manager):
        return [
            SplitGenerator(name=Split.TRAIN, gen_kwargs={"datasetDir": "/home/clouds/code/AIlice-github/AIlice/trace"}),
        ]
    
    def _generate_examples(self, datasetDir):
        idx = -1
        directoryPath = Path(datasetDir)
        for jsonFile in directoryPath.glob('*.json'):
            with jsonFile.open('r', encoding='utf-8') as f:
                data = json.load(f)
                for conv in self.ExtractConversations(data):
                    idx += 1
                    yield idx, {'conversations': conv}

    def ExtractConversations(self, trace):
        convs = []
        agentTrace = trace
        convs.append(agentTrace['conversations'])
        if 'subProcessors' in agentTrace:
            for agentTrace in agentTrace['subProcessors']:
                convs += self.ExtractConversations(agentTrace, convs)
        return convs