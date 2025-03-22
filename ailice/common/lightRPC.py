#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 15 11:39:09 2021

@author: Steven Lu
"""

import os
import sys
import threading
import inspect
import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator
import json
import traceback
from pydantic import validate_call
from ailice.common.ADataType import *
from ailice.common.AExceptions import ALightRPCException
from ailice.common.ASerialization import AJSONEncoder, AJSONDecoder, SignatureFromString, AnnotationsFromSignature

WORKERS_ADDR="inproc://workers"
context=zmq.Context()

def SendMsg(conn,msg):
  try:
    conn.send(json.dumps(msg, cls=AJSONEncoder).encode("utf-8"))
  except Exception as e:
     print("Exception: ", str(e))
     traceback.print_tb(e.__traceback__)
  return
  
def ReceiveMsg(conn):
  return json.loads(conn.recv().decode("utf-8"), cls=AJSONDecoder)

def validate_methods(cls, methodList=None):
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if (not name.startswith('_')) and ((methodList is None) or (name in methodList)):
            setattr(cls, name, validate_call(method, validate_return=(not inspect.isgeneratorfunction(method))))
    return cls

def GenerateCertificates(baseDir, name):
    keysDir = os.path.join(baseDir, 'certificates')
    os.makedirs(keysDir, exist_ok=True)
    
    publicFile, secretFile = zmq.auth.create_certificates(keysDir, name)
    return publicFile, secretFile

def LoadCertificate(filename):
    with open(filename, 'r') as f:
        keyText = f.read()
    return keyText

class GeneratorStorage:
    def __init__(self, obj):
        self.obj = obj
        self.generators = {}
        
    def SaveGenerator(self, generatorID, gen):
        self.generators[generatorID] = gen
        
    def GetGenerator(self, generatorID):
        return self.generators[generatorID]
        
    def __getattr__(self, name):
        return getattr(self.obj, name)

class GenesisRPCServer(object):
  def __init__(self, objCls, objArgs, url, APIList, enableSecurity=False, keysDir=None):
    self.objCls = validate_methods(objCls, APIList)
    self.objArgs = objArgs
    self.url = url
    self.objPool = dict()
    self.APIList = APIList
    self.context = context
    self.receiver = self.context.socket(zmq.ROUTER)
    
    self.enableSecurity = enableSecurity
    if enableSecurity:
      if keysDir is None:
        keysDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certificates')
      
      self.auth = ThreadAuthenticator(self.context)
      self.auth.start()
      self.auth.configure_curve(domain='*', location=zmq.auth.CURVE_ALLOW_ANY)
      
      serverPublicFile, serverSecretFile = zmq.auth.find_certificates(keysDir, "server")
      serverPublic, serverSecret = zmq.auth.load_certificate(serverSecretFile)
      
      self.receiver.curve_secretkey = serverSecret
      self.receiver.curve_publickey = serverPublic
      self.receiver.curve_server = True
    
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
      if self.enableSecurity:
        self.auth.stop()
      sys.exit(1)
    finally:
      self.receiver.close()
      self.dealer.close()
      if self.enableSecurity:
        self.auth.stop()
  
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
          methods=inspect.getmembers(self.objCls, predicate=lambda x: (inspect.isfunction(x) and x.__name__ in self.APIList))
          ret = {"META": {"methods": {methodName: {
                                        'signature': str(inspect.signature(method)),
                                        'is_generator': inspect.isgeneratorfunction(method)
                                      } for methodName, method in methods}}}
        elif "CREATE" in msg:
          newID = str(max([int(k) for k in self.objPool]) + 1) if self.objPool else '10000000'
          self.objPool[newID] = GeneratorStorage(self.objCls(**self.objArgs))
          ret = {"clientID": newID}
        elif "DEL" in msg:
          del self.objPool[msg['clientID']]
        elif "NEXT" in msg:
          gen = self.objPool[msg['clientID']].GetGenerator(msg['generatorID'])
          try:
            ret = {'ret': next(gen), 'finished': False}
          except StopIteration:
            ret = {'ret': None, 'finished': True}
        else:
          result = getattr(self.objPool[msg['clientID']], msg['function'])(*msg['args'], **msg['kwargs'])
          if inspect.isgenerator(result):
            generatorID = str(id(result))
            self.objPool[msg['clientID']].SaveGenerator(generatorID, result)
            ret = {'ret': {'generatorID': generatorID}}
          else:
            ret = {'ret': result}
      except Exception as e:
        e.tb = ''.join(traceback.format_tb(e.__traceback__))
        ret={'exception':f"{str(e)}\n\n{e.tb}"}
        traceback.print_tb(e.__traceback__)
        print('Exception. msg: ',str(msg),'. Except: ',str(e))
      SendMsg(socket,ret)
    return


def makeServer(objCls, objArgs, url, APIList, enableSecurity=False, keysDir=None):
  return GenesisRPCServer(objCls, objArgs, url, APIList, enableSecurity, keysDir)

def AddMethod(kls, methodName, methodMeta):
  signature = methodMeta['signature']
  is_generator = methodMeta['is_generator']
  
  newSignature = SignatureFromString(signature)

  def methodTemplate(self,*args,**kwargs):
    return self.RemoteCall(methodName,args,kwargs)
  methodTemplate.__is_generator__ = is_generator
  methodTemplate.__annotations__ = AnnotationsFromSignature(newSignature)
  methodTemplate.__signature__ = newSignature
  setattr(kls,methodName,methodTemplate)


def makeClient(url, returnClass=False, enableSecurity=False, keysDir=None, serverPublicKey=None):
  class RemoteGenerator:
      def __init__(self, client, generatorID):
          self.client = client
          self.generatorID = generatorID
          
      def __iter__(self):
          return self
          
      def __next__(self):
          ret = self.client.Send({
              'NEXT': '',
              'clientID': self.client.clientID,
              'generatorID': self.generatorID
          })
          
          if 'exception' in ret:
              raise ALightRPCException(ret['exception'])
              
          if ret['finished']:
              raise StopIteration
              
          return ret['ret']
      
  class GenesisRPCClientTemplate(object):
    def __init__(self):
      self.url = url
      self.context = context
      self.enableSecurity = enableSecurity
      
      if self.enableSecurity:
        if keysDir is None:
          keysDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certificates')
        
        clientPublicFile, clientSecretFile = zmq.auth.find_certificates(keysDir, "client")
        clientPublic, clientSecret = zmq.auth.load_certificate(clientSecretFile)
        
        self.clientPublic = clientPublic
        self.clientSecret = clientSecret
        self.serverPublic = serverPublicKey
      
      ret = self.Send({'CREATE':''})
      if "exception" in ret:
        raise ALightRPCException(ret["exception"])
      self.clientID = ret['clientID']
      return
    
    def Send(self, msg):
      with self.context.socket(zmq.REQ) as socket:
        if self.enableSecurity:
          socket.curve_secretkey = self.clientSecret
          socket.curve_publickey = self.clientPublic
          socket.curve_serverkey = self.serverPublic
        
        socket.setsockopt(zmq.CONNECT_TIMEOUT, 10000)
        socket.setsockopt(zmq.HEARTBEAT_IVL, 2000)
        socket.setsockopt(zmq.HEARTBEAT_TIMEOUT, 10000)
        socket.connect(url)
        SendMsg(socket, msg)
        return ReceiveMsg(socket)
    
    def RemoteCall(self,funcName,args,kwargs):
      ret = self.Send({'clientID': self.clientID, 'function':funcName, 'args':args, "kwargs": kwargs})
      if 'exception' in ret:
        raise ALightRPCException(ret['exception'])
      if isinstance(ret['ret'], dict) and 'generatorID' in ret['ret']:
        return RemoteGenerator(self, ret['ret']['generatorID'])
      return ret['ret']
    
    def __del__(self):
      if hasattr(self, "clientID"):
        self.Send({'DEL':'', 'clientID': self.clientID})
      return
  
  with context.socket(zmq.REQ) as socket:
    socket.setsockopt(zmq.CONNECT_TIMEOUT, 10000)
    socket.setsockopt(zmq.SNDTIMEO, 10000) 
    socket.setsockopt(zmq.RCVTIMEO, 10000)
    socket.connect(url)
    SendMsg(socket,{'GET_META':''})
    ret=ReceiveMsg(socket)
  for funcName, methodMeta in ret['META']['methods'].items():
    AddMethod(GenesisRPCClientTemplate,funcName,methodMeta)
  return validate_methods(GenesisRPCClientTemplate) if returnClass else validate_methods(GenesisRPCClientTemplate)()


#baseDir = os.path.dirname(os.path.abspath(__file__))
#serverPublicFile, serverSecretFile = GenerateCertificates(baseDir, "server")
#clientPublicFile, clientSecretFile = GenerateCertificates(baseDir, "client")