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
  def __init__(self,obj,url,APIList):
    self.url=url
    self.obj=obj
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
        if "GET_META" in msg:
          ret={"META":{"methods": [method for method in self.APIList]}}
        else:
          ret={'ret':(getattr(self.obj,msg['function'])(*msg['args'], **msg['kwargs']))}
      except Exception as e:
        ret={'exception':e}
        traceback.print_tb(e.__traceback__)
        print('Exception. msg: ',str(msg),'. Except: ',str(e))
      SendMsg(socket,ret)
    return


def makeServer(obj,url,APIList):
  return GenesisRPCServer(obj,url,APIList)

def AddMethod(kls,methodName):
  def methodTemplate(self,*args,**kwargs):
    return self.RemoteCall(methodName,args,kwargs)
  setattr(kls,methodName,methodTemplate)

def makeClient(url,returnClass=False):
  class GenesisRPCClientTemplate(object):
    def __init__(self):
      self.url=url
      self.context=context
      return
    
    def RemoteCall(self,funcName,args,kwargs):
      with self.context.socket(zmq.REQ) as socket:
        socket.setsockopt(zmq.CONNECT_TIMEOUT, 10000)
        socket.setsockopt(zmq.HEARTBEAT_IVL, 2000)
        socket.setsockopt(zmq.HEARTBEAT_TIMEOUT, 10000)

        socket.connect(url)
        SendMsg(socket,{'function':funcName,'args':args, "kwargs": kwargs})
        ret=ReceiveMsg(socket)
      if 'exception' in ret:
        raise ret['exception']
      return ret['ret']
  
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
