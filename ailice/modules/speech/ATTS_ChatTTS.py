import os
import appdirs
import ChatTTS


class T2S_ChatTTS():
    def __init__(self):
        self.device = "cuda"
        self.toneFile = os.path.join(appdirs.user_data_dir("ailice", "Steven Lu"), "speaker_tone")
        
        self.model = ChatTTS.Chat()
        succ = False
        for i in range(5):
            succ = self.model.load(compile=False)
            if succ:
                break
        if not succ:
            raise Exception("T2S_ChatTTS.__init__(): Load model FAILED, please retry.")
        
        if os.path.exists(self.toneFile):
            with open(self.toneFile, 'r') as f:
                self.rand_spk = f.read()
        else:
            self.SwitchTone()
        return
    
    def SwitchTone(self) -> str:
        self.rand_spk = self.model.sample_random_speaker()
        with open(self.toneFile, 'w') as f:
            f.write(self.rand_spk)
        return "The new speaker tone has been created."
    
    def To(self, device: str):
        self.model = self.model.to(device)
        self.device = device
        return
    
    def __call__(self, txt: str):
        params_infer_code = ChatTTS.Chat.InferCodeParams(
            spk_emb = self.rand_spk,
            temperature = .3,
            top_P = 0.7,
            top_K = 20,
        )
        params_refine_text = ChatTTS.Chat.RefineTextParams(
            prompt='[oral_2][laugh_0][break_6]',
        )
        wavs = self.model.infer([txt], params_refine_text = params_refine_text, params_infer_code = params_infer_code)
        return wavs[0],24000
