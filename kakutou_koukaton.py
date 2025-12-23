import pygame as pg
import sys
import os

# 初期設定
WIDTH, HEIGHT = 1000, 600
FLOOR = HEIGHT - 50

TITLE = 0
SELECT = 1
BATTLE = 2

# Windows標準日本語フォント
FONT_PATH = "C:/Windows/Fonts/msgothic.ttc"

os.chdir(os.path.dirname(os.path.abspath(__file__)))

pg.init()
screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("こうかとん ファイター")
clock = pg.time.Clock()

# =====================
# 画像読み込み
# =====================
TITLE_BG = pg.transform.scale(
    pg.image.load("ダウンロード (1).jpg").convert(),
    (WIDTH, HEIGHT)
)
# =====================
# ステージ定義
# =====================
STAGES = [
    {
        "name": "境内",
        "bg": pg.transform.scale(
            pg.image.load("Tryfog.jpg").convert(),
            (WIDTH, HEIGHT)
        )
    },
    {
        "name": "稽古場",
        "bg": pg.transform.scale(
            pg.image.load("ダウンロード.jpg").convert(),
            (WIDTH, HEIGHT)
        )
    },
    {
        "name": "繁華街（夜）",
        "bg": pg.transform.scale(
            pg.image.load("3Dオリジナル背景作品 格闘ゲーム用背景.jpg").convert(),
            (WIDTH, HEIGHT)
        )
    }
]



# =====================
# ファイタークラス
# =====================
class Fighter(pg.sprite.Sprite):
    def __init__(self, x, color, keys):
        super().__init__()
        self.image = pg.Surface((60, 120))
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (x, FLOOR)

        self.vx = 0
        self.vy = 0
        self.on_ground = True
        self.hp = 100
        self.keys = keys
        self.facing = 1  # 1:右向き -1:左向き

    def update(self, key_lst):
        self.vx = 0

        if key_lst[self.keys["left"]]:
            self.vx = -6
            self.facing = -1
        if key_lst[self.keys["right"]]:
            self.vx = 6
            self.facing = 1

        # ジャンプ
        if key_lst[self.keys["jump"]] and self.on_ground:
            self.vy = -20
            self.on_ground = False

        # 重力
        self.vy += 1

        self.rect.x += self.vx
        self.rect.y += self.vy

        # 着地判定
        if self.rect.bottom >= FLOOR:
            self.rect.bottom = FLOOR
            self.vy = 0
            self.on_ground = True

# =====================
# 攻撃判定（HitBox）
# =====================
class Attack(pg.sprite.Sprite):
    def __init__(self, fighter):
        super().__init__()
        self.image = pg.Surface((40, 20))
        self.image.fill((255, 0, 0))
        self.rect = self.image.get_rect()

        if fighter.facing == 1:
            self.rect.midleft = fighter.rect.midright
        else:
            self.rect.midright = fighter.rect.midleft

        self.life = 10  # 10フレームだけ存在

    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()

# =====================
# タイトル画面
# =====================
def draw_title():
    screen.blit(TITLE_BG, (0, 0))

    overlay = pg.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(120)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    font = pg.font.Font(FONT_PATH, 80)
    small = pg.font.Font(FONT_PATH, 36)

    title = font.render("こうかとん ファイター", True, (255, 255, 255))
    guide = small.render("ENTERキーでスタート", True, (230, 230, 230))

    screen.blit(title, (WIDTH//2 - title.get_width()//2, 220))
    screen.blit(guide, (WIDTH//2 - guide.get_width()//2, 330))

# =====================
# バトル選択画面
# =====================
def draw_select(selected):
    screen.blit(STAGES[selected]["bg"], (0, 0))

    overlay = pg.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(150)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    font = pg.font.Font(FONT_PATH, 60)
    small = pg.font.Font(FONT_PATH, 30)

    title = font.render("バトルステージ選択", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 60))

    for i, stage in enumerate(STAGES):
        color = (255, 255, 0) if i == selected else (200, 200, 200)
        label = small.render(stage["name"], True, color)

        rect = pg.Rect(350, 180 + i * 80, 300, 50)
        pg.draw.rect(screen, color, rect, 2)
        screen.blit(
            label,
            (rect.centerx - label.get_width()//2,
             rect.centery - label.get_height()//2)
        )

    guide = small.render("↑↓で選択　ENTERで決定", True, (220, 220, 220))
    screen.blit(guide, (WIDTH//2 - guide.get_width()//2, 500))



# =====================
# メイン
# =====================
def main():
    game_state = TITLE
    selected_stage = 0
    current_stage = 0
    attacks = pg.sprite.Group()

    p1 = Fighter(200, (0, 0, 255), {
        "left": pg.K_a,
        "right": pg.K_d,
        "jump": pg.K_w,
        "attack": pg.K_f
    })

    p2 = Fighter(700, (255, 0, 0), {
        "left": pg.K_LEFT,
        "right": pg.K_RIGHT,
        "jump": pg.K_UP,
        "attack": pg.K_RCTRL
    })

    fighters = pg.sprite.Group(p1, p2)

    running = True
    while running:
        screen.fill((30, 30, 30))
        key_lst = pg.key.get_pressed()

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

            if game_state == TITLE:
                if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                    game_state = SELECT

            elif game_state == SELECT:
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_UP:
                        selected_stage = (selected_stage - 1) % len(STAGES)
                    if event.key == pg.K_DOWN:
                        selected_stage = (selected_stage + 1) % len(STAGES)
                    if event.key == pg.K_RETURN:
                        current_stage = selected_stage
                        game_state = BATTLE

        if game_state == TITLE:
            draw_title()
        elif game_state == SELECT:
            draw_select(selected_stage)
        # elif game_state == BATTLE:
        #     screen.blit(STAGES[current_stage]["bg"], (0, 0))
        elif game_state == BATTLE:
            # 背景描画
            screen.blit(STAGES[current_stage]["bg"], (0, 0))

            # 更新（バトル中のみ）
            fighters.update(key_lst)
            attacks.update()

            # 当たり判定
            if pg.sprite.spritecollide(p1, attacks, True):
                p1.hp -= 5
            if pg.sprite.spritecollide(p2, attacks, True):
                p2.hp -= 5

            # 描画
            fighters.draw(screen)
            attacks.draw(screen)    

        # 勝敗判定
        if p1.hp <= 0 or p2.hp <= 0:
            font = pg.font.Font(None, 80)
            text = font.render("K.O.", True, (255, 255, 0))
            screen.blit(text, (WIDTH//2 - 80, HEIGHT//2 - 40))
            pg.display.update()
            pg.time.delay(2000)
            return

        pg.display.update()
        clock.tick(60)

if __name__ == "__main__":
    main()
    pg.quit()
    sys.exit()