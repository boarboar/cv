import wx
import wx.lib.newevent
import cv2
import urllib.request
from urllib.error import URLError
import numpy as np
import threading
import time

# py -m pip install -U wxPython
# py -m pip install -U opencv-python
#

#RedrawEvent, EVT_RDR_EVENT = wx.lib.newevent.NewEvent()

class StreamClientThread(threading.Thread):
    def __init__(self, idx, wnd, url, proxysetting):
        threading.Thread.__init__(self)
        self.__lock=threading.Lock()
        self.wnd=wnd
        self.__url = url
        self.__proxysetting=proxysetting
        self.__stop = False
        self.__idx = idx
        self.stream=None
        self.bytes=b''
        self.setDaemon(1)

    def stop(self) : self.__stop=True
    def lock(self) : self.__lock.acquire()
    def unlock(self) : self.__lock.release()

    def loadimg(self):
        if self.stream is None : return None
        while True:
            try:
                step = "read" 
                self.bytes += self.stream.read(1024)
                step = "find bord" 
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

            self.frame = self.loadimg()

            if self.frame is not None:
                self.height, self.width = self.frame.shape[:2]
                self.bmp = wx.BitmapFromBuffer(self.width, self.height, self.frame)

            else:
                print("Error no webcam image")
                continue

            while not self.__stop and self.frame is not None:
                cv2.putText(self.frame, "L" if self.__idx == 0 else "R", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (23, 230, 210), 1)
                self.bmp.CopyFromBuffer(self.frame)
                #self.wnd.SetBitmap(self.bmp)
                #UGLY
                Size  = self.wnd.ClientSize
                image=wx.ImageFromBitmap(self.bmp)
                image = image.Scale(Size[0], Size[1], wx.IMAGE_QUALITY_HIGH)
                bmp = wx.BitmapFromImage(image)
                self.wnd.SetBitmap(bmp)
                
                self.frame = self.loadimg()

class viewWindow(wx.Frame):
    def __init__(self, parent, title="View Window"):
            # super(viewWindow,self).__init__(parent)
            wx.Frame.__init__(self, parent)

            self.imgSizer = (320, 240)
            self.pnl = wx.Panel(self)
            self.vbox = wx.BoxSizer(wx.HORIZONTAL)

            self.image = wx.Image(self.imgSizer[0],self.imgSizer[1])
            
            self.imageBit0 = wx.Bitmap(self.image)
            self.staticBit0 = wx.StaticBitmap(self.pnl, wx.ID_ANY, self.imageBit0)

            self.imageBit1 = wx.Bitmap(self.image)
            self.staticBit1 = wx.StaticBitmap(self.pnl, wx.ID_ANY, self.imageBit1)

            self.vbox.Add(self.staticBit0, 1, flag=wx.EXPAND)
            self.vbox.Add(self.staticBit1, 1, flag=wx.EXPAND)
            #self.staticBit0.ScaleMode(wx.StaticBitmap.Scale_AspectFit)
            #self.staticBit1.ScaleMode(wx.StaticBitmap.Scale_AspectFit)

            self.SetBackgroundColour('black')
            self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
            #self.pnl.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
            #self.staticBit0.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
            #self.staticBit1.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
            # wx.EVT_SIZE or wx.EVT_SIZING

            #self.SetSize(self.imgSizer)
            self.pnl.SetSizer(self.vbox)
            self.vbox.Fit(self)
            self.Show()
                        #self.streamthread =StreamClientThread(self,
            #                                      "http://88.53.197.250/axis-cgi/mjpg/video.cgi?resolution=320x240",
            #                                      {'http': 'proxy.reksoft.ru:3128'})

            self.streamthread0 = StreamClientThread(0, self.staticBit0, "http://192.168.1.134", None)
            self.streamthread0.start()
            self.streamthread1 = StreamClientThread(1, self.staticBit1, "http://192.168.1.135", None)
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