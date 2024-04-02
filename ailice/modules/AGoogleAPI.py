#The primary work of this module is completed by AIlice.
#This module can be used to replace AGoogle.py by utilizing Google's official API for search tasks.
#The replacement method involves the following configuration in the configuration file(note that you need to fill in the api_key and cse_id.):
#
#    "google": {
#      "cmd": "python3 -m ailice.modules.AGoogleAPI --addr=ipc:///tmp/AGoogle.ipc --api_key=YOUR_API_KEY --cse_id=YOUR_CSE_ID",
#      "addr": "ipc:///tmp/AGoogle.ipc"
#    },


from googleapiclient.discovery import build
from ailice.common.lightRPC import makeServer
from ailice.modules.AScrollablePage import AScrollablePage

class AGoogle(AScrollablePage):
    def __init__(self, api_key: str, cse_id: str):
        super(AGoogle, self).__init__({"SCROLLDOWN": "SCROLLDOWNGOOGLE"})
        self.api_key = api_key
        self.cse_id = cse_id
        self.service = build("customsearch", "v1", developerKey=self.api_key)
        return
    
    def ModuleInfo(self):
        return {
            "NAME": "google",
            "ACTIONS": {
                "GOOGLE": {"func": "Google", "prompt": "Use Google to search the web."},
                "SCROLLDOWNGOOGLE": {"func": "ScrollDown", "prompt": "Scroll down the search results."}
            }
        }
    
    def Google(self, keywords: str) -> str:
        try:
            res = self.service.cse().list(q=keywords, cx=self.cse_id).execute()
            ret = str(res.get('items', []))
        except Exception as e:
            print("Google Search exception: ", e)
            ret = f"Google Search exception: {str(e)}"
        self.LoadPage(ret, "TOP")
        return self()

if __name__ == '__main__':    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr', type=str, help="The address where the service runs on.")
    parser.add_argument('--api_key', type=str, help="Google api key. You can create it in 'https://console.cloud.google.com/'.")
    parser.add_argument('--cse_id', type=str, help="Search engine ID(or the 'CX' value).")

    args = parser.parse_args()
    makeServer(objCls=AGoogle, objArgs={'api_key': args.api_key, 'cse_id': args.cse_id}, url=args.addr, APIList=["ModuleInfo", "Google", "ScrollDown"]).Run()
