import threading
from ailice.common.AExceptions import AExceptionOutofGas

class AGasTank():
    def __init__(self, amount: int):
        self.gas = amount
        return
    
    def Set(self, amount: int):
        self.gas = amount
        return
    
    def Consume(self, resourceType: str, amount) -> int:
        if (self.gas - amount) < 0:
            #print(f"consume: {amount}, total: {self.gas}. EXCEPTION raised.")
            raise AExceptionOutofGas()
        self.gas -= amount
        #print(f"consume: {amount}, remaining: {self.gas}")
        return self.gas
    
    def Charge(self, amount: int) -> int:
        self.gas += amount
        #print(f"charge: {amount}, remaining: {self.gas}")
        return self.gas