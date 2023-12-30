from setuptools import setup, find_packages

setup(
    name='ailice',
    version='0.2.0',
    packages=find_packages(),
    package_data={
        'ailice': ['prompts/*.txt'],
    },
    install_requires=[
        'zmq',
        'termcolor',
        'simplejson',
        'transformers>=4.0.0',
        'torch',
        'accelerate',
        'bitsandbytes',
        'peft',
        'appdirs',
        'openai',
        'gradio',
        'importlib-metadata',
        'chromadb',
        'googlesearch-python',
        'urlextract', 'selenium>=4.10.0', 'html2text', 'nougat-ocr', 'scipy', 'scikit-learn',
        'arxiv'
    ],
    extras_require={
        'finetuning': ['bitsandbytes', 'datasets',],
        'speech': ['typeguard==2.13.3', 'sounddevice', 'numpy', 'librosa', 'datasets', 'SpeechRecognition', 'espnet', 'espnet-model-zoo', 'espnet-tts-frontend', 'torchaudio',],
    },
    author='Steven Lu',
    author_email='stevenlu1729@gmail.com',
    description='A lightweight AI Agent',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/stevenlu137/AIlice',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)