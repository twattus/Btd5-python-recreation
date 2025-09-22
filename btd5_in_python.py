import pygame,sys,math,random
from pygame.locals import QUIT

pygame.init()

screen_x=1000
screen_y=600
tick=0
player_money=650 #starting money
player_lives=400

speeds=[1,1.3,1.5,2,2.5,1.1,3] #speeds for each balloon type
temp_balloon_cols=[(255,0,0),(0,0,255),(0,255,0),(255,255,0),(255,64,128),(200,200,200),(123,213,231)] #for temp rects - use blit later
balloon_sizes=[15,15,20,20,20,25,20]
balloon_level_hp=[1,1,1,1,1,4,2] #pops taken to get to next layer - not health of  each type
global selected_tower #mildly dodgy
selected_tower=-1 #tower id, -1 means nothing selected
main_font=pygame.font.SysFont("bahnschrift", 32) #(cheeky little bit of memoisation)
cursor_font=pygame.font.SysFont("bahnschrift", 24) #if I dont do this the font is redefined every tick
player_round=0
round_interim=False
new_round=False #1 tick flag to release bloons
cursor_message="" #explains what things does - sort of like this
banana_farm_round_income=0 #btd4 style farms (if I can be bothered to implement it)
game_speeds=[1,2,4]
game_speed_option=0#index of game_speeds


def distance(p_1_x,p_1_y,p_2_x,p_2_y):
    return math.sqrt(((p_1_x-p_2_x)**2)+((p_1_y-p_2_y)**2))

def remove_false(list_name):
    return [e for e in list_name if e]

def in_bounds(x,y,tolerance):
    return (x+tolerance>0 and x-tolerance<=screen_x) and (y+tolerance>0 and y-tolerance<screen_y) #tolerance for how far out of bounds they need to be

def sign(x):
    if x<0:
        return -1
    else:
        return 1

def draw_text(text,x,y,col):
    screen.blit(main_font.render(text,1,col),(x,y))

def cursor_text_draw(text):
    screen.blit(cursor_font.render(text,1,(187,165,61)),(0,screen_y-24))

class track:
    def __init__(self,points):
        self.points=points

    def balloon_pos(self,time,level): #IT WORKS!! 
        if time<-10:
            return [-512,-512]
        total_length=0
        lengths=[]
        for e in range(0,len(self.points)-1):
            lengths.append(distance(self.points[e][0],self.points[e][1],self.points[e+1][0],self.points[e+1][1]))
        covered=time*speeds[level]
        last_point=-1
        dist_between=0
        for e in range(0,len(lengths)):
            total_length+=lengths[e]
            if total_length>=covered:
                last_point=e
                dist_between=covered-(total_length-lengths[e])
                break
        if last_point==-1:
            return [-256,-256]
        x_val=self.points[last_point][0]+(self.points[last_point+1][0]-self.points[last_point][0])*(dist_between/lengths[last_point])
        y_val=self.points[last_point][1]+(self.points[last_point+1][1]-self.points[last_point][1])*(dist_between/lengths[last_point])
        return [x_val,y_val]

    def draw_track(self):
        for e in range(0,len(self.points)-1):
            pygame.draw.line(screen,(96,96,96),self.points[e],self.points[e+1],20)

class balloon:
    def __init__(self,x,y,level,hp,time):
        self.x=x
        self.y=y
        self.level=level
        self.hp=hp
        self.time=time
        self.popped=False

    def update_pos(self,track):
        coords=track.balloon_pos(self.time,self.level)
        self.x=coords[0]
        self.y=coords[1]
    
    def update_time(self):
        self.time+=1

    def generate_rect(self):
        return pygame.Rect(self.x-balloon_sizes[self.level]//2,self.y-balloon_sizes[self.level]//2,balloon_sizes[self.level],balloon_sizes[self.level])
    
    def draw_balloon(self):
        pygame.draw.rect(screen,temp_balloon_cols[self.level],self.generate_rect())

    def damage_balloon(self,projectile_name):
        projectile_name.pierce-=1
        self.hp-=projectile_name.dmg
        if self.hp<=0:
            self.pop_layer()
    
    def cumulative_hp(self):
        if self.level: return sum(balloon_level_hp[:self.level])+self.hp
        else: return self.hp


    def pop_layer(self):
        global player_money
        while self.hp<=0:
            if self.level>0:
                self.time*=(speeds[self.level]/speeds[self.level-1])
                self.level-=1
                self.hp+=balloon_level_hp[self.level]
                player_money+=1
            else:
                self.popped=True
                player_money+=1
                break
projectiles=[]
projectile_stats=[[1,1,16,16,(128,128,128)], #0 - dart monkey dart
                  [16,4,8,40,(128,128,128)], #1 - art monkey boulder
                  [1,1,4,8,(255,0,0)],  #2 - small flamethrower flame
                  [1,6,50,40,(62,32,32)], #3 - small sniper bullet
                  [1,20,100,70,(42,32,32)], #4 - big sniper bullet
                  [1,2,6,10,(255,0,0)], #5 - big flamethrower flame
                  [1,1,12,8,(96,96,96)], #6 - small tack shooter tack
                  [2,2,12,8,(106,106,106)], #7 - medium tack shooter tack
                  [3,4,12,8,(146,66,36)],  #8 - big tack shooter tack
                  [1,1,8,12,(128,128,128)], #9 - small ninja shuriken
                  [2,1,10,14,(138,138,128)], #10 - medium ninja shuriken
                  [2,2,12,16,(168,128,128)], #11 - big ninja shuriken
                  [0,0,0,0,(0,0,0)]]  

# stats are as follows:
#pierce,dmg,max_vel,size,col

projectile_id_special_stats=[[0],[0],[1,3,15,0],[0],[0],[1,3,3,0],[1,6,360,1],[1,10,360,1],[1,20,360,1],[0],[1,2,15,0],[1,5,20,1]] 
#first index indicates if there is anything special
#flags are as follows:
#0 - specialness (bool)1 - num of projectiles, 2 - spread angle, 3 - uniform spread(bool)

class projectile:
    def __init__(self,x,y,angle,id):
        self.x=x
        self.y=y
        self.id=id
        self.angle=angle #in degrees NOTE: USE math.radians() WHEN PUTTING NUMBERS INTO TRIG FUNCS
        self.pierce=projectile_stats[id][0]
        self.dmg=projectile_stats[id][1]
        self.max_vel=projectile_stats[id][2] #x and y vel are done with some cheeky trig
        self.size=projectile_stats[id][3]
        self.colour=projectile_stats[id][4]
        self.expired=False
        self.x_vel=round(math.cos(math.radians(self.angle))*self.max_vel,6) #cheeky trig incoming
        self.y_vel=round(math.sin(math.radians(self.angle))*self.max_vel,6)

        
    
    def proj_move(self):
        self.x+=self.x_vel
        self.y+=self.y_vel

    def generate_rect(self):
        return pygame.Rect(self.x-self.size//2,self.y-self.size//2,self.size,self.size)
    
    def draw_projectile(self):
        if not self.expired:
            pygame.draw.rect(screen,self.colour,self.generate_rect())
    
    def collide_balloon(self,track_name):
        on_path=False
        collision_box_rough=self.generate_rect()
        collision_box_rough.height+=max(balloon_sizes)
        collision_box_rough.width+=max(balloon_sizes)
        collision_box_rough.center=(self.x,self.y)
        for e in range(0,len(track_name.points)-1):
            if collision_box_rough.clipline(tuple(track_name.points[e]),tuple(track_name.points[e+1])):
                on_path=True
                break
        if not on_path:
            return False
        for e in range(0,len(balloons)):
            if self.pierce==0:
                self.expired=True
                break
            if balloons[e].time>-10 and pygame.Rect.colliderect(self.generate_rect(),balloons[e].generate_rect()):
                balloons[e].damage_balloon(self)


tower_behaviours=[[[150,50,0,(125,42,42),40,180],[150,40,0,(165,52,52),40,150],[250,15,0,(165,62,62),40,400],[450,120,1,(165,72,72),50,4200]], #3d list -top layer for id, bottom layer for level
                  [[80,45,2,(165,0,0),30,300],[80,40,2,(185,0,0),30,250],[80,40,2,(195,0,0),30,500],[200,6,5,(205,0,32),40,3500]],  #flamethrower
                  [[8000,140,3,(0,165,0),35,250],[8000,100,3,(0,190,0),35,240],[8000,80,4,(0,220,0),35,400],[8000,20,4,(0,255,0),40,2200]],  #sniper
                  [[150,80,6,(255,42,92),40,270],[150,60,6,(255,32,92),40,210],[150,60,7,(255,52,92),40,500],[150,35,8,(255,102,92),40,4000]], #tack shooter
                  [[200,60,9,(200,0,0),40,340],[250,50,9,(210,10,10),40,230],[250,45,10,(220,40,40),40,640],[250,30,11,(250,60,60),40,2300]], #ninja
                  [[],[],[],[]]]
# Traits are as follows :
#0 - range, 1 - attack speed (cooldown in ticks), 2 - projectile id, 3 - colour(replace with image later), 4 - size, 5 - cost (first index is purchase cost, others are upgrade cost)
# ids: 0-monke, 1-flamethrower, 2-sniper, 3-tack shooter, 4-ninja
tower_names=["Dart monkey","Flamethrower","Sniper","Tack Shooter","Ninja"]

class tower:
    def __init__(self,x,y,id,level):
        self.x=x
        self.y=y
        self.id=id
        self.level=level
        self.attack_cooldown=0
        self.range=tower_behaviours[self.id][self.level][0]
        self.atk_speed=tower_behaviours[self.id][self.level][1]
        self.proj_type=tower_behaviours[self.id][self.level][2]#just the id - everything else handled by the projectile class
        self.colour=tower_behaviours[self.id][self.level][3]
        self.size=tower_behaviours[self.id][self.level][4]
        self.price=tower_behaviours[self.id][self.level][5]
        self.rect=pygame.Rect(x-(self.size//2),y-(self.size//2),self.size,self.size)
    
    def draw_tower(self):
        pygame.draw.rect(screen,self.colour,self.rect)

    def advance_time(self):
        if self.attack_cooldown>0:
            self.attack_cooldown-=1    
    
    def attack(self,angle):
        if projectile_id_special_stats[self.proj_type][0]:
            projectile_quantity=projectile_id_special_stats[self.proj_type][1]
            projectile_arc_aim=projectile_id_special_stats[self.proj_type][2]

            for e in range(0,projectile_quantity):
                if projectile_id_special_stats[self.proj_type][3]: #uniform spread for tack shooters
                    arc_angle=angle+((e-projectile_quantity/2)*(projectile_id_special_stats[self.proj_type][2]/projectile_quantity))
                else:
                    arc_angle=angle+random.randint(-projectile_arc_aim,projectile_arc_aim)
                projectiles.append(projectile(self.x,self.y,arc_angle,self.proj_type))
        else:
            projectiles.append(projectile(self.x,self.y,angle,self.proj_type))

    def detect_balloon(self):
        if not self.attack_cooldown:
            for e in range(0,len(balloons)):
                if balloons[e].x==-256 and balloons[e].y==-256: #🚨MAGIC NUMBER ALERT🚨 - (-256,-256) is where balloons with a delayed spawn live until they enter the track
                    continue #"just fix the maxic number by giving the location a name" shut up
                if balloons[e].time<-10:
                    continue
                if distance(self.x,self.y,balloons[e].x,balloons[e].y)<=self.range:
                    if self.y>balloons[e].y: #arctan(x) only returns values of ∓90, so 2 cases needed for above tower & below tower 
                        attack_angle=270-(math.degrees(math.atan((sign(self.x-balloons[e].x)*max(abs(self.x-balloons[e].x),0.001))/(sign(self.y-balloons[e].y)*max(abs(self.y-balloons[e].y),0.001)))))
                    else:
                        attack_angle=90-(math.degrees(math.atan((sign(self.x-balloons[e].x)*max(abs(self.x-balloons[e].x),0.001))/(sign(self.y-balloons[e].y)*max(abs(self.y-balloons[e].y),0.001)))))
                    self.attack(attack_angle)
                    self.attack_cooldown=self.atk_speed
                    break

    def upgrade_tower(self):
        global player_money
        if self.level<3 and player_money>=tower_behaviours[self.id][self.level+1][5]: #NOTE: self.level is zero based
            self.level+=1
            self.__init__(self.x,self.y,self.id,self.level) #re-initialises it because I defined all the stats at initialisation and I am clinging on to all the memoisation I can
            player_money-=self.price 

    def detect_upgrade(self):
        mouse_pos=pygame.mouse.get_pos()
        if pygame.Rect.collidepoint(self.rect,mouse_pos[0],mouse_pos[1]):
            self.upgrade_tower()

towers=[]


class tower_picker:
    def __init__(self,x,y,size,id):
        self.x=x
        self.y=y
        self.size=size
        self.id=id
        self.rect=pygame.Rect(self.x-self.size//2,self.y-self.size//2,self.size,self.size)

    def draw(self):
        pygame.draw.rect(screen,(tower_behaviours[self.id][0][3]),self.rect)

    def select_tower(self):
        global selected_tower
        if selected_tower==-1:   
            if tower_behaviours[self.id][0][5]<player_money:
                selected_tower=self.id


tower_pickers=[tower_picker(840,160,50,0),tower_picker(900,160,50,1),tower_picker(960,160,50,2),
               tower_picker(840,220,50,3),tower_picker(900,220,50,4)]


class round_balloon_data:
    def __init__(self,balloon_ids,balloon_quantities,balloon_spread,balloon_delay):
        self.balloon_ids=balloon_ids
        self.balloon_quantities=balloon_quantities
        self.balloon_spread=balloon_spread
        self.balloon_delay=balloon_delay
    def deploy_bloons(self):
        for e in range(0,len(self.balloon_ids)):
            for f in range(0,self.balloon_quantities[e]):
                balloons.append(balloon(0,0,self.balloon_ids[e],balloon_level_hp[self.balloon_ids[e]],-self.balloon_delay[e]-(self.balloon_spread[e]*f)))

class button:
    def __init__(self,x,y,width,height,col,text,hover_respond,secondary_col):
        self.x=x
        self.y=y
        self.width=width
        self.height=height
        self.col=col
        self.text=text
        self.hover_respond=hover_respond
        self.secondary_col=secondary_col
        self.rect=pygame.Rect(self.x,self.y,self.width,self.height)
    def get_pressed(self):
        if frame_click[0]:
            return pygame.Rect.collidepoint(self.rect,mouse_position[0],mouse_position[1])
        else: return False
    def get_hover(self):
        return pygame.Rect.collidepoint(self.rect,mouse_position[0],mouse_position[1])
    def draw_button(self):
        if self.hover_respond and self.get_hover():
            pygame.draw.rect(screen,self.secondary_col,self.rect)
            draw_text(self.text,self.x,self.y,(0,0,0))
        else:
            pygame.draw.rect(screen,self.col,self.rect)
            draw_text(self.text,self.x,self.y,(0,0,0))

round_button=button(800,480,200,120,(72,245,72),"Next Round",True,(32,255,32))
speed_button=button(800,420,200,60,(225,62,72),"1x Speed",True,(255,52,52))

temp_track=track([[0,100],[200,120],[400,250],[400,530],[200,400],[200,200],[400,150],[700,450],[800,600]])

balloons=[]

def balloon_sort_key(balloon_name):
    return speeds[balloon_name.level]*balloon_name.time


round_data=[round_balloon_data([0],[10],[60],[0]),round_balloon_data([0,1],[20,10],[40,60],[0,0]),round_balloon_data([0,1,1],[20,15,10],[100,120,30],[0,300,1800]),
            round_balloon_data([1,1,2],[30,15,20],[60,20,40],[0,300,180]),round_balloon_data([1,2,2],[30,60,20],[10,20,5],[0,300,1200]),round_balloon_data([2,2,3],[70,100,40],[15,20,30],[0,300,600]),
            round_balloon_data([2,3,3],[40,30,60],[15,20,20],[0,120,300]),round_balloon_data([3,3,4],[40,20,30],[30,5,45],[0,300,600]),round_balloon_data([4,4,4],[30,30,30],[20,20,10],[0,300,600]),
            round_balloon_data([3,4,5],[50,50,20],[20,15,30],[0,300,900]),round_balloon_data([5,5,3],[5,15,55],[55,35,5],[155,55,555]),round_balloon_data([5,6],[10,20],[5,20],[0,200])]


screen=pygame.display.set_mode((screen_x,screen_y))
pygame.display.set_caption('BTD5 in python')

current_mouse_state=[0,0,0] 
previous_mouse_state=[0,0,0] #uses the last frame to determine this
frame_click=[0,0,0] #clicks this frame

def tower_placement_valid(rect):
    bool_out=(rect.x<800 and rect.x>0) and (rect.y>0 and rect.y<screen_y)
    if bool_out:
        for e in range(0,len(temp_track.points)-1):
            if rect.clipline(tuple(temp_track.points[e]),tuple(temp_track.points[e+1])):
                bool_out=False
                break
    if bool_out:
        for e in range(0,len(towers)):
            if pygame.Rect.colliderect(rect,towers[e].rect):
                bool_out=False
    return bool_out


while True:
    current_mouse_state=pygame.mouse.get_pressed()
    for e in range(0,3):
        frame_click[e]=current_mouse_state[e] and not previous_mouse_state[e]
    mouse_position=pygame.mouse.get_pos()
    clicked_option=False
    deployed_tower=False
    clock=pygame.time.Clock()
    tick+=1
    round_interim=not bool(balloons)# start next round when balloons list is empty
    cursor_message="" #tooltip is empty when nothing selected
    pygame.draw.rect(screen,(0,0,0),pygame.Rect(0,0,screen_x,screen_y)) #bg
    temp_track.draw_track()
    balloons.sort(key=balloon_sort_key,reverse=True)
    temp_balloon_cols[6]=(max(0,255*math.sin(tick/100)),max(0,255*math.sin((900-tick)/80)),max(0,255*math.sin(tick/1000)))
    

    for e in range(0,len(tower_pickers)):
        if pygame.Rect.collidepoint(tower_pickers[e].rect,mouse_position[0],mouse_position[1]):
            cursor_message=f"{tower_names[tower_pickers[e].id]} - £{tower_behaviours[tower_pickers[e].id][0][5]}"
            break
        
    for e in range(0,len(tower_pickers)):
        if not frame_click[0]:
            break
        if selected_tower==-1:
            if pygame.Rect.collidepoint(tower_pickers[e].rect,mouse_position[0],mouse_position[1]):
                tower_pickers[e].select_tower()
                clicked_option=True
                break
    if frame_click[2]:
        selected_tower=-1
    if selected_tower!=-1: #done further down for draw order reasons
        #pygame.draw.rect(screen,tower_behaviours[selected_tower][0][3],pygame.Rect(mouse_position[0]-tower_behaviours[selected_tower][0][4]//2,mouse_position[1]-tower_behaviours[selected_tower][0][4]//2,tower_behaviours[selected_tower][0][4],tower_behaviours[selected_tower][0][4]))
        if (frame_click[0] and not clicked_option) and tower_placement_valid(pygame.Rect(mouse_position[0]-tower_behaviours[selected_tower][0][4]//2,mouse_position[1]-tower_behaviours[selected_tower][0][4]//2,tower_behaviours[selected_tower][0][4],tower_behaviours[selected_tower][0][4])):
            towers.append(tower(mouse_position[0],mouse_position[1],selected_tower,0))
            player_money-=tower_behaviours[selected_tower][0][5]
            selected_tower=-1
            deployed_tower=True #"Erm ackshually memoisation can be used here" shut up
        elif not tower_placement_valid(pygame.Rect(mouse_position[0]-tower_behaviours[selected_tower][0][4]//2,mouse_position[1]-tower_behaviours[selected_tower][0][4]//2,tower_behaviours[selected_tower][0][4],tower_behaviours[selected_tower][0][4])):
            pygame.draw.rect(screen,(255,0,0),pygame.Rect(mouse_position[0]-tower_behaviours[selected_tower][0][4]//2,mouse_position[1]-tower_behaviours[selected_tower][0][4]//2,tower_behaviours[selected_tower][0][4],tower_behaviours[selected_tower][0][4]))

    for e in range(0,len(towers)):
        if pygame.Rect.collidepoint(towers[e].rect,mouse_position[0],mouse_position[1]):
            if towers[e].level<3:
                cursor_message=f"Upgrade level {towers[e].level} > {towers[e].level+1} - £{tower_behaviours[towers[e].id][towers[e].level+1][5]}"
            else:
                cursor_message=f"Max level"
        towers[e].advance_time()
        towers[e].draw_tower()
        towers[e].detect_balloon()
        if frame_click[0] and selected_tower==-1 and not deployed_tower:
            towers[e].detect_upgrade()

    if len(projectiles)>1000:
        projectiles=projectiles[len(projectiles)-1000:] #projectile limit of 1000
    for e in range(0,len(projectiles)):
        if not in_bounds(projectiles[e].x,projectiles[e].y,64):
            projectiles[e]=0
            continue

        projectiles[e].proj_move() 
        projectiles[e].draw_projectile()
        projectiles[e].collide_balloon(temp_track)

    projectiles=[e for e in projectiles if e]

    #<MENU ZONE>




    pygame.draw.rect(screen,(160,160,160),pygame.Rect(800,0,200,screen_y)) #menu bg
    pygame.draw.rect(screen,(85,52,43),pygame.Rect(800,0,screen_x-800,120))
    draw_text(f"Round {player_round}",800,10,(0,0,0))
    draw_text(f"£{str(player_money)}",800,50,(187,165,61)) #187 165 61
    draw_text(f"{str(player_lives)}",800,90,(255,0,0))
    speed_button.text=f"{game_speeds[game_speed_option]}x Speed"
    speed_button.draw_button()
    if round_interim:
        round_button.draw_button()
    else:
        pygame.draw.rect(screen,(255,0,0),round_button.rect)
        draw_text("ROUND IN",800,480,(0,0,0))
        draw_text("PROGRESS",800,520,(0,0,0))
    for e in range(0,len(tower_pickers)):
        tower_pickers[e].draw()
    if selected_tower!=-1:
            if not tower_placement_valid(pygame.Rect(mouse_position[0]-tower_behaviours[selected_tower][0][4]//2,mouse_position[1]-tower_behaviours[selected_tower][0][4]//2,tower_behaviours[selected_tower][0][4],tower_behaviours[selected_tower][0][4])):
                pygame.draw.rect(screen,(255,0,0),pygame.Rect(mouse_position[0]-tower_behaviours[selected_tower][0][4]//2,mouse_position[1]-tower_behaviours[selected_tower][0][4]//2,tower_behaviours[selected_tower][0][4],tower_behaviours[selected_tower][0][4]))
            else:
                pygame.draw.rect(screen,tower_behaviours[selected_tower][0][3],pygame.Rect(mouse_position[0]-tower_behaviours[selected_tower][0][4]//2,mouse_position[1]-tower_behaviours[selected_tower][0][4]//2,tower_behaviours[selected_tower][0][4],tower_behaviours[selected_tower][0][4]))
    if round_interim and round_button.get_pressed():
        player_round+=1
        
        while len(round_data)-2<=player_round: #Freeplay - rounds are all randomised but get progressively worse
            round_data.append(round_balloon_data([5,6,6,5],[random.randint(player_round,5*player_round),random.randint(player_round,3*player_round),random.randint(player_round,6*player_round),random.randint(player_round,5*player_round)],[random.randint(4,10),random.randint(4,10),random.randint(4,10),random.randint(4,10)],[0,300,600,900]))
        new_round=True

    if speed_button.get_pressed():
        game_speed_option=(1+game_speed_option)%len(game_speeds)    

    #<MENU ZONE\>
    if new_round:
        round_data[player_round-1].deploy_bloons()
        player_money+=200+min(50*player_round,1000)
    new_round=False

    drawn_baloons=balloons[::-1] #monke targets by first, balloons draw by last
    for e in range(0,len(balloons)):
        
        balloons[e].update_time()
        balloons[e].update_pos(temp_track) 
        drawn_baloons[e].draw_balloon() #draw order and targeting order differ to allow for towers to target first 
        #makes monke target first without nasty overlapeffect from overtaking bloons
    
        if (balloons[e].x==-256 and balloons[e].y==-256) or balloons[e].popped: #MUST BE AT END OF LOOP
            if (balloons[e].x==-256 and balloons[e].y==-256):
                player_lives-=balloons[e].cumulative_hp() #if balloon reaches end of track, RBE(red bloon equivalent) is reduced from health  
            balloons[e]=0 #removes invalid balloons from the list

    balloons=[e for e in balloons if (e and not e.popped)]
    cursor_text_draw(cursor_message)
    previous_mouse_state=pygame.mouse.get_pressed()
    clock.tick(60*game_speeds[game_speed_option])
    for event in pygame.event.get():
       if event.type == QUIT:
           pygame.quit()
           sys.exit()
    pygame.display.update()
