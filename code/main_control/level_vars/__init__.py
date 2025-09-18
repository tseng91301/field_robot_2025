class Level1:
    def  __init__(self):
        self.now_detected_obj = "" # 目前看到的東西
        self.finish_looking = False # 是否得到結果
        self.same_count = 0 # 看到同一物件多少次
        self.see_count = 0 # 偵測次數
        self.min_see_count = 10 # 連續看到多少次才算通過
        self.max_move_see = 30 # 邊移動邊看，但當移動中偵測次數超過這個數字還沒得到結果，就要停下來看
        self.signed_obj = {} # 紀錄看到的東西及次數
        self.light_triggered = False # 是否亮過燈
        pass

    def look_obj(self, obj: str):
        if not self.finish_looking:
            if self.now_detected_obj == obj:
                self.same_count += 1
                self.signed_obj[obj] = self.signed_obj.get(obj, 0) + 1
                if self.same_count >= self.min_see_count:
                    self.finish_looking = True
            else:
                self.now_detected_obj = obj
                self.same_count = 1
            self.see_count += 1
            if self.see_count >= self.max_move_see and self.finish_looking == False:
                # 超過移動觀看次數，立即用目前偵測到最多次的物件來當作結果
                if len(self.signed_obj) > 0:
                    self.now_detected_obj = max(self.signed_obj, key=self.signed_obj.get)
                self.finish_looking = True
            # if self.finish_looking == True:
            #     print(f"Saw Object: {self.now_detected_obj}")
    
    def manual_finish(self):
        # 手動結束關卡
        if not self.finish_looking:
            if len(self.signed_obj) > 0:
                self.now_detected_obj = max(self.signed_obj, key=self.signed_obj.get)
            self.finish_looking = True
        return self.now_detected_obj
    
class Level2:
    def __init__(self):
        self.machine_pos_x = -1 # 目前偵測到機器的 x 位置
        self.machine_pos_y = -1 # 目前偵測到機器的 y 位置
        self.target_pos_offset = 0 # 偵測機器在視覺範圍中心的偏移量(左負右正)
        self.y_max_pos = 500 # 合理的機器高度(由上往下遞增)
        self.frame_w = -1
        self.frame_h = -1
        self.move_speed = 1.0 # 往前的速度比例，隨著距離目標愈近要減速
        self.stop = False
        pass

    def get_obj(self, inf: list):
        c = [inf[0] + inf[2] / 2, inf[1] + inf[3] / 2]
        self.machine_pos_x = c[0] - self.target_pos_offset
        self.machine_pos_y = c[1]
        offset = self.frame_w / 2 - self.machine_pos_x
        # 依據目前的 offset 設定速度
        if not self.stop:
            if offset <= -self.frame_w*0.8: self.move_speed = 1.0
            elif offset <= -self.frame_w*0.5: self.move_speed = 0.8
            elif offset <= -self.frame_w*0.3: self.move_speed = 0.6
            elif offset <= -self.frame_w*0.1: self.move_speed = 0.4
            else: 
                self.move_speed = 0.0
                self.stop = True
