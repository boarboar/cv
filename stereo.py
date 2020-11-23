import wx
import wx.lib.newevent
import cv2
import urllib.request
from urllib.error import URLError
import numpy as np
import threading
import time
import ssl

# py -m pip install -U wxPython
# py -m pip install -U opencv-python
#

#RedrawEvent, EVT_RDR_EVENT = wx.lib.newevent.NewEvent()

class StreamClientThread(threading.Thread):
    def __init__(self, idx, wnd, url, proxysetting):
        threading.Thread.__init__(self)
        #self.__lock = threading.Lock()
        self.wnd=wnd
        self.__url = url
        self.__proxysetting=proxysetting
        self.__stop = False
        self.__idx = idx
        self.stream=None
        self.bytes=b''
        self.setDaemon(1)

    def stop(self) : self.__stop=True
    #def lock(self) : self.__lock.acquire()
    #def unlock(self) : self.__lock.release()

    def loadimg(self):
        if self.stream is None : return None
        while True:
            try:
                step = "read" 
                self.bytes += self.stream.read(1024)
                step = "find boundary" 
                a = self.bytes.find(b'\xff\xd8')
                b = self.bytes.find(b'\xff\xd9')
                if a!=-1 and b!=-1:
                    jpg = self.bytes[a:b+2]
                    self.bytes = self.bytes[b+2:]       
                    step = "convert"     
                    img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8),cv2.IMREAD_COLOR)
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB, img)
                    print("read frame")
                    return img
                    
            except Exception as e:
                print('failed at:', step, ' with ', e)
                return None
                
    def run (self):
        if self.__proxysetting is not None :
            proxy = urllib.request.ProxyHandler(self.__proxysetting)
            opener = urllib.request.build_opener(proxy)
            urllib.request.install_opener(opener)

        # workaround for unverified certs
        try:
           _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            # Legacy Python that doesn't verify HTTPS certificates by default
            pass
        else:
            # Handle target environment that doesn't support HTTPS verification
            ssl._create_default_https_context = _create_unverified_https_context

        while not self.__stop:
            time.sleep(1.0)
            print('opening stream...')
            self.stream=None
            try:
                self.stream=urllib.request.urlopen(self.__url, timeout=10.0)
                print('stream opened')
            except URLError as e:
                print(e.reason)
                continue

            while not self.__stop: 
                self.frame = self.loadimg()
                if self.frame is None:
                    break                
                self.wnd.Update(self.frame,  "L" if self.__idx == 0 else "R")
                
                
class jpegWnd(wx.StaticBitmap) :
    def __init__(self, parent, imgSizer):
        # self.bmp = wx.Bitmap(wx.Image(imgSizer[0], imgSizer[1]))        
        wx.StaticBitmap.__init__(self, parent, wx.ID_ANY, wx.Bitmap(wx.Image(imgSizer[0], imgSizer[1])))
        self.SetMinSize(imgSizer)
        self.ScaleMode(wx.StaticBitmap.Scale_AspectFit)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.SetBackgroundColour('black')
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.chgSize = True
        
    def Update(self, frame, label):
        if self.chgSize :
            self.chgSize = False            
            size  = self.ClientSize
            if size[0] >= 320 and size[1] >= 240 :
                print("recreate bmp")
                self.bmp = wx.Bitmap(wx.Image(size[0], size[1]))

        img = cv2.resize(frame, (self.bmp.GetWidth(), self.bmp.GetHeight()), cv2.INTER_AREA)
        cv2.putText(img, label, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (23, 230, 210), 1)
        self.bmp.CopyFromBuffer(img)       
        self.SetBitmap(self.bmp)
        
        pass
            
    def OnEraseBackground(self, event):
        pass
    def OnSize(self, event):
        print("OnSize")
        self.chgSize = True

    
class viewWindow(wx.Frame):
    def __init__(self, parent, title="View Window"):
            # super(viewWindow,self).__init__(parent)
            wx.Frame.__init__(self, parent)

            #self.imgSizer = (320, 240)
            self.pnl = wx.Panel(self)
            self.vbox = wx.BoxSizer(wx.HORIZONTAL)
 
            self.staticBit0 = jpegWnd(self.pnl, (320, 240))
            self.staticBit1 = jpegWnd(self.pnl, (320, 240))
            
            self.vbox.Add(self.staticBit0, 1, flag=wx.EXPAND)
            self.vbox.Add(self.staticBit1, 1, flag=wx.EXPAND)


            self.SetBackgroundColour('black')
            self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
            self.pnl.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
 
            self.pnl.SetSizer(self.vbox)
            self.vbox.Fit(self)
            self.Show()
            
            #self.streamthread0 = StreamClientThread(0, self.staticBit0, "http://192.168.1.134", None)
            #self.streamthread1 = StreamClientThread(1, self.staticBit1, "http://192.168.1.135", None)


            self.streamthread0 =StreamClientThread(0, self.staticBit0, 
                                                  "https://webcam1.lpl.org/axis-cgi/mjpg/video.cgi",
                                                  {'https': 'proxy.reksoft.ru:3128'} )
            self.streamthread1 =StreamClientThread(1, self.staticBit1, 
                                                  "https://webcam1.lpl.org/axis-cgi/mjpg/video.cgi",
                                                  {'https': 'proxy.reksoft.ru:3128'} )
            self.streamthread0.start()            
            self.streamthread1.start()
            
    def OnEraseBackground(self, event):
        pass
    
def main():
    app = wx.App()
    frame = viewWindow(None)
    frame.Center()
    frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()
