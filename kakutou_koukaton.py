import pygame as pg
import sys
import os

# =====================
# 定数・初期設定
# =====================
WIDTH, HEIGHT = 1000, 600
FLOOR = HEIGHT - 50

TITLE = 0
SELECT = 1
BATTLE = 2
PAUSED = 3
SETTINGS = 4

# OS判定して適切なフォントパスを設定
import platform
if platform.system() == "Windows":
    FONT_PATH = "C:/Windows/Fonts/msgothic.ttc"
elif platform.system() == "Darwin":  # macOS
    FONT_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc"
else:  # Linux等
    FONT_PATH = None  # システムデフォルトフォントを使用

# BGMファイル(プロジェクト内の相対パス)
MENU_BGM = "sound/bgm/menu-bgm.mp3"
BATTLE_BGM = "sound/bgm/vhs-tape.mp3"

# マッチ時間(秒) -- 90秒
MATCH_TIME = 90

# カレントディレクトリをスクリプトの場所に
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except Exception:
    pass

pg.init()
pg.mixer.init()
screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("こうかとん ファイター")
clock = pg.time.Clock()

# フォント
FONT_BIG = pg.font.Font(None, 80)
FONT_MED = pg.font.Font(None, 36)
FONT_SMALL = pg.font.Font(None, 24)


# =====================
# ユーティリティ関数
# =====================
def safe_load_and_play_bgm(path, volume=0.5, loops=-1):
    """
    BGMを安全にロードして再生する(ファイルが無くてもクラッシュさせない)。
    """
    try:
        pg.mixer.music.load(path)
        pg.mixer.music.set_volume(volume)
        pg.mixer.music.play(loops)
    except Exception as e:
        print(f"[BGM load error] {path} : {e}")


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
        "name": "繁華街(夜)",
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
    """
    プレイヤー用ファイター。移動、ジャンプ、HPを管理する。
    keys: dict で "left","right","jump","attack" のキーコードを渡す
    """
    def __init__(self, x, color, keys, name="Fighter"):
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
        self.facing = 1  # 1 = 右向き, -1 = 左向き
        self.name = name

    def update(self, key_lst):
        """
        入力に応じて移動・ジャンプ処理を行い、重力と地面判定を適用する。
        """
        self.vx = 0

        if key_lst[self.keys["left"]]:
            self.vx = -6
            self.facing = -1
        if key_lst[self.keys["right"]]:
            self.vx = 6
            self.facing = 1

        if key_lst[self.keys["jump"]] and self.on_ground:
            self.vy = -20
            self.on_ground = False

        # 簡易重力
        self.vy += 1

        # 位置更新
        self.rect.x += self.vx
        self.rect.y += self.vy

        # 地面判定
        if self.rect.bottom >= FLOOR:
            self.rect.bottom = FLOOR
            self.vy = 0
            self.on_ground = True


# =====================
# 攻撃クラス
# =====================
class Attack(pg.sprite.Sprite):
    """
    簡易な飛び道具/パンチ用スプライト。
    owner: 発射元の Fighter オブジェクト(味方判定に使用)
    life: 生存フレーム(寿命)
    vx: 横速度
    """
    def __init__(self, fighter):
        super().__init__()
        self.image = pg.Surface((40, 20))
        self.image.fill((255, 0, 0))
        self.rect = self.image.get_rect()

        # 発射時の位置をファイターの前方に設定
        if fighter.facing == 1:
            self.rect.midleft = fighter.rect.midright
            self.vx = 12
        else:
            self.rect.midright = fighter.rect.midleft
            self.vx = -12

        self.life = 30
        self.owner = fighter

    def update(self):
        """
        横移動し、寿命が尽きたら削除する。
        """
        self.rect.x += self.vx
        self.life -= 1
        if self.life <= 0:
            self.kill()


# =====================
# UI: タイマー・スコア・ポーズ等を管理するクラス
# =====================
class HUD:
    """
    画面上部のタイマー・スコア・ポーズボタン・下部の操作説明を描画する。
    """
    def __init__(self):
        self.match_time = MATCH_TIME
        self.p1_wins = 0
        self.p2_wins = 0
        # ポーズボタン領域(右上)
        self.pause_rect = pg.Rect(WIDTH - 110, 70, 100, 40)
        # 音量
        self.volume = 0.5

    def reset_timer(self):
        self.match_time = MATCH_TIME

    def update_time(self, dt):
        """
        秒単位の時間を減少させる(dt は秒)。
        """
        self.match_time = max(0, self.match_time - dt)

    def draw_top(self, screen):
        """
        上部中央に時間、左/右にスコア、右上にポーズボタンを描画する。
        """
        # スコア(左・右)
        score_left = FONT_MED.render(f"P1 Wins: {self.p1_wins}", True, (255, 255, 255))
        score_right = FONT_MED.render(f"P2 Wins: {self.p2_wins}", True, (255, 255, 255))
        screen.blit(score_left, (10, 10))
        screen.blit(score_right, (WIDTH - 10 - score_right.get_width(), 10))

        # タイマー(中央) - 秒表示(整数)
        time_sec = int(self.match_time)

        # 30秒以下で点滅(偶数秒:赤 / 奇数秒:白)
        if time_sec <= 30 and time_sec % 2 == 0:
            time_color = (255, 0, 0)   # 赤
        else:
            time_color = (255, 255, 255)

        time_text = FONT_MED.render(f"Time: {time_sec}", True, time_color)
        screen.blit(time_text, (WIDTH // 2 - time_text.get_width() // 2, 10))

        # ポーズボタン(右上)
        pg.draw.rect(screen, (180, 180, 180), self.pause_rect)
        p_label = FONT_SMALL.render("PAUSE", True, (0, 0, 0))
        screen.blit(p_label, (self.pause_rect.centerx - p_label.get_width() // 2,
                              self.pause_rect.centery - p_label.get_height() // 2))

    def draw_bottom_controls(self, screen, p1_keys_text, p2_keys_text):
        """
        画面下部に1行で操作説明を表示(左側P1、右側P2)。
        """
        # 1行の背面灰色長方形(視認性のため)
        rect = pg.Rect(0, HEIGHT - 40, WIDTH, 40)
        pg.draw.rect(screen, (40, 40, 40), rect)
        left = FONT_SMALL.render(p1_keys_text, True, (220, 220, 220))
        right = FONT_SMALL.render(p2_keys_text, True, (220, 220, 220))
        screen.blit(left, (10, HEIGHT - 32))
        screen.blit(right, (WIDTH - 10 - right.get_width(), HEIGHT - 32))


# =====================
# UI: ポーズ画面。続行・設定・終了のメニュー
# =====================
class PauseMenu:
    """
    ポーズ画面。続行・設定・終了メニューを実装。
    """
    def __init__(self, hud):
        self.options = ["Continue", "Settings", "Quit"]
        self.selected = 0
        self.hud = hud

    def draw(self, screen):
        """
        半透明の背景+メニュー描画。
        """
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        title = FONT_BIG.render("Paused", True, (255, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        # メニュー
        for i, opt in enumerate(self.options):
            color = (255, 255, 0) if i == self.selected else (220, 220, 220)
            label = FONT_MED.render(opt, True, color)
            rect = label.get_rect(center=(WIDTH // 2, 220 + i * 70))
            screen.blit(label, rect)

        # 操作ガイド
        guide = FONT_SMALL.render("↑↓ Select  ENTER Confirm  SPACE Continue", True, (200, 200, 200))
        screen.blit(guide, (WIDTH // 2 - guide.get_width() // 2, 500))

    def handle_event(self, event):
        """
        キー入力でメニューを操作する。選択確定は呼び出し元で判定する。
        """
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            if event.key == pg.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            if event.key == pg.K_RETURN:
                return self.options[self.selected]
            if event.key == pg.K_SPACE:
                return "Continue"
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            # クリックで選択
            mx, my = event.pos
            for i, opt in enumerate(self.options):
                label = FONT_MED.render(opt, True, (0, 0, 0))
                rect = label.get_rect(center=(WIDTH // 2, 220 + i * 70))
                if rect.collidepoint(mx, my):
                    return opt
        return None


# =====================
# UI: 設定画面(音量調整)
# =====================
class SettingsMenu:
    """
    設定画面(音量調整)。
    """
    def __init__(self, hud):
        self.hud = hud

    def draw(self, screen):
        """
        設定画面の描画。
        """
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        title = FONT_BIG.render("Settings", True, (255, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        # 音量表示
        vol_text = FONT_MED.render(f"Music Volume: {int(self.hud.volume * 100)}%", True, (255, 255, 255))
        screen.blit(vol_text, (WIDTH // 2 - vol_text.get_width() // 2, 250))

        # 音量バー
        bar_back = pg.Rect(WIDTH // 2 - 150, 320, 300, 20)
        pg.draw.rect(screen, (80, 80, 80), bar_back)
        fill = pg.Rect(bar_back.x, bar_back.y, int(300 * self.hud.volume), 20)
        pg.draw.rect(screen, (0, 200, 100), fill)

        # 操作ガイド
        guide1 = FONT_SMALL.render("←/→ to change volume", True, (200, 200, 200))
        guide2 = FONT_SMALL.render("ESC or ENTER to return to pause menu", True, (200, 200, 200))
        screen.blit(guide1, (WIDTH // 2 - guide1.get_width() // 2, 400))
        screen.blit(guide2, (WIDTH // 2 - guide2.get_width() // 2, 430))

        # 戻るボタン
        back_rect = pg.Rect(WIDTH // 2 - 75, 480, 150, 50)
        pg.draw.rect(screen, (100, 100, 100), back_rect)
        pg.draw.rect(screen, (200, 200, 200), back_rect, 2)
        back_label = FONT_MED.render("Back", True, (255, 255, 255))
        screen.blit(back_label, (back_rect.centerx - back_label.get_width() // 2,
                                 back_rect.centery - back_label.get_height() // 2))

        self.back_rect = back_rect

    def handle_event(self, event):
        """
        設定画面のイベント処理。
        """
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_LEFT:
                self.hud.volume = max(0.0, self.hud.volume - 0.05)
                pg.mixer.music.set_volume(self.hud.volume)
            if event.key == pg.K_RIGHT:
                self.hud.volume = min(1.0, self.hud.volume + 0.05)
                pg.mixer.music.set_volume(self.hud.volume)
            if event.key == pg.K_ESCAPE or event.key == pg.K_RETURN:
                return "Back"
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # バーをクリックして音量変更
            bar = pg.Rect(WIDTH // 2 - 150, 320, 300, 20)
            if bar.collidepoint(mx, my):
                rel = (mx - bar.x) / bar.width
                self.hud.volume = min(1.0, max(0.0, rel))
                pg.mixer.music.set_volume(self.hud.volume)
            # 戻るボタン
            if self.back_rect.collidepoint(mx, my):
                return "Back"
        return None


# =====================
# タイトル画面
# =====================
def draw_title():
    screen.blit(TITLE_BG, (0, 0))

    overlay = pg.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(120)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    # フォントパスがNoneの場合はデフォルトフォントを使用
    if FONT_PATH:
        font = pg.font.Font(FONT_PATH, 80)
        small = pg.font.Font(FONT_PATH, 36)
    else:
        font = pg.font.Font(None, 80)
        small = pg.font.Font(None, 36)

    title = font.render("こうかとん ファイター", True, (255, 255, 255))
    guide = small.render("ENTERキーでスタート", True, (230, 230, 230))

    screen.blit(title, (WIDTH//2 - title.get_width()//2, 220))
    screen.blit(guide, (WIDTH//2 - guide.get_width()//2, 330))


# =====================
# バトル選択画面
# =====================
def draw_select(selected):
    # 選択肢に応じた背景表示(ゲーム終了以外)
    if selected < len(STAGES):
        screen.blit(STAGES[selected]["bg"], (0, 0))
    else:
        screen.blit(STAGES[0]["bg"], (0, 0))

    overlay = pg.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(150)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    # フォントパスがNoneの場合はデフォルトフォントを使用
    if FONT_PATH:
        font = pg.font.Font(FONT_PATH, 60)
        small = pg.font.Font(FONT_PATH, 30)
    else:
        font = pg.font.Font(None, 60)
        small = pg.font.Font(None, 30)

    title = font.render("バトルステージ選択", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 60))

    # ステージ選択肢
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

    # ゲーム終了ボタン
    quit_index = len(STAGES)
    color = (255, 255, 0) if quit_index == selected else (200, 200, 200)
    label = small.render("ゲーム終了", True, color)
    rect = pg.Rect(350, 180 + quit_index * 80, 300, 50)
    pg.draw.rect(screen, color, rect, 2)
    screen.blit(
        label,
        (rect.centerx - label.get_width()//2,
         rect.centery - label.get_height()//2)
    )

    guide = small.render("↑↓で選択  ENTERで決定", True, (220, 220, 220))
    screen.blit(guide, (WIDTH//2 - guide.get_width()//2, 500))


# =====================
# メイン処理
# =====================
def main():
    game_state = TITLE
    selected_stage = 0
    current_stage = 0

    # グループ
    fighters = pg.sprite.Group()
    attacks = pg.sprite.Group()

    # プレイヤー作成
    p1 = Fighter(200, (0, 0, 255), {
        "left": pg.K_a,
        "right": pg.K_d,
        "jump": pg.K_w,
        "attack": pg.K_f
    }, name="P1")

    p2 = Fighter(700, (255, 0, 0), {
        "left": pg.K_LEFT,
        "right": pg.K_RIGHT,
        "jump": pg.K_UP,
        "attack": pg.K_RCTRL
    }, name="P2")

    fighters.add(p1, p2)

    # HUD とメニュー
    hud = HUD()
    pause_menu = PauseMenu(hud)
    settings_menu = SettingsMenu(hud)

    # 初期BGM(タイトル/メニュー)
    safe_load_and_play_bgm(MENU_BGM, hud.volume)

    running = True

    # 操作説明(下部)
    p1_keys_text = "P1: A/D Move  W Jump  F Attack"
    p2_keys_text = "P2: ←/→ Move  ↑ Jump  RCTRL Attack"

    # バトル画面の保存用(ポーズ時に背景として使う)
    battle_surface = None

    while running:
        dt_ms = clock.tick(60)
        dt = dt_ms / 1000.0

        key_lst = pg.key.get_pressed()

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

            # ===== タイトル =====
            if game_state == TITLE:
                if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                    game_state = SELECT

            # ===== バトル選択 =====
            elif game_state == SELECT:
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_UP:
                        selected_stage = (selected_stage - 1) % (len(STAGES) + 1)
                    if event.key == pg.K_DOWN:
                        selected_stage = (selected_stage + 1) % (len(STAGES) + 1)
                    if event.key == pg.K_RETURN:
                        if selected_stage == len(STAGES):  # ゲーム終了
                            running = False
                        else:
                            current_stage = selected_stage
                            game_state = BATTLE
                            hud.reset_timer()
                            safe_load_and_play_bgm(BATTLE_BGM, hud.volume)

            # ===== バトル中の入力 =====
            elif game_state == BATTLE:
                # ESCキーでポーズ
                if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                    game_state = PAUSED
                    battle_surface = screen.copy()

                # ポーズボタン(クリック判定)
                if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    if hud.pause_rect.collidepoint(event.pos):
                        game_state = PAUSED
                        battle_surface = screen.copy()

                if event.type == pg.KEYDOWN:
                    # 攻撃キーでAttack生成
                    if event.key == p1.keys["attack"]:
                        attacks.add(Attack(p1))
                    if event.key == p2.keys["attack"]:
                        attacks.add(Attack(p2))

            # ===== ポーズ中の入力 =====
            elif game_state == PAUSED:
                result = pause_menu.handle_event(event)
                if result == "Continue":
                    game_state = BATTLE
                elif result == "Settings":
                    game_state = SETTINGS
                elif result == "Quit":
                    game_state = SELECT
                    safe_load_and_play_bgm(MENU_BGM, hud.volume)

            # ===== 設定画面の入力 =====
            elif game_state == SETTINGS:
                result = settings_menu.handle_event(event)
                if result == "Back":
                    game_state = PAUSED

        # ===== 描画・更新 =====
        if game_state == TITLE:
            draw_title()

        elif game_state == SELECT:
            draw_select(selected_stage)

        elif game_state == BATTLE:
            # 背景描画
            screen.blit(STAGES[current_stage]["bg"], (0, 0))

            # 時間の経過更新
            hud.update_time(dt)

            # 更新
            fighters.update(key_lst)
            attacks.update()

            # 攻撃判定(攻撃のownerが被弾相手と等しくないことを確認)
            for atk in attacks.copy():
                if atk.owner != p1 and atk.rect.colliderect(p1.rect):
                    p1.hp -= 5
                    atk.kill()
                if atk.owner != p2 and atk.rect.colliderect(p2.rect):
                    p2.hp -= 5
                    atk.kill()

            # 描画
            fighters.draw(screen)
            attacks.draw(screen)

            # HUD 描画
            hud.draw_top(screen)
            hud.draw_bottom_controls(screen, p1_keys_text, p2_keys_text)

            # 終了条件: HPが0か時間切れ
            if p1.hp <= 0 or p2.hp <= 0 or hud.match_time <= 0:
                # 勝者判定
                if p1.hp > p2.hp:
                    winner = "P1"
                    hud.p1_wins += 1
                elif p2.hp > p1.hp:
                    winner = "P2"
                    hud.p2_wins += 1
                else:
                    winner = "Draw"

                # 表示
                result_text = FONT_BIG.render("K.O." if (p1.hp <= 0 or p2.hp <= 0) else "Time Up", True, (255, 255, 0))
                screen.blit(result_text, (WIDTH // 2 - result_text.get_width() // 2, HEIGHT // 2 - 40))
                winner_text = FONT_MED.render(f"Winner: {winner}", True, (255, 255, 255))
                screen.blit(winner_text, (WIDTH // 2 - winner_text.get_width() // 2, HEIGHT // 2 + 30))
                pg.display.update()
                pg.time.delay(2000)

                # リセット
                p1.hp = 100
                p2.hp = 100
                attacks.empty()
                hud.reset_timer()
                safe_load_and_play_bgm(MENU_BGM, hud.volume)
                game_state = SELECT
                continue

        elif game_state == PAUSED:
            # バトル画面を背景として表示
            if battle_surface:
                screen.blit(battle_surface, (0, 0))
            pause_menu.draw(screen)

        elif game_state == SETTINGS:
            # バトル画面を背景として表示
            if battle_surface:
                screen.blit(battle_surface, (0, 0))
            settings_menu.draw(screen)

        pg.display.update()

    pg.quit()
    sys.exit()


# =====================
# 実行
# =====================
if __name__ == "__main__":
    main()