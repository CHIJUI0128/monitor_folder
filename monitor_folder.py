import os, threading, time, re, shutil, logging,warnings
from watchdog.observers import Observer
from watchdog.events import *
from watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff
import numpy as np
import pandas as pd
import ctypes
import matplotlib
from measurement_check import *


matplotlib.use('Agg')
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
warnings.filterwarnings("ignore")
FORMAT = '%(asctime)s %(levelname)s: %(message)s'
logging.basicConfig(level=logging.DEBUG, filename='./myLog.log', filemode='a', format=FORMAT)

def check_shift(path):
   meas_data = pd.read_csv(path, encoding='big5')  
   meas_data.columns = range(len(meas_data.columns))
   org_pt = []
   sec_pt = []
   
   
   #檢驗板子是否偏移
   for  row, item in enumerate(meas_data[0]):
       if "offset_correction_" in  item:
           tmp = meas_data[meas_data[0]==item]
           org_x = tmp[tmp[2] == "座標X"][6].iloc[0]
           org_y = tmp[tmp[2] == "座標Y"][6].iloc[0]
           id_ = item.split("offset_correction_")[1]
           if id_ not in  [x[0] for x in org_pt]:
               org_pt.append( [ id_, [org_x, org_y] ])
           
           
       if "target_hole_" in item:    
           tmp = meas_data[meas_data[0]==item]
           sec_x = tmp[tmp[2] == "座標X"][6].iloc[0]
           sec_y = tmp[tmp[2] == "座標Y"][6].iloc[0]
           id_t = item.split("target_hole_")[1]
           if id_t not in  [x[0] for x in sec_pt]:
               sec_pt.append([id_t, [sec_x, sec_y]])
       #bd_558diameter_5-標準值  bd_49diameter_10_量測值
   
   shift = []
   if org_pt and sec_pt:
       for org_ in org_pt:
           for sec_ in sec_pt:
               if org_[0] == sec_[0]:
                   shift.append( distance(org_[1], sec_[1]))  
            
   return(shift)  

def distance(pt1, pt2):
   return ((pt1[0] -pt2[0]) **2 + (pt1[1] -pt2[1]) **2) **0.5

def check_diameter(path):
   dia_check=[]
   meas_data_dia = pd.read_csv(path, encoding='big5')  
   meas_data_dia.columns = range(len(meas_data_dia.columns))
   filt = (meas_data_dia[0].str.contains('target_hole_')) & (meas_data_dia[2]=="直徑D")
   
   meas_data_dia = meas_data_dia.loc[filt]
   dia_check = meas_data_dia[6].values
   #print(dia_check)
   error_num = sum(i > 3.165 for i in dia_check)
   #print(error_num)
            
   return(error_num)  

def check_shift_and_dia(fileAllName):
    chk_shift_BOT = check_shift(fileAllName)
    #檢查靶孔孔徑
    chk_dia_BOT = check_diameter(fileAllName)
    
    #偏移超過 0.003 停止程式
    if max(chk_shift_BOT)> 0.003:
    
        ctypes.windll.user32.MessageBoxW(0, "!! Error !!\n板子 於量測過程發生偏移\nヾ(;ﾟ;Д;ﾟ;)ﾉﾞ",
                                                "  !! Error !!  ", 0, 0x40000)
        print('======================== 靶孔位置 檢查中 ========================')
        logging.info('量測過程發生偏移')
        return
    #靶孔孔徑過大  
    if chk_dia_BOT!=0:
        ctypes.windll.user32.MessageBoxW(0, "!! Error !!\n靶孔孔徑 過大(>3.165mm，請告知鑽孔人員)\nヾ(;ﾟ;Д;ﾟ;)ﾉﾞ",
                                                "  !! Error !!  ", 0, 0x40000)
        print('======================== 靶孔位置 檢查中 ========================')
        logging.info('靶孔孔徑過大')  
        return
    
def remove_C_folder_to_S_folder(filelist):
    source_path = os.path.join(*['C:\\'] + filelist[1:5])
    target_path = 'S:/製造/鑽孔Nikon-3D'
    # 建立目標路徑
    os.makedirs(target_path, exist_ok=True)

    new_filelist = [target_path] + filelist[3:5]

    # 產生完整的檔案路徑
    file_path = os.path.join(*new_filelist)

    try:
        shutil.copytree(source_path, file_path)

    except FileExistsError:

        current_time = time.strftime("_%m%d_%H%M_%S", time.localtime())
        file_path += f"{current_time}"
        shutil.copytree(source_path, file_path)
    print(source_path, file_path)
    logging.info('remove_C_folder_to_S_folder done') 
    print('======================== 靶孔位置 檢查中 ========================')
        
class FileEventHandler(FileSystemEventHandler):
    def __init__(self, aim_path):
        FileSystemEventHandler.__init__(self)
        self.aim_path = aim_path
        self.timer = None
        self.snapshot = DirectorySnapshot(self.aim_path)
           
    def on_any_event(self, event):
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(0.5, self.checkSnapshot)
        self.timer.start()
    
    def checkSnapshot(self):
        snapshot = DirectorySnapshot(self.aim_path)
        diff = DirectorySnapshotDiff(self.snapshot, snapshot)
        self.snapshot = snapshot
        self.timer = None

        for fileAllName in diff.files_created:
            
            fileAllName = fileAllName.replace('\\', '/')
            if fileAllName.endswith('BOT_measurement.csv') :
                print('BOT_measurement csv showwwwwww!!!!!!!!!!')
                logging.info('BOT_measurement csv showwwwwww!!!!!!!!!!') 
                # print(fileAllName)
    
                check_shift_and_dia(fileAllName) 

                filelist = fileAllName.split('/')
                remove_C_folder_to_S_folder(filelist)
                    
            elif fileAllName.endswith('TOP_measurement.csv') :
                print('TOP_measurement csv showwwwwww!!!!!!!!!!')
                logging.info('TOP_measurement csv showwwwwww!!!!!!!!!!') 
                # print(fileAllName)

                check_shift_and_dia(fileAllName) 

                filelist = fileAllName.split('/')
                remove_C_folder_to_S_folder(filelist)
                    
class DirMonitor(object):
    """文件夹监视类"""
    
    def __init__(self, aim_path):
        """构造函数"""
        self.aim_path= aim_path
        self.observer = Observer()
    
    def start(self):
        """启动"""
        event_handler = FileEventHandler(self.aim_path)
        self.observer.schedule(event_handler, self.aim_path, True)
        self.observer.start()
    
    def stop(self):
        """停止"""
        self.observer.stop()
    
if __name__ == "__main__": 
    event = threading.Event()   # 註冊事件
    monitor1 = DirMonitor(r"C:/NEXIV3/Data/TOP_measurement") 
    monitor2 = DirMonitor(r"C:/NEXIV3/Data/BOT_measurement") 
    monitor1.start() 
    monitor2.start()

            
    logging.info('====================== 靶孔位置 start ======================') 
    print('======================== 靶孔位置 start ========================')
    try: 
        while True: 
            time.sleep(1) 
    except KeyboardInterrupt: 
        logging.info('====================== 靶孔位置 end ======================') 
        monitor1.stop() 
        monitor2.stop() 





