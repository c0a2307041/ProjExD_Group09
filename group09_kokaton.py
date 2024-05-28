import math
import os
import random
import sys
import time
import pygame as pg

WIDTH, HEIGHT = 1600, 900  # ゲームウィンドウの幅，高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def check_bound(obj_rct:pg.Rect) -> tuple[bool, bool]:
    """
    Rectの画面内外判定用の関数
    引数：こうかとんRect，または，爆弾Rect，またはビームRect
    戻り値：横方向判定結果，縦方向判定結果（True：画面内／False：画面外）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:  # 横方向のはみ出し判定
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:  # 縦方向のはみ出し判定
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal" #変数stateの設定
        self.hyper_life = -1 #変数hyper_lifeの設定

    def bird_check(self):
        """
        シフトを押している間速さを変える関数
        """
        key_lst = pg.key.get_pressed()
        if key_lst[pg.K_LSHIFT]:
            self.speed = 20


    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        if self.state == "hyper": #stateがhyper（無敵）の時
            self.hyper_life -= 1 #1ずつ減少
            self.image2 = pg.transform.laplacian(self.image)#透明なこうかとん作成
            self.images = [self.imgs[self.dire],self.image2]#透明なこうかとんと普通のこうかとんのリスト
            self.image = self.images[self.hyper_life//4%2] #攻撃を受けた際に点滅するように
        if self.hyper_life < 0: #hyper_lifeが0になったら
            self.state = "normal" #stateがnormal(通常)になる ＝ 無敵解除
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height/2
        self.speed = 6

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Syuriken(pg.sprite.Sprite):
    """
    手裏剣に関するクラス
    """
    def __init__(self, bird: Bird):
        """
        手裏剣画像Surfaceを生成する
        引数 bird：手裏剣を放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/syu.png"), angle, 2.0)#画像ロード
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 20

    def update(self):
        """
        手裏剣を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vy = +6
        self.bound = random.randint(50, HEIGHT/2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.centery += self.vy


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


#レベル上げ
class Level:
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Level: {self.value}", 0, self.color) #レベルの表示
        self.rect = self.image.get_rect()
        self.rect.center = 1500, 25 #座標

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Level: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)  



class Bird_life():
    """
    こうかとんのライフを表示するクラス
    """
    def __init__(self):
        self.value = 10
        
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.image = self.font.render(f"Life", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = WIDTH-100, HEIGHT-50
        '''
        こうかとんのライフゲージの枠設定
        '''
        self.width = 1105
        self.height = 40
        self.image = pg.Surface((self.width,self.height),pg.SRCALPHA)
        pg.draw.rect(self.image,(255,255,255),(0,0,self.width,self.height))
        self.rect = self.image.get_rect()
        '''
        こうかとんのライフゲージの設定  
        '''
        self.width = self.value*100
        self.height = 25
        if self.value < 3: #こうかとんのライフが３以上あるときライフゲージは青色
            self.gauge_color = (255,0,0)
        else:              #こうかとんのライフが2以下のときライフゲージは赤色
            self.gauge_color = (0,0,255)
        self.image = pg.Surface((self.width,self.height),pg.SRCALPHA)
        pg.draw.rect(self.image,self.gauge_color,(0,0,self.width,self.height))
        self.rect = self.image.get_rect()

        

    def update(self, screen: pg.Surface):
        self.width = 1080
        self.height = 30
        self.image = pg.Surface((self.width,self.height),pg.SRCALPHA)
        pg.draw.rect(self.image,(255,255,255),(70,5,self.width,self.height))
        self.rect = self.image.get_rect()
        screen.blit(self.image, self.rect)

        self.width = self.value*100+75
        self.height = 25
        if self.value < 3:
            self.gauge_color = (255,0,0)
        else:
            self.gauge_color = (0,0,255)
        self.image = pg.Surface((self.width,self.height),pg.SRCALPHA)
        pg.draw.rect(self.image,self.gauge_color,(75,10,self.width,self.height))
        self.rect = self.image.get_rect()
        screen.blit(self.image, self.rect)
        
        self.image = self.font.render(f"Life", 0, self.color)
        screen.blit(self.image, self.rect)
        


def main():
    pg.display.set_caption("こうかとん疾風伝")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    bg_img2 = pg.image.load(f"fig/pg_bg.jpg")
    bg_img2 = pg.transform.flip(bg_img2,True,False)
    score = Score()
    bird_lf = Bird_life() 

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    syuris = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    

    tmr = 0
    clock = pg.time.Clock()
    level = Level()
    while True:
        bird.bird_check() 
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                syuris.add(Syuriken(bird))

        x = tmr%3200
                
        screen.blit(bg_img, [-x, 0])
        screen.blit(bg_img2, [-x+1600, 0])
        screen.blit(bg_img, [-x+3200, 0])
        screen.blit(bg_img2, [-x+4800, 0])

        if tmr%2000 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, syuris, True, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト
        for bomb in pg.sprite.groupcollide(bombs, syuris, True, True).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

            #レベル上げ
        if score.value > 0: #スコア０以上の時
            level.value = score.value // 30 # スコアが３０上がるたびに1上がる
        
        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if bird.state == "hyper": # こうかとんが無敵状態（hyper）の時
                exps.add(Explosion(bomb, 50)) # こうかとんと爆弾が衝突時、爆弾が爆発する
                break
            if bird_lf.value == 1:
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                score.update(screen)
                level.update(screen)
                bird_lf.value -= 1
                bird_lf.update(screen)
                
                pg.display.update()
                time.sleep(2)
                return
            else:
                bird.state = "hyper" # こうかとんがhyper(無敵状態)になる
                bird.hyper_life = 20 # 発動時間20フレーム
                bird_lf.value -= 1

            
        for emy in pg.sprite.spritecollide(bird, emys, True):
            if bird.state == "hyper": # こうかとんが無敵状態（hyper）の時
                exps.add(Explosion(emy, 50)) # こうかとんと爆弾が衝突時、爆弾が爆発する
                break
            if bird_lf.value == 1:
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                score.update(screen)
                bird_lf.value -= 1
                bird_lf.update(screen)
                pg.display.update()
                time.sleep(2)
                return
            else:
                bird.state = "hyper" # こうかとんがhyperになる
                bird.hyper_life = 20 # 発動時間20フレーム
                bird_lf.value -= 1
    

        bird.update(key_lst, screen)
        syuris.update()
        syuris.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        score.update(screen)
        bird_lf.update(screen)
        level.update(screen)
        pg.display.update()
        tmr += 10
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
