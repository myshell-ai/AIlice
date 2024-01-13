#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 15 11:39:09 2021

@author: Steven Lu
"""

import sys
import threading
import zmq
import pickle
import traceback

WORKERS_ADDR="inproc://workers"
context=zmq.Context()

def SendMsg(conn,msg):
  conn.send(pickle.dumps(msg))
  return
  
def ReceiveMsg(conn):
  return pickle.loads(conn.recv())

class GenesisRPCServer(object):
  def __init__(self,objFactory,url,APIList):
    self.objFactory=objFactory
    self.url=url
    self.objPool=dict()
    self.APIList=APIList
    self.context=context
    self.receiver = self.context.socket(zmq.ROUTER)
    self.receiver.bind(url)
    self.dealer = self.context.socket(zmq.DEALER)
    self.dealer.bind(WORKERS_ADDR)
    return
  
  def Run(self):
    try:
      for i in range(16):
        thread = threading.Thread(target=self.Worker, name="RPC-Worker-%d" % (i + 1))
        thread.daemon = True
        thread.start()

      zmq.device(zmq.QUEUE, self.receiver, self.dealer)
    except Exception as e:
      print('GenesisRPCServer:Run() FATAL EXCEPTION. ',self.url,', ',str(e))
      sys.exit(1)
    finally:
      self.receiver.close()
      self.dealer.close()
  
  def Worker(self):
    socket = self.context.socket(zmq.REP)
    socket.setsockopt(zmq.HEARTBEAT_IVL, 2000)
    socket.setsockopt(zmq.HEARTBEAT_TIMEOUT, 10000)
    socket.connect(WORKERS_ADDR)

    while True:
      msg=ReceiveMsg(socket)
      ret=None
      try:
        if ('clientID' in msg) and (msg['clientID'] not in self.objPool):
          ret = {"exception": KeyError(f"clientID {msg['clientID']} not exist.")}
        elif "GET_META" in msg:
          ret={"META":{"methods": [method for method in self.APIList]}}
        elif "CREATE" in msg:
          newID = str(max([int(k) for k in self.objPool]) + 1) if self.objPool else '10000000'
          self.objPool[newID]=self.objFactory()
          ret = {"clientID": newID}
        elif "DEL" in msg:
          del self.objPool[msg['clientID']]
        else:
          ret={'ret':(getattr(self.objPool[msg['clientID']],msg['function'])(*msg['args'], **msg['kwargs']))}
      except Exception as e:
        ret={'exception':e}
        traceback.print_tb(e.__traceback__)
        print('Exception. msg: ',str(msg),'. Except: ',str(e))
      SendMsg(socket,ret)
    return


def makeServer(objFactory,url,APIList):
  return GenesisRPCServer(objFactory,url,APIList)

def AddMethod(kls,methodName):
  def methodTemplate(self,*args,**kwargs):
    return self.RemoteCall(methodName,args,kwargs)
  setattr(kls,methodName,methodTemplate)

def makeClient(url,returnClass=False):
  class GenesisRPCClientTemplate(object):
    def __init__(self):
      self.url=url
      self.context=context
      self.clientID=self.Send({'CREATE':''})['clientID']
      return
    
    def Send(self, msg):
      with self.context.socket(zmq.REQ) as socket:
        socket.setsockopt(zmq.CONNECT_TIMEOUT, 10000)
        socket.setsockopt(zmq.HEARTBEAT_IVL, 2000)
        socket.setsockopt(zmq.HEARTBEAT_TIMEOUT, 10000)
        socket.connect(url)
        SendMsg(socket, msg)
        return ReceiveMsg(socket)
    
    def RemoteCall(self,funcName,args,kwargs):
      ret = self.Send({'clientID': self.clientID, 'function':funcName, 'args':args, "kwargs": kwargs})
      if 'exception' in ret:
        raise ret['exception']
      return ret['ret']

    def __del__(self):
      self.Send({'DEL':'', 'clientID': self.clientID})
      return
  
  with context.socket(zmq.REQ) as socket:
    socket.setsockopt(zmq.CONNECT_TIMEOUT, 10000)
    socket.setsockopt(zmq.SNDTIMEO, 10000) 
    socket.setsockopt(zmq.RCVTIMEO, 10000)
    socket.connect(url)
    SendMsg(socket,{'GET_META':''})
    ret=ReceiveMsg(socket)
  for funcName in ret['META']['methods']:
    AddMethod(GenesisRPCClientTemplate,funcName)
  return GenesisRPCClientTemplate if returnClass else GenesisRPCClientTemplate()
