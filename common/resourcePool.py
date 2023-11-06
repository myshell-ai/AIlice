#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 17 21:27:38 2021

@author: Steven Lu
"""

import time
import threading
from collections import deque
from contextlib import contextmanager


class ResourcePool():
  def __init__(self,resources):
    self.pool=resources
    self.availables=deque(resources)
    self.lock=threading.Lock()
  
  def getAvailable(self):
    while True:
      with self.lock:
        if 0!=len(self.availables):
          return self.availables.pop()
      time.sleep(0.1)
  
  def returnResource(self,resource):
    with self.lock:
      self.availables.append(resource)
    return
  
  @contextmanager
  def get(self):
    try:
      obj=self.getAvailable()
      yield obj
    finally:
      self.returnResource(obj)