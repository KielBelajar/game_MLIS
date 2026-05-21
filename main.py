import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration, WebRtcMode
import cvzone
import cv2
import numpy as np
import math
import random
import time
import av
from cvzone.HandTrackingModule import HandDetector

# 1. SETUP HALAMAN WEB STREAMLIT
st.set_page_config(page_title="Snake CV Web Game", layout="wide")
st.title("🐍 Snake CV Game - Web Edition")
st.write("Gunakan **2 Jari (Telunjuk & Tengah)** untuk navigasi menu, **rapatkan jari** untuk KLIK. Saat bermain, kendalikan ular dengan **Jari Telunjuk**.")

# Konfigurasi STUN Server (Wajib agar WebRTC berjalan lancar saat di-deploy ke internet)
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# 2. LOGIKA UTAMA GAME SNAKE
class SnakeGameWeb:
    def __init__(self, foodPath="Donut.png"):
        self.point = []  # Titik-titik badan ular
        self.length = []  # Jarak antar titik
        self.currentLength = 0  
        self.TotalAllowedLength = 150  
        self.headPrevious = 0, 0  

        # Inisialisasi Makanan
        self.foodIMG = cv2.imread(foodPath, cv2.IMREAD_UNCHANGED)  
        if self.foodIMG is not None:
            self.foodHeight, self.foodWidth, _ = self.foodIMG.shape
        else:
            # Cadangan jika gambar Donut.png tidak ditemukan di server
            self.foodHeight, self.foodWidth = 50, 50
            self.foodIMG = np.zeros((50, 50, 4), dtype=np.uint8)
            cv2.circle(self.foodIMG, (25, 25), 20, (0, 255, 255, 255), -1)

        self.foodLocation = 0, 0
        self.FoodLocationRandom()  
        self.score = 0
        
        # State Management
        self.gameStarted = False
        self.gameOver = False
        self.exitGame = False  # Flag jika memilih EXIT
        self.startTime = 0
        self.finalTime = 0

    def FoodLocationRandom(self):
        self.foodLocation = random.randint(100, 1100), random.randint(100, 600)

    def update(self, mainIMG, hand):
        if self.exitGame:
            overlay = mainIMG.copy()
            cv2.rectangle(overlay, (0, 0), (1280, 720), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.8, mainIMG, 0.2, 0, mainIMG)
            cvzone.putTextRect(mainIMG, "GAME BERHENTI", [380, 320], scale=4, thickness=4, colorR=(0,0,255), offset=20)
            cv2.putText(mainIMG, "Silakan segarkan (Refresh) browser untuk bermain lagi.", (270, 430), cv2.FONT_HERSHEY_COMPLEX, 0.9, (255,255,255), 2)
            return mainIMG

        headCurrent = (-1, -1)
        cursorX, cursorY = -1, -1
        cursorClick = False
        x8, y8, x12, y12 = 0, 0, 0, 0

        if hand is not None:
            landmarkList = hand['lmList']
            x8, y8 = landmarkList[8][0:2]
            x12, y12 = landmarkList[12][0:2]
            
            cursorX, cursorY = (x8 + x12) // 2, (y8 + y12) // 2
            headCurrent = (x8, y8)  
            
            fingersDistance = math.hypot(x12 - x8, y12 - y8)
            if fingersDistance < 40:
                cursorClick = True

        # ==================== MENU UTAMA ====================
        if not self.gameStarted:
            overlay = mainIMG.copy()
            cv2.rectangle(overlay, (0, 0), (1280, 720), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, mainIMG, 0.4, 0, mainIMG)

            cvzone.putTextRect(mainIMG, "SNAKE CV GAME", [360, 180], scale=5, thickness=5, colorT=(255, 255, 255), colorR=(255, 0, 0), offset=20)
            mainIMG, bboxPlay = cvzone.putTextRect(mainIMG, "PLAY", [560, 340], scale=3, thickness=3, colorT=(255, 255, 255), colorR=(0, 200, 0), offset=20)
            mainIMG, bboxExit = cvzone.putTextRect(mainIMG, "EXIT", [565, 470], scale=3, thickness=3, colorT=(255, 255, 255), colorR=(0, 0, 200), offset=20)
            cv2.putText(mainIMG, "Petunjuk: Rapatkan Jari Telunjuk & Tengah untuk KLIK", (290, 620), cv2.FONT_HERSHEY_COMPLEX, 0.9, (255, 255, 255), 2)

            if hand is not None:
                if cursorClick:
                    cv2.circle(mainIMG, (cursorX, cursorY), 15, (0, 255, 0), cv2.FILLED)  
                    if bboxPlay[0] < cursorX < bboxPlay[2] and bboxPlay[1] < cursorY < bboxPlay[3]:
                        self.gameStarted = True
                        self.startTime = time.time()
                    elif bboxExit[0] < cursorX < bboxExit[2] and bboxExit[1] < cursorY < bboxExit[3]:
                        self.exitGame = True
                else:
                    cv2.circle(mainIMG, (cursorX, cursorY), 12, (0, 0, 255), cv2.FILLED)  
                    cv2.line(mainIMG, (x8, y8), (x12, y12), (255, 255, 255), 2)
            return mainIMG

        # ==================== GAME OVER ====================
        if self.gameOver:
            overlay = mainIMG.copy()
            cv2.rectangle(overlay, (0, 0), (1280, 720), (0, 0, 255), -1)
            cv2.addWeighted(overlay, 0.3, mainIMG, 0.7, 0, mainIMG)

            cvzone.putTextRect(mainIMG, "Game Over", [400, 180], scale=7, thickness=5, colorT=(255, 255, 255), colorR=(0, 0, 255), offset=20)
            cvzone.putTextRect(mainIMG, f'Score: {self.score} | Time: {self.finalTime}s', [350, 300], scale=3, thickness=3, colorT=(255, 255, 255), colorR=(0, 0, 0), offset=15)
            
            mainIMG, bboxRestart = cvzone.putTextRect(mainIMG, "RESTART", [520, 420], scale=3, thickness=3, colorT=(255, 255, 255), colorR=(0, 200, 0), offset=20)
            mainIMG, bboxExit2 = cvzone.putTextRect(mainIMG, "EXIT", [565, 540], scale=3, thickness=3, colorT=(255, 255, 255), colorR=(0, 0, 200), offset=20)

            if hand is not None:
                if cursorClick:
                    cv2.circle(mainIMG, (cursorX, cursorY), 15, (0, 255, 0), cv2.FILLED)
                    if bboxRestart[0] < cursorX < bboxRestart[2] and bboxRestart[1] < cursorY < bboxRestart[3]:
                        self.resetGame()
                    elif bboxExit2[0] < cursorX < bboxExit2[2] and bboxExit2[1] < cursorY < bboxExit2[3]:
                        self.exitGame = True
                else:
                    cv2.circle(mainIMG, (cursorX, cursorY), 12, (0, 0, 255), cv2.FILLED)
                    cv2.line(mainIMG, (x8, y8), (x12, y12), (255, 255, 255), 2)
            return mainIMG

        # ==================== SEDANG BERMAIN ====================
        else:
            currentTime = int(time.time() - self.startTime)

            if headCurrent != (-1, -1):
                currentX, currentY = headCurrent
                if self.headPrevious == (0, 0):
                    self.headPrevious = headCurrent

                previousX, previousY = self.headPrevious
                distance = math.hypot(currentX - previousX, currentY - previousY)  
                
                if distance > 5:
                    self.point.append([currentX, currentY])
                    self.length.append(distance)
                    self.currentLength += distance
                    self.headPrevious = currentX, currentY

                while self.currentLength > self.TotalAllowedLength and self.length:
                    self.currentLength -= self.length.pop(0)
                    self.point.pop(0)

                # Cek makan makanan
                randomX, randomY = self.foodLocation
                if (randomX - self.foodWidth // 2 < currentX < randomX + self.foodWidth // 2  
                        and randomY - self.foodHeight // 2 < currentY < randomY + self.foodHeight // 2):
                    self.FoodLocationRandom()
                    self.TotalAllowedLength += 50
                    self.score += 1

                # Tabrakan Badan
                if len(self.point) > 25:
                    for p in self.point[:-18]:
                        distToBody = math.hypot(currentX - p[0], currentY - p[1])
                        if distToBody < 18:  
                            self.gameOver = True
                            self.finalTime = currentTime
                            break
            else:
                cvzone.putTextRect(mainIMG, "TANGAN TIDAK TERDETEKSI", [400, 360], scale=2, thickness=2, colorT=(0, 0, 255), colorR=(255, 255, 255), offset=10)

            # Gambar badan ular
            if self.point:
                for i, point in enumerate(self.point):
                    if i != 0:
                        cv2.line(mainIMG, self.point[i - 1], self.point[i], (0, 0, 255), 20)  
                cv2.circle(mainIMG, self.point[-1], 20, (200, 0, 200), cv2.FILLED)

            # Menampilkan Makanan
            randomX, randomY = self.foodLocation
            try:
                mainIMG = cvzone.overlayPNG(mainIMG, self.foodIMG, (randomX - self.foodWidth // 2, randomY - self.foodHeight // 2))
            except Exception:
                pass

            # UI Skor & Timer
            cvzone.putTextRect(mainIMG, f'Score: {self.score}', [50, 80], scale=3, thickness=3, offset=10, colorR=(0, 0, 0))
            cvzone.putTextRect(mainIMG, f'Time: {currentTime}s', [1020, 80], scale=3, thickness=3, offset=10, colorR=(0, 0, 0))

        return mainIMG

    def resetGame(self):
        self.point = []
        self.length = []
        self.currentLength = 0
        self.TotalAllowedLength = 150
        self.headPrevious = 0, 0
        self.score = 0
        self.gameOver = False
        self.gameStarted = True
        self.startTime = time.time()
        self.FoodLocationRandom()

# 3. KELAS PROSESOR WEBRTC STREAMLIT

# Gunakan cache agar MediaPipe hanya di-load 1 kali saja secara global, menghindari tabrakan EGL 0x3008
@st.cache_resource
def info_load_detector():
    return HandDetector(detectionCon=0.8, maxHands=1)

# Inisialisasi secara global
detector_global = info_load_detector()

class GameVideoProcessor(VideoProcessorBase):
    def __init__(self):
        # Hapus baris self.detector lama dari sini
        self.game = SnakeGameWeb("Donut.png")

    def recv(self, frame):
        # Konversi frame dari WebRTC ke format BGR OpenCV
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)  # Mode cermin

        # Deteksi Tangan menggunakan detector_global
        hands, img = detector_global.findHands(img, flipType=False)

        if hands:
            img = self.game.update(img, hands[0])
        else:
            img = self.game.update(img, None)

        return av.VideoFrame.from_ndarray(img, format="bgr24")

# 4. MEMULAI LIVE STREAMING WEBCAM DI WEBSITE
webrtc_streamer(
    key="snake-cv-game",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIGURATION,
    video_processor_factory=GameVideoProcessor,
    async_processing=True,
)