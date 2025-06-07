import pygame
import sys
import random
import math
import os
import cv2
import numpy as np

# 初始化
pygame.init()
pygame.mixer.init()
pygame.font.init()

# 中文字体
def get_chinese_font(size):
    candidates = [
    pygame.font.match_font('simhei'),
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",]

    for path in candidates:
        if path and os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)

# 屏幕设置
WIDTH, HEIGHT = 750, 750
CELL_SIZE = 30
GRID_WIDTH, GRID_HEIGHT = WIDTH // CELL_SIZE, HEIGHT // CELL_SIZE
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("耄耋大狗嚼")

clock = pygame.time.Clock()

# BGM
pygame.mixer.music.load("pics/haqi.mp3")
pygame.mixer.music.play(-1)

DARK_RED = (139, 0, 0)

# 标题
def show_title():
    screen.blit(pygame.transform.scale(pygame.image.load("pics/title.png"), (WIDTH, HEIGHT)), (0, 0))
    loading_font = get_chinese_font(14)
    loading_text = loading_font.render("正在加载资源...", True, (255, 255, 255))
    # 居中底部
    screen.blit(loading_text, (WIDTH//2 - loading_text.get_width()//2, HEIGHT - loading_text.get_height() - 20))
    pygame.display.flip()
    waiting = True
    while waiting:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif e.type == pygame.KEYDOWN:
                waiting = False

show_title()

# 加载资源
def load_scaled(path, size):
    img = pygame.image.load(path)
    return pygame.transform.scale(img, size)

head_img = load_scaled("pics/maodie.png", (CELL_SIZE, CELL_SIZE))
body_img = load_scaled("pics/maodieshen.png", (CELL_SIZE, CELL_SIZE))
shiti_img = load_scaled("pics/shiti.png", (CELL_SIZE, CELL_SIZE))
food_raw = pygame.image.load("pics/huotuichang.png")
# 卡车等比缩放
truck_raw = pygame.image.load("pics/truck.png")
truck_w, truck_h = truck_raw.get_size()
truck_scale = (CELL_SIZE * 3 / truck_w, CELL_SIZE * 3 / truck_h)
truck_img = pygame.transform.smoothscale(truck_raw, (int(truck_w * truck_scale[0]), int(truck_h * truck_scale[1])))
truck_img_mirror = pygame.transform.flip(truck_img, True, False)
# trunk2: 2x2
trunk2_raw = pygame.image.load("pics/truck2.png")
trunk2_w, trunk2_h = trunk2_raw.get_size()
trunk2_scale = (CELL_SIZE * 2 / trunk2_w, CELL_SIZE * 2 / trunk2_h)
trunk2_img = pygame.transform.smoothscale(trunk2_raw, (int(trunk2_w * trunk2_scale[0]), int(trunk2_h * trunk2_scale[1])))
trunk2_img_mirror = pygame.transform.flip(trunk2_img, True, False)
# car: 2x2
car_raw = pygame.image.load("pics/car.png")
car_img = pygame.transform.smoothscale(car_raw, (CELL_SIZE * 2, CELL_SIZE * 2))
car_img_mirror = pygame.transform.flip(car_img, True, False)
title_img = pygame.image.load("pics/title.png")
zhanbai_img = pygame.image.load("pics/zhanbai.png")
bg_img = pygame.image.load("pics/bg.png")

scale = CELL_SIZE / food_raw.get_height()
food_img = pygame.transform.smoothscale(food_raw, (int(food_raw.get_width()*scale), CELL_SIZE))

maodie = [(8, 5), (7, 5), (6, 5), (5, 5), (4, 5), (3, 5)]  # 初始长度
direction = (1, 0)
food = None
trucks = []
particles = []
dead_parts = []
recovery_texts = []

def spawn_food():
    while True:
        pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
        if pos not in maodie:
            return pos

food = spawn_food()

def spawn_truck():
    # 随机选择类型
    t = random.choice(['truck', 'trunk2', 'car'])
    if t == 'truck':
        size = 3
        img = truck_img
        img_mirror = truck_img_mirror
        msg = "和我的保险说去吧"
    elif t == 'trunk2':
        size = 2
        img = trunk2_img
        img_mirror = trunk2_img_mirror
        msg = "我以为减速带呢"
    else:
        size = 2
        img = car_img
        img_mirror = car_img_mirror
        msg = "视野盲区"
    y = random.randint(0, GRID_HEIGHT - size)
    # 方向概率调整
    if y < GRID_HEIGHT // 2:
        # 上半部分90%右->左
        dir = -1 if random.random() < 0.9 else 1
    else:
        # 下半部分90%左->右
        dir = 1 if random.random() < 0.9 else -1
    x = -size if dir == 1 else GRID_WIDTH
    return {'pos': [x, y], 'dir': dir, 'size': size, 'img': img, 'img_mirror': img_mirror, 'msg': msg, 'type': t}

def create_particles(pos, count=10):
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.5, 6)
        particles.append({'x': pos[0]*CELL_SIZE + CELL_SIZE//2,
                          'y': pos[1]*CELL_SIZE + CELL_SIZE//2,
                          'dx': math.cos(angle)*speed,
                          'dy': math.sin(angle)*speed,
                          'life': 20})

def add_recovery_text(pos):
    recovery_texts.clear()
    recovery_texts.append({'text': "能量回收", 'x': maodie[0][0]*CELL_SIZE, 'y': maodie[0][1]*CELL_SIZE, 'alpha': 255, 'font_size': 28})

# --- 预加载CG视频帧 ---
def preload_cg_frames(win, filename):
    cg_path = os.path.join(os.path.dirname(__file__), filename)
    cg_frames = []
    cg_fps = 30
    cg_total_frames = 0
    if not os.path.exists(cg_path):
        return cg_frames, cg_fps, cg_total_frames
    cap = cv2.VideoCapture(cg_path)
    cg_fps = cap.get(cv2.CAP_PROP_FPS)
    cg_total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        surf = pygame.surfarray.make_surface(np.flipud(np.rot90(frame)))
        surf = pygame.transform.scale(surf, (win.get_width(), win.get_height()))
        cg_frames.append(surf)
    cap.release()
    return cg_frames, cg_fps, cg_total_frames

cg1_frames, cg1_fps, cg1_total_frames = preload_cg_frames(screen, "cg1.mp4")
cg2_frames, cg2_fps, cg2_total_frames = preload_cg_frames(screen, "cg2.mp4")

# 加载完成后提示
def show_loaded():
    screen.blit(pygame.transform.scale(title_img, (WIDTH, HEIGHT)), (0, 0))
    loading_font = get_chinese_font(14)
    loaded_text = loading_font.render("资源加载已完成", True, (255, 255, 255))
    screen.blit(loaded_text, (WIDTH//2 - loaded_text.get_width()//2, HEIGHT - loaded_text.get_height() - 20))
    pygame.display.flip()
    pygame.time.wait(800)

show_loaded()

# --- 播放CG函数 ---
def play_cg(win, frames, fps, total_frames, zhanbai_img, show_text_func):
    fade_duration = 2.0
    fade_start_frame = total_frames - int(fps * fade_duration)
    clock = pygame.time.Clock()
    for idx, surf in enumerate(frames):
        win.blit(surf, (0, 0))
        show_text_func()
        pygame.display.flip()
        clock.tick(fps)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

# 战败界面
def show_gameover(length, death_type, death_frame_maodie=None, death_frame_particles=None):
    pygame.mixer.music.stop()
    if death_frame_maodie is not None:
        for _ in range(10):
            screen.blit(bg_img, (0, 0))
            for i, segment in enumerate(death_frame_maodie):
                # 死亡时蛇头用 shiti_img
                img = shiti_img if i == 0 else body_img
                screen.blit(img, (segment[0]*CELL_SIZE, segment[1]*CELL_SIZE))
            if death_frame_particles:
                for p in death_frame_particles:
                    alpha = max(0, min(255, int(255 * (p['life'] / 20))))
                    blood_surface = pygame.Surface((4, 4), pygame.SRCALPHA)
                    pygame.draw.circle(blood_surface, (*DARK_RED, alpha), (2, 2), 2)
                    screen.blit(blood_surface, (int(p['x'])-2, int(p['y'])-2))
            pygame.display.flip()
            pygame.time.wait(20)

        # 黑屏渐变
        fade_surface = pygame.Surface((WIDTH, HEIGHT))
        fade_surface.fill((0, 0, 0))
        for alpha in range(0, 256, 16):
            screen.blit(bg_img, (0, 0))
            for i, segment in enumerate(death_frame_maodie):
                img = shiti_img if i == 0 else body_img
                screen.blit(img, (segment[0]*CELL_SIZE, segment[1]*CELL_SIZE))
            if death_frame_particles:
                for p in death_frame_particles:
                    a = max(0, min(255, int(255 * (p['life'] / 20))))
                    blood_surface = pygame.Surface((4, 4), pygame.SRCALPHA)
                    pygame.draw.circle(blood_surface, (*DARK_RED, a), (2, 2), 2)
                    screen.blit(blood_surface, (int(p['x'])-2, int(p['y'])-2))
            fade_surface.set_alpha(alpha)
            screen.blit(fade_surface, (0, 0))
            pygame.display.flip()
            pygame.time.wait(20)

    def draw_text():
        font = get_chinese_font(36)
        font.set_bold(True)
        text = font.render(f"第{length}集 [ 剧终 ]", True, DARK_RED)
        screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 + 100))
        tip_font = get_chinese_font(28)
        tip_font.set_bold(True)
        tip = tip_font.render("扣1复活耄耋", True, (255, 255, 255))
        screen.blit(tip, (WIDTH//2 - tip.get_width()//2, HEIGHT//2 + 160))
    if death_type == "self" and cg1_frames:
        play_cg(screen, cg1_frames, cg1_fps, cg1_total_frames, zhanbai_img, draw_text)
    elif death_type == "truck" and cg2_frames:
        play_cg(screen, cg2_frames, cg2_fps, cg2_total_frames, zhanbai_img, draw_text)
    else:
        draw_text()
        pygame.display.flip()
        pygame.time.wait(1500)
    waiting = True
    restart = False
    while waiting:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    restart = True
                    waiting = False
    return restart

def reset_game():
    global maodie, direction, food, trucks, particles, dead_parts, recovery_texts, tick
    maodie = [(8, 5), (7, 5), (6, 5), (5, 5), (4, 5), (3, 5)]  # 初始长度6节
    direction = (1, 0)
    food = spawn_food()
    trucks = []
    particles = []
    dead_parts = []
    recovery_texts = []
    tick = 0

# 展示开始
# 删除/注释掉下面这行（避免再次进入加载界面）
# show_title()

# 主循环（支持复活）
first_run = True
while True:
    # 死亡/重开后重新播放BGM，但第一次进入游戏不重播
    if not first_run:
        pygame.mixer.music.load("pics/haqi.mp3")
        pygame.mixer.music.play(-1)
    else:
        first_run = False
    reset_game()
    running = True
    death_type = None  # 辅助记录死亡类型
    death_frame_maodie = None  # 死亡帧蛇身
    death_frame_particles = None  # 死亡帧粒子
    while running:
        clock.tick(10)
        tick += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_w and direction != (0, 1):
                    direction = (0, -1)
                elif event.key == pygame.K_s and direction != (0, -1):
                    direction = (0, 1)
                elif event.key == pygame.K_a and direction != (1, 0):
                    direction = (-1, 0)
                elif event.key == pygame.K_d and direction != (-1, 0):
                    direction = (1, 0)

        # 移动蛇
        new_head = (maodie[0][0]+direction[0], maodie[0][1]+direction[1])

        # 边缘穿越
        new_head = (new_head[0] % GRID_WIDTH, new_head[1] % GRID_HEIGHT)

        # 撞到自己
        if new_head in maodie[1:]:
            # 死亡音效立即播放
            if "self" == "self":
                try:
                    death_sound = pygame.mixer.Sound("dead1.MP3")
                    death_sound.play()
                except Exception:
                    pass
            create_particles(new_head, count=120)  # 极多血液
            death_type = "self"
            # 记录死亡帧
            death_frame_maodie = list(maodie)
            death_frame_particles = [dict(p) for p in particles]
            running = False
            # 不再break，继续进入后续粒子绘制流程
            continue

        # 吃身体碎片
        eaten = False
        for part in dead_parts:
            if part['pos'] == new_head:
                add_recovery_text(new_head)
                dead_parts.remove(part)
                eaten = True
                # 播放变长音效
                try:
                    long_sound = pygame.mixer.Sound("long.mp3")
                    long_sound.play()
                except Exception:
                    pass
                break

        if not eaten:
            maodie.pop()

        maodie.insert(0, new_head)

        # 吃食物
        if new_head == food:
            maodie.append(maodie[-1])
            food = spawn_food()
            # 播放变长音效
            try:
                long_sound = pygame.mixer.Sound("long.mp3")
                long_sound.play()
            except Exception:
                pass

        # 生成卡车
        if tick % 30 == 0:
            trucks.append(spawn_truck())

        # 移动卡车
        for truck in trucks:
            truck['pos'][0] += truck['dir']

        # 移除越界卡车
        trucks = [
            t for t in trucks
            if not (t['dir'] == 1 and t['pos'][0] > GRID_WIDTH) and not (t['dir'] == -1 and t['pos'][0] < -t['size'])
        ]

        # 检查卡车撞蛇
        if 'truck_hit_state' not in locals():
            truck_hit_state = {'active': False, 'timer': 0, 'truck_id': None, 'msg': ""}
        for idx, truck in enumerate(trucks):
            truck_cells = [
                (truck['pos'][0] + dx, truck['pos'][1] + dy)
                for dx in range(truck['size']) for dy in range(truck['size'])
            ]
            # 撞到蛇头
            if maodie[0] in truck_cells:
                # 恢复此处死亡音效播放
                if "truck" == "truck":
                    try:
                        death_sound = pygame.mixer.Sound("dead2.MP3")
                        death_sound.play()
                    except Exception:
                        pass
                create_particles(maodie[0], count=120)  # 极多血液
                death_type = "truck"
                # 记录死亡帧
                death_frame_maodie = list(maodie)
                death_frame_particles = [dict(p) for p in particles]
                running = False
                # 不再break，继续进入后续粒子绘制流程
                continue
            # 撞到身体
            hit_body = [i for i, seg in enumerate(maodie[1:], 1) if seg in truck_cells]
            if hit_body:
                # 播放heat. MP3
                try:
                    heat_sound = pygame.mixer.Sound("heat.MP3")
                    heat_sound.play()
                except Exception:
                    pass
                min_idx = min(hit_body)
                for part in maodie[min_idx:]:
                    dead_parts.append({'pos': part, 'alpha': 255, 'time': 0, 'decay': 2})
                create_particles(maodie[min_idx])
                maodie = maodie[:min_idx]
                truck_hit_state = {
                    'active': True,
                    'timer': 30,
                    'truck_id': id(truck),
                    'msg': truck['msg']
                }
                # 被车撞身体不死亡，不设置death_type，不break
                # break  # <-- 移除此行

        # 更新粒子
        for p in particles:
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['life'] -= 1
        particles = [p for p in particles if p['life'] > 0]

        # 更新碎尸透明度
        for part in dead_parts:
            # 使用decay参数控制衰减速度，默认5，增加后更慢
            decay = part.get('decay', 5)
            part['time'] += 1
            part['alpha'] = max(0, 255 - part['time'] * decay)
        dead_parts = [p for p in dead_parts if p['alpha'] > 0]

        # 更新能量文字
        for t in recovery_texts:
            t['y'] -= 1
            t['alpha'] -= 5
        recovery_texts = [t for t in recovery_texts if t['alpha'] > 0]

        # 绘图
        # screen.fill(SKY_BLUE)  # 天蓝色背景
        screen.blit(bg_img, (0, 0))  # 使用背景图

        # 食物
        screen.blit(food_img, (food[0]*CELL_SIZE, food[1]*CELL_SIZE))

        # 卡车
        for t in trucks:
            img = t['img_mirror'] if t['dir'] == 1 else t['img']
            screen.blit(img, (t['pos'][0]*CELL_SIZE, t['pos'][1]*CELL_SIZE))
            # 如果需要显示撞击提示，且卡车id匹配，且计时未到
            if (
                'truck_hit_state' in locals()
                and truck_hit_state.get('active')
                and truck_hit_state.get('timer', 0) > 0
                and truck_hit_state.get('truck_id') == id(t)
            ):
                alpha = int(255 * (truck_hit_state['timer'] / 30))
                font = get_chinese_font(22)
                # 卡车撞击提示颜色由黄色改为白色
                text_surface = font.render(truck_hit_state.get('msg', ""), True, (255, 255, 255))
                text_surface.set_alpha(alpha)
                tx = t['pos'][0]*CELL_SIZE + (CELL_SIZE*t['size'] - text_surface.get_width())//2
                ty = t['pos'][1]*CELL_SIZE - text_surface.get_height() - 2
                screen.blit(text_surface, (tx, ty))

        # 死亡身体
        prev = None
        for idx, part in enumerate(dead_parts):
            # 判断是否为断开的第一节
            is_first = (idx == 0) or (prev is None) or (
                abs(part['pos'][0] - prev['pos'][0]) + abs(part['pos'][1] - prev['pos'][1]) > 1
            )
            img = shiti_img.copy() if is_first else body_img.copy()
            img.set_alpha(part['alpha'])
            screen.blit(img, (part['pos'][0]*CELL_SIZE, part['pos'][1]*CELL_SIZE))
            prev = part

        # 蛇
        for i, segment in enumerate(maodie):
            img = head_img if i == 0 else body_img
            screen.blit(img, (segment[0]*CELL_SIZE, segment[1]*CELL_SIZE))

        # 粒子特效（血液渐变消失）
        for p in particles:
            # alpha 随 life 变化，最大255，最小0
            alpha = max(0, min(255, int(255 * (p['life'] / 20))))
            blood_surface = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(blood_surface, (*DARK_RED, alpha), (2, 2), 2)
            screen.blit(blood_surface, (int(p['x'])-2, int(p['y'])-2))

        # 回收提示
        for t in recovery_texts:
            font = get_chinese_font(t.get('font_size', 16))  # 支持不同字号
            # 能量回收提示颜色改为黄色
            s = font.render(t['text'], True, (255, 255, 0))
            s.set_alpha(t['alpha'])
            screen.blit(s, (t['x'], t['y']))

        # 在每帧末尾减少提示计时器
        if 'truck_hit_state' in locals() and truck_hit_state.get('active'):
            if truck_hit_state['timer'] > 0:
                truck_hit_state['timer'] -= 1
            if truck_hit_state['timer'] <= 0:
                truck_hit_state['active'] = False

        pygame.display.flip()

    # 死亡后血液粒子动画
    if death_type in ("self", "truck") and particles:
        # 记录死亡帧蛇身用于静止显示
        death_maodie = death_frame_maodie if death_frame_maodie else []
        while particles:
            clock.tick(30)
            # 更新粒子
            for p in particles:
                p['x'] += p['dx']
                p['y'] += p['dy']
                p['life'] -= 1
            particles = [p for p in particles if p['life'] > 0]
            # 绘制死亡帧
            screen.blit(bg_img, (0, 0))
            for i, segment in enumerate(death_maodie):
                img = shiti_img if i == 0 else body_img
                screen.blit(img, (segment[0]*CELL_SIZE, segment[1]*CELL_SIZE))
            for p in particles:
                alpha = max(0, min(255, int(255 * (p['life'] / 20))))
                blood_surface = pygame.Surface((4, 4), pygame.SRCALPHA)
                pygame.draw.circle(blood_surface, (*DARK_RED, alpha), (2, 2), 2)
                screen.blit(blood_surface, (int(p['x'])-2, int(p['y'])-2))
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

    # 结束界面，若返回True则复活，否则退出
    if not show_gameover(len(maodie), death_type, death_frame_maodie, death_frame_particles):
        break

pygame.quit()
