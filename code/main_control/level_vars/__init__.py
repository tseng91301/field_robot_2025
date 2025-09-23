class Level1:
    def  __init__(self):
        self.now_detected_obj = "" # 目前看到的東西
        self.finish_looking = False # 是否得到結果
        self.same_count = 0 # 看到同一物件多少次
        self.see_count = 0 # 偵測次數
        self.min_see_count = 3 # 連續看到多少次才算通過
        self.max_move_see = 5 # 邊移動邊看，但當移動中偵測次數超過這個數字還沒得到結果，就要停下來看
        self.signed_obj = {} # 紀錄看到的東西及次數
        self.light_triggered = False # 是否亮過燈
        self.look_objects = []
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
        self.stop = False # 停止移動
        self.in_range_time = 0 # 辨識到在範圍內的次數
        self.min_in_range_time = 5 # 辨識到 5 次在範圍內才能做下一個動作
        self.machine_available = False # 是否可以使用機器
        self.used_machine = False # 是否用過機器
        self.look_objects = []
        pass

    def get_obj(self, inf: list):
        """
        機器會由左往右走，因此辨識到的物體(飼料供應器)位置會從右到左(x 從大到小)。
        假設鏡頭在杯子的右邊 10 單位，辨識的機器位置就會在杯子對機器位置往左偏 10 單位
        (Ex: 鏡頭看到的 offset 是 0，已經在中間，實際上還需要再讓 offset 變為 -10 才會讓杯子在正確位置)
        self.target_pos_offset 變數是之前設定杯子和鏡頭的 x 距離(杯子在左邊為負，右邊為正)
        """
        if not self.machine_available:
            # Need Change
            # self.stop = True
            # self.in_range_time += 1
            # if self.in_range_time == self.min_in_range_time:
            #     self.machine_available = True
            # return 0

            if inf[4] not in self.look_objects: return 0
            c = [inf[0] + inf[2] / 2, inf[1] + inf[3] / 2]
            self.machine_pos_x = c[0] - self.target_pos_offset
            self.machine_pos_y = c[1]
            offset = self.frame_w / 2 - self.machine_pos_x
            # 依據目前的 offset 設定速度
            # if not self.stop:
            #     if offset <= -self.frame_w*0.8: self.move_speed = 1.0
            #     elif offset <= -self.frame_w*0.5: self.move_speed = 0.8
            #     elif offset <= -self.frame_w*0.3: self.move_speed = 0.6
            #     elif offset <= -self.frame_w*0.1: self.move_speed = 0.4
            #     else:
            #         self.move_speed = 0.0
            #         self.stop = True
            # 假設 offset 接近 0 時就停止(變成負的也是直接停止)
            # print(f"Offset: {offset}")
            if offset <= 5:
                self.stop = True
                self.in_range_time += 1
                if self.in_range_time == self.min_in_range_time:
                    self.machine_available = True
            return offset
        else:
            return 0

class Level3:
    def __init__(self):
        self.animal_pos_x = -1 # 目前偵測到動物的 x 位置
        self.animal_pos_y = -1 # 目前偵測到動物的 y 位置
        self.target_pos_offset = 0 # 偵測動物在視覺範圍中心的偏移量(左負右正)
        self.y_max_pos = 500 # 合理的高度(由上往下遞增)
        self.frame_w = -1
        self.frame_h = -1
        self.move_speed = 1.0 # 往前的速度比例，隨著距離目標愈近要減速
        self.stop = False # 停止移動
        self.in_range_time = 0 # 辨識到在範圍內的次數
        self.min_in_range_time = 5 # 辨識到 5 次在範圍內才能做下一個動作
        self.animal_available = False # 是否可以餵食
        self.fed_animal = False # 是否完成餵食
        self.look_objects = []
        pass

    def get_obj(self, inf: list):
        """
        參考 Level2 的說明
        """
        if not self.animal_available:
            if inf[4] not in self.look_objects: return 0

            c = [inf[0] + inf[2] / 2, inf[1] + inf[3] / 2]
            self.animal_pos_x = c[0] - self.target_pos_offset
            self.animal_pos_y = c[1]
            offset = self.frame_w / 2 - self.animal_pos_x
            # 依據目前的 offset 設定速度
            # if not self.stop:
            #     if offset <= -self.frame_w*0.8: self.move_speed = 1.0
            #     elif offset <= -self.frame_w*0.5: self.move_speed = 0.8
            #     elif offset <= -self.frame_w*0.3: self.move_speed = 0.6
            #     elif offset <= -self.frame_w*0.1: self.move_speed = 0.4
            #     else:
            #         self.move_speed = 0.0
            #         self.stop = True
            # 假設 offset 接近 0 時就停止(變成負的也是直接停止)
            if offset <= 5:
                self.stop = True
                self.in_range_time += 1
                if self.in_range_time == self.min_in_range_time:
                    self.animal_available = True
            return offset
        else:
            return 0
