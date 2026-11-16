import bpy, math, os, json
from mathutils import Vector
from math import sin, cos, pi

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(OUT, 'model'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'renders'), exist_ok=True)
MM = 0.001

def m(v): return v * MM

def clean():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):
        if c.name != 'Collection': bpy.data.collections.remove(c)
    base = bpy.data.collections.get('Collection')
    base.name = '00 • Сборка'

clean()
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'MILLIMETERS'
scene.unit_settings.scale_length = 1.0
scene['Проект'] = 'Rev.3.3 Curved — компоновочная модель корпуса'
scene['Шасси_мм'] = '450 × 360 × 78; с боковыми накладками ширина 474'
scene['Audio_PCB_мм'] = '271 × 203 × 2'
scene['PSU_PCB_мм'] = '130 × 155 × 2'
scene['Допущение_T1_мм'] = 'Ø140 × 80 — уточнить у изготовителя'
scene['Допущение_T2_мм'] = '92 × 82 × 88 каждый — уточнить у изготовителя'
scene['Статус'] = 'Компоновочная концепция; не производственный чертёж'

COLS = {}
for name in ['01 • Шасси', '02 • Верхняя дека', '03 • Audio PCB', '04 • PSU PCB',
             '05 • Лампы', '06 • Трансформаторы и дроссель', '07 • TL783 и радиаторы',
             '08 • Панельные элементы', '09 • Проводка', '10 • Защитная решётка',
             '11 • Крепёж', '90 • Сцена']:
    c = bpy.data.collections.new(name); scene.collection.children.link(c); COLS[name[:2]] = c
CUR = COLS['01']

def use(key):
    global CUR
    CUR = COLS[key]

def move(obj):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    CUR.objects.link(obj)
    return obj

def material(name, color, metal=0, rough=.4, transmission=0, emission=None):
    mat = bpy.data.materials.new(name); mat.diffuse_color = (*color, 1); mat.use_nodes = True
    p = mat.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    p.inputs['Transmission Weight'].default_value = transmission
    if transmission: p.inputs['IOR'].default_value = 1.46
    if emission:
        p.inputs['Emission Color'].default_value = (*emission[0], 1)
        p.inputs['Emission Strength'].default_value = emission[1]
    return mat

BLACK = material('Анодированный алюминий • графит', (.012,.016,.020), .78,.29)
DECK = material('Верхняя дека • тёмный титан', (.035,.043,.050), .72,.32)
STEEL = material('Нержавеющая сталь', (.52,.57,.60), .9,.23)
ALU = material('Алюминий • satin', (.55,.58,.60), .82,.3)
GOLD = material('Латунь / позолота', (.58,.35,.10), .78,.28)
COPPER = material('Медная обмотка', (.55,.19,.065), .82,.25)
PCB = material('FR-4 • тёмно-зелёная', (.018,.16,.095), .15,.38)
PCBPSU = material('FR-4 PSU • синяя', (.025,.09,.16), .12,.38)
SOLDER = material('Пайка', (.45,.49,.50), .85,.24)
CERAMIC = material('Керамика панелек', (.73,.69,.57), .05,.48)
BAKELITE = material('Чёрный бакелит', (.018,.015,.013), .05,.3)
GLASS = material('Стекло ламп • слегка дымчатое', (.50,.61,.55), .0,.055,.97)
PLATE = material('Аноды • графит', (.065,.07,.073), .65,.38)
HEATER = material('Накал', (.7,.12,.015), .15,.32, emission=((1,.16,.018),2.2))
RED = material('Провод • красный', (.48,.025,.018), .05,.4)
YELLOW = material('Провод • жёлтый', (.65,.39,.025), .05,.4)
WIREBLACK = material('Провод • чёрный', (.012,.014,.016), .05,.38)
BLUEWIRE = material('Провод • синий', (.025,.16,.42), .05,.4)
WHITE = material('Шелкография', (.78,.80,.76), .05,.5)
LABEL = material('Таблички • тёмная латунь', (.24,.16,.065), .72,.32)
CAPMAT = material('Электролиты • синие', (.025,.055,.105), .25,.32)
RESMAT = material('Резисторы • beige', (.55,.43,.25), .05,.5)
WOOD = material('Орех • боковые накладки', (.18,.065,.025), .05,.34)
# Procedural end-to-end walnut grain.
nt = WOOD.node_tree; p = nt.nodes.get('Principled BSDF')
tex = nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=5; tex.inputs['Detail'].default_value=3
coord = nt.nodes.new('ShaderNodeTexCoord'); mapping = nt.nodes.new('ShaderNodeVectorMath'); mapping.operation='MULTIPLY'; mapping.inputs[1].default_value=(5,1,32)
nt.links.new(coord.outputs['Generated'],mapping.inputs[0]); nt.links.new(mapping.outputs[0],tex.inputs['Vector'])
ramp=nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position=.22; ramp.color_ramp.elements[0].color=(.045,.012,.004,1); ramp.color_ramp.elements[1].position=.8; ramp.color_ramp.elements[1].color=(.30,.12,.045,1)
nt.links.new(tex.outputs['Fac'],ramp.inputs[0]); nt.links.new(ramp.outputs[0],p.inputs['Base Color'])
RUBBER = material('Резина', (.012,.014,.016), .0,.72)
FLOOR = material('Фон • тёплый серый', (.16,.175,.19), .0,.78)

def bevel(obj, amount=.6, segments=3):
    if amount:
        mod=obj.modifiers.new('Скругления кромок','BEVEL'); mod.width=m(amount); mod.segments=segments
    return obj

def box(name, loc, dims, mat, bevel_mm=.5, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=tuple(m(v) for v in loc))
    o=move(bpy.context.object); o.name=name; o.dimensions=tuple(m(v) for v in dims)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rot: o.rotation_euler=tuple(math.radians(v) for v in rot)
    if mat: o.data.materials.append(mat)
    bevel(o,bevel_mm)
    return o

def cyl(name, loc, radius, depth, mat, vertices=64, rot=None, bevel_mm=.35):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=m(radius), depth=m(depth), location=tuple(m(v) for v in loc))
    o=move(bpy.context.object); o.name=name
    if rot: o.rotation_euler=tuple(math.radians(v) for v in rot)
    if mat: o.data.materials.append(mat)
    bevel(o,bevel_mm,2)
    for p in o.data.polygons: p.use_smooth=True
    return o

def sphere(name, loc, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=tuple(m(v) for v in loc))
    o=move(bpy.context.object); o.name=name; o.scale=tuple(m(v) for v in scale)
    if mat:o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    return o

def torus(name, loc, major, minor, mat, rot=None, seg=80):
    bpy.ops.mesh.primitive_torus_add(major_segments=seg,minor_segments=12,location=tuple(m(v) for v in loc),major_radius=m(major),minor_radius=m(minor))
    o=move(bpy.context.object);o.name=name
    if rot:o.rotation_euler=tuple(math.radians(v) for v in rot)
    o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    return o

def curve(name, pts, radius, mat, cyclic=False, smooth=True):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=16;cu.bevel_depth=m(radius);cu.bevel_resolution=3
    sp=cu.splines.new('BEZIER' if smooth else 'POLY')
    if smooth:
        sp.bezier_points.add(len(pts)-1)
        for p,co in zip(sp.bezier_points,pts):p.co=tuple(m(v) for v in co);p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    else:
        sp.points.add(len(pts)-1)
        for p,co in zip(sp.points,pts):p.co=(*tuple(m(v) for v in co),1)
    sp.use_cyclic_u=cyclic
    o=bpy.data.objects.new(name,cu);CUR.objects.link(o);cu.materials.append(mat);return o

def text(name, body, loc, size, mat, rot=(90,0,0), align='CENTER', extrude=.03):
    cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.size=m(size);cu.align_x=align;cu.align_y='CENTER';cu.extrude=m(extrude);cu.bevel_depth=m(.01)
    o=bpy.data.objects.new(name,cu);CUR.objects.link(o);o.location=tuple(m(v) for v in loc);o.rotation_euler=tuple(math.radians(v) for v in rot);cu.materials.append(mat);return o

def difference(obj, cutter):
    bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Вырез','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)

def screw(name, x,y,z, axis='Z', radius=2.7):
    rot=None if axis=='Z' else (90,0,0)
    o=cyl(name,(x,y,z),radius,2.2,STEEL,32,rot,0.2)
    if axis=='Z':
        box(name+' • шлиц',(x,y,z+1.15),(2.8,.55,.25),BAKELITE,.05)
    return o

def lathe(name, profile, loc, mat, segments=72):
    verts=[];faces=[]
    for r,z in profile:
        for i in range(segments):
            a=2*pi*i/segments;verts.append((m(loc[0]+r*cos(a)),m(loc[1]+r*sin(a)),m(loc[2]+z)))
    for j in range(len(profile)-1):
        for i in range(segments):
            a=j*segments+i;b=j*segments+(i+1)%segments;c=(j+1)*segments+(i+1)%segments;d=(j+1)*segments+i
            faces.append((a,b,c,d))
    faces.append(tuple(range(segments-1,-1,-1)));faces.append(tuple((len(profile)-1)*segments+i for i in range(segments)))
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);CUR.objects.link(o);me.materials.append(mat)
    for p in me.polygons:p.use_smooth=True
    return o

# ---------- chassis ----------
use('01')
base=box('Шасси • днище 2 мм',(0,0,1.5),(450,360,3),BLACK,1)
front=box('Передняя панель 3 мм',(0,-178.5,40),(450,3,78),BLACK,0)
rear=box('Задняя панель 3 мм',(0,178.5,40),(450,3,78),BLACK,0)
left=box('Левая стенка',(-223.5,0,40),(3,354,78),BLACK,.8)
right=box('Правая стенка',(223.5,0,40),(3,354,78),BLACK,.8)
for x in (-231,231):
    box('Боковая накладка • орех',(x,0,39),(12,336,70),WOOD,5)
for x in (-180,180):
    for y in (-132,132):
        cyl('Опора • резина',(x,y,-6),14,12,RUBBER,48,bevel_mm=1)
        cyl('Опора • шайба',(x,y,.2),10,2,STEEL,32)
# Front openings.
for x,r in [(-135,12.2),(-45,5.2),(140,5.2),(45,2.6)]:
    cut=cyl('CUT',(x,-178.5,40),r,12,None,48,(90,0,0),0);difference(front,cut)
# Rear D-size, IEC, switch and fuse openings.
for x in (100,145):
    cut=cyl('CUT',(x,178.5,42),12.2,12,None,48,(90,0,0),0);difference(rear,cut)
for loc,dims in [((-155,178.5,39),(31,12,23)),((-92,178.5,40),(23,12,31))]:
    cut=box('CUT',loc,dims,None,0);difference(rear,cut)
cut=cyl('CUT',(-38,178.5,40),8,12,None,48,(90,0,0),0);difference(rear,cut)
bevel(front,.8);bevel(rear,.8)

use('02')
deck=box('Верхняя дека 2 мм',(0,0,77),(444,354,2),DECK,0)
SOCKETS=[(-60,-5,'6SN7'),(35,-5,'6AS7 L'),(130,-5,'6AS7 R'),(-180,45,'GZ34')]
for x,y,label in SOCKETS:
    cut=cyl('CUT • отверстие лампы',(x,y,77),22,12,None,64,bevel_mm=0);difference(deck,cut)
    torus('Защитное кольцо отверстия '+label,(x,y,78.2),22.5,1.0,STEEL)
# Vent slots on both front sides.
for x in (-199,199):
    for y in (-125,-108,-91,-74,-57):
        cut=box('CUT • вентиляция',(x,y,77),(3.2,11,12),None,0);difference(deck,cut)
for x in (-209,209):
    for y in (-161,161):
        cut=cyl('CUT',(x,y,77),2,10,None,24,bevel_mm=0);difference(deck,cut);screw('Винт деки M3',x,y,78.3)
bevel(deck,.6)

# ---------- PCB helpers ----------
def pcb_board(name, center, dims, mat, key):
    use(key);x,y,z=center;w,d,h=dims
    board=box(name,(x,y,z),(w,d,h),mat,1.5)
    for dx in (-w/2+8,w/2-8):
        for dy in (-d/2+8,d/2-8):
            cyl(name+' • стойка M3',(x+dx,y+dy,z/2),3.2,z-3,STEEL,24)
            torus(name+' • монтажное кольцо',(x+dx,y+dy,z+h/2+.15),3.1,.65,GOLD,seg=32)
            cyl(name+' • отверстие',(x+dx,y+dy,z+h/2+.25),1.6,.4,BAKELITE,24,bevel_mm=0)
    return board

def capacitor(name,x,y,z,r=11,h=31):
    cyl(name,(x,y,z+h/2),r,h,CAPMAT,48,bevel_mm=.7)
    cyl(name+' • верх',(x,y,z+h+.15),r*.88,.5,ALU,48,bevel_mm=.1)
    box(name+' • вентиль',(x,y,z+h+.45),(r*.8,.7,.2),BAKELITE,.05)
    box(name+' • полоса',(x-r*.72,y,z+h*.52),(.8,r*.45,h*.8),WHITE,.1)

def resistor(name,x,y,z,axis='X'):
    rot=(0,90,0) if axis=='X' else (90,0,0)
    cyl(name,(x,y,z+3),2.2,10,RESMAT,24,rot,.3)
    if axis=='X':
        curve(name+' • выводы',[(x-8,y,z),(x-5,y,z+3),(x+5,y,z+3),(x+8,y,z)],.35,SOLDER,smooth=False)
    else:
        curve(name+' • выводы',[(x,y-8,z),(x,y-5,z+3),(x,y+5,z+3),(x,y+8,z)],.35,SOLDER,smooth=False)

def terminal(name,x,y,z,ways=3):
    box(name,(x,y,z+5),(ways*6,10,10),material(name+' зелёный',(.03,.24,.10),.05,.45),.5)
    for i in range(ways):cyl(name+' • винт',(x+(i-(ways-1)/2)*6,y,z+10.4),1.5,1,STEEL,20)

audio=pcb_board('Audio PCB • 271×203', (35,-60,40),(271,203,2),PCB,'03')
use('03')
# Local component placement follows assembly drawing; tubes are on the rear row.
for i,(x,y,r,h) in enumerate([(-70,-137,13,29),(5,-137,11,28),(48,-137,11,28),(97,-137,13,29),(145,-120,10,25),(175,-120,10,25)]):
    capacitor('Audio C'+str(i+1),x,y,41,r,h)
for i,(x,y) in enumerate([(-75,-70),(-35,-70),(10,-75),(60,-70),(105,-70),(150,-70),(-75,-25),(150,-25)]):
    resistor('Audio R'+str(i+1),x,y,41,'X' if i%2==0 else 'Y')
terminal('Audio J1 • вход',-65,-108,41,4);terminal('Audio J8/J18 • B+',80,-102,41,2)
for x,y,label in SOCKETS[:3]:
    cyl('Belton VT8 • '+label,(x,y,51),17,20,CERAMIC,64,bevel_mm=.8)
    cyl('Октальное основание • '+label,(x,y,62),14,4,BAKELITE,48)
    for i in range(8):
        a=2*pi*i/8;cyl('Контакт '+label,(x+8.6*cos(a),y+8.6*sin(a),62),1,3,GOLD,16)
# Silkscreen visible in service view.
text('Audio PCB • маркировка','AUDIO  Rev.3.3  /  271 × 203 mm',(35,-143,41.3),4.2,WHITE,rot=(0,0,0))

psu=pcb_board('PSU PCB • 130×155', (-140,90,20),(155,130,2),PCBPSU,'04')
use('04')
for i,(x,y,r,h) in enumerate([(-185,105,13,36),(-115,110,13,36),(-120,65,9,25)]):capacitor('PSU C'+str(i+1),x,y,21,r,h)
for i,(x,y) in enumerate([(-180,135),(-145,135),(-95,85)]):resistor('PSU R'+str(i+1),x,y,21)
terminal('PSU J1 • HV',-95,140,21,3);terminal('PSU J3 • выход',-150,145,21,4)
x,y,_=SOCKETS[3]
cyl('Belton VT8 • GZ34',(x,y,33),17,22,CERAMIC,64,bevel_mm=.8)
cyl('Октальное основание • GZ34',(x,y,46),14,4,BAKELITE,48)
text('PSU PCB • маркировка','GZ34  CLC  PSU',(-140,92,21.3),4.5,WHITE,rot=(0,0,0))

# ---------- TL783 heatsinks: two per side, electrically isolated ----------
use('07')
for side in (-1,1):
    for idx,y in enumerate((-92,-35)):
        x=side*215
        box('SK409 • основание',(x,y,39),(3,45,50.8),ALU,.45)
        for j in range(11):
            yy=y-20+j*4
            box('SK409 • ребро',(x-side*6.2,yy,39),(12.4,1.15,50.8),ALU,.22)
        box('TL783C • TO-220',(x-side*4,y,39),(3.2,10,15),BAKELITE,.5)
        box('Изолирующая прокладка',(x-side*2.1,y,39),(.6,13,19),CERAMIC,.15)
        cyl('Изолирующая втулка M3',(x-side*5,y,42),2,2,STEEL,24,(0,90,0),.15)
        for dy in (-4,0,4):curve('Вывод TL783',[(x-side*5,y+dy,34),(x-side*12,y+dy,29),(x-side*18,y+dy,29)],.45,SOLDER)

# ---------- tubes ----------
def tube(label,x,y,base_z,height,radius,kind):
    use('05')
    cyl(label+' • октальный цоколь',(x,y,base_z+7),16,14,BAKELITE,64,bevel_mm=1)
    torus(label+' • кромка цоколя',(x,y,base_z+13.5),15.2,.8,STEEL)
    # Glass envelope, lathed closed profile.
    z0=base_z+12;H=height-12;r=radius
    profile=[(r*.70,0),(r*.92,3),(r,8),(r,H*.68),(r*.98,H*.80),(r*.88,H*.90),(r*.58,H*.97),(r*.16,H),(0,H+1)]
    lathe(label+' • стеклянный баллон',profile,(x,y,z0),GLASS)
    cyl(label+' • нижний экран',(x,y,z0+6),r*.68,2,PLATE,48)
    n=2 if kind=='6AS7' else 1
    for k in range(n):
        dx=(k-(n-1)/2)*r*.75
        box(label+' • анод '+str(k+1),(x+dx,y,z0+H*.48),(r*.60,r*.72,H*.48),PLATE,1)
        for zz in (-1,1):box(label+' • ребро анода',(x+dx,y+zz*r*.39,z0+H*.48),(r*.68,.7,H*.5),PLATE,.2)
    for dx in (-r*.58,r*.58):cyl(label+' • стойка',(x+dx,y,z0+H*.47),.65,H*.72,STEEL,16)
    pts=[]
    for i in range(90):
        t=i/89;pts.append((x+r*.32*cos(t*8*pi),y+r*.32*sin(t*8*pi),z0+8+t*H*.60))
    curve(label+' • спираль накала',pts,.32,HEATER,smooth=False)
    cyl(label+' • геттер',(x,y,z0+H*.88),r*.63,.7,STEEL,48)
    text(label+' • маркировка',kind,(x,y-16.1,base_z+7),4.2,WHITE,rot=(90,0,0))

tube('V1',-60,-5,65,91,16,'6SN7')
tube('V2L',35,-5,65,112,20,'6AS7')
tube('V2R',130,-5,65,112,20,'6AS7')
tube('V3',-180,45,48,108,17,'GZ34')

# ---------- magnetics ----------
use('06')
# T1: assumed toroid, copper winding exposed with steel clamp.
tx,ty=15,112
cyl('T1 • демпфирующая прокладка',(tx,ty,80),59,4,RUBBER,64)
torus('T1 • магнитопровод',(tx,ty,112),45,20,PLATE,seg=96)
for i in range(72):
    a=2*pi*i/72;pts=[]
    for j in range(33):
        b=2*pi*j/32;rr=45+21*cos(b);pts.append((tx+rr*cos(a),ty+rr*sin(a),112+21*sin(b)))
    curve('T1 • медный виток %02d'%i,pts,1.25,COPPER,cyclic=True,smooth=False)
cyl('T1 • центральная шайба',(tx,ty,135),27,3,STEEL,64)
cyl('T1 • втулка',(tx,ty,112),9,48,STEEL,48)
screw('T1 • центральный винт',tx,ty,137,radius=5)
box('T1 • табличка',(tx,ty-37,134.8),(52,17,1.4),LABEL,1)
text('T1 • обозначение','T1  /  250 VA',(tx,ty-37,135.7),4.2,WHITE,rot=(0,0,0))
# Output transformers: drawn-steel shrouds, mounting flanges.
for x,label in [(-132,'T2L'),(153,'T2R')]:
    y=113
    box(label+' • монтажный фланец',(x,y,80),(102,92,3),STEEL,1.2)
    box(label+' • кожух',(x,y,123),(92,82,86),BLACK,5)
    box(label+' • верхняя крышка',(x,y,166),(89,79,2),DECK,3)
    for dx in (-44,44):
        for dy in (-39,39):screw(label+' • винт M4',x+dx,y+dy,82.2,radius=3.3)
    box(label+' • табличка',(x,y-41.3,128),(58,1,19),LABEL,1)
    text(label+' • обозначение',label+'  1 kΩ',(x,y-42,128),5.2,WHITE)
# Choke below deck.
box('L1 • Hammond 193L',(142,105,32),(62,48,48),BLACK,3)
for x in (117,167):box('L1 • фланец',(x,105,17),(12,58,3),STEEL,.8)
text('L1 • маркировка','193L',(142,80.7,34),5,WHITE)

# ---------- panel hardware ----------
use('08')
# ALPS body and volume knob.
box('ALPS RK27 • корпус',(140,-158,40),(28,30,28),STEEL,1.5)
cyl('ALPS RK27 • вал Ø6',(140,-184,40),3,30,STEEL,32,(90,0,0))
cyl('Ручка громкости • aluminium',(140,-198,40),24,24,ALU,96,(90,0,0),1.4)
cyl('Ручка громкости • торец',(140,-210.4,40),21.8,1.2,BLACK,96,(90,0,0),.4)
box('Ручка громкости • метка',(140,-211.2,52),(1.4,.5,8),WHITE,.3)
text('Надпись VOLUME','VOLUME',(140,-180.3,70),4.4,WHITE)
# Headphone jack.
cyl('Neutrik NJ3FP6C • корпус',(-135,-171,40),12,23,BAKELITE,64,(90,0,0),.5)
cyl('Neutrik NJ3FP6C • гайка',(-135,-181.5,40),15,3,STEEL,6,(90,0,0),.4)
cyl('Neutrik NJ3FP6C • лицевое кольцо',(-135,-183.4,40),10.7,1.5,GOLD,64,(90,0,0),.2)
cyl('Neutrik NJ3FP6C • отверстие',(-135,-184.4,40),5.2,1.4,BAKELITE,64,(90,0,0),.1)
text('Надпись PHONES','PHONES  6.35 mm',(-135,-180.3,70),4.4,WHITE)
# Impedance selector.
cyl('C&K A20415 • корпус',(-45,-169,40),11,18,BAKELITE,48,(90,0,0))
cyl('Селектор импеданса • ручка',(-45,-190,40),15,20,BLACK,64,(90,0,0),1)
box('Селектор • метка',(-45,-200.5,48),(1,.6,6),WHITE,.2)
text('Надпись IMPEDANCE','IMPEDANCE  Ω',(-45,-180.3,69),3.7,WHITE)
text('Надпись диапазона','16   32   150   600',(-45,-180.3,11),3.3,WHITE)
# Warm power indicator.
cyl('LED • державка',(45,-181,40),4,3,GOLD,48,(90,0,0))
LED=material('LED • amber',(.9,.25,.025),.1,.2,emission=((1,.22,.02),3))
sphere('LED • линза',(45,-183,40),(2.4,1.4,2.4),LED)
text('Фирменная маркировка','REV. 3.3',(5,-180.3,59),6.0,WHITE)
text('Описание','OCTAL  HEADPHONE  AMPLIFIER',(5,-180.3,48),3.2,WHITE)
# Rear connectors and lettering (text faces +Y).
for x,num in [(100,'R'),(145,'L')]:
    cyl('Neutrik RCA '+num,(x,174,42),12,18,BAKELITE,64,(90,0,0))
    cyl('Neutrik RCA '+num+' • гайка',(x,181,42),15,3,STEEL,6,(90,0,0),.3)
    ringmat=RED if num=='R' else WHITE
    cyl('Neutrik RCA '+num+' • кольцо',(x,183,42),10.5,2,ringmat,64,(90,0,0))
    cyl('Neutrik RCA '+num+' • контакт',(x,184.5,42),4,2,GOLD,48,(90,0,0))
    text('RCA '+num+' label','INPUT '+num,(x,180.2,64),4.2,WHITE,rot=(90,0,180))
box('Bulgin IEC C14',(-155,181,39),(36,10,28),BAKELITE,2)
for x in (-163,-155,-147):box('IEC • контакт',(x,186.5,39),(2,3,7),GOLD,.2)
box('DPST • выключатель',(-92,182,40),(24,12,32),BAKELITE,2)
box('DPST • клавиша',(-92,189,40),(18,4,25),RED,2)
cyl('Держатель предохранителя',(-38,183,40),10,10,BAKELITE,64,(90,0,0))
box('Предохранитель • шлиц',(-38,188.5,40),(8,1,1.4),STEEL,.2)
text('Задняя маркировка','REV.3.3  /  CLASS I',(15,180.2,19),3.8,WHITE,rot=(90,0,180))
# PE chassis stud inside rear.
cyl('PE • шпилька M4',(-195,160,10),2,14,STEEL,32)
torus('PE • зазубренная шайба',(-195,160,5),4,.8,GOLD)

# ---------- internal harness ----------
use('09')
for i,(x,mat) in enumerate([(-8,RED),(0,YELLOW),(8,WIREBLACK)]):
    curve('T1 • вывод '+str(i),[(15+x,72,111),(15+x,55,95),(-10+x,35,70),(-70,40+i*4,35),(-90,75+i*4,29)],1.5,mat)
for x0,label in [(-132,'L'),(153,'R')]:
    for i,mat in enumerate((RED,BLUEWIRE)):
        curve('T2'+label+' • первичная '+str(i),[(x0+i*6,75,92),(x0+i*6,62,70),(x0*.75,35,55),(35+i*10,5,48)],1.25,mat)
for side in (-1,1):
    for y in (-92,-35):
        curve('TL783 • катодная связь',[(side*198,y,30),(side*175,y-8,30),(side*145,-48,43)],1.1,RED)
curve('Защитная земля PE',[(-195,160,12),(-190,145,12),(-170,150,7)],2.0,YELLOW)

# ---------- removable safety guard ----------
use('10')
# Rounded-rectangle top perimeter and four posts; thin stainless rods.
zlo,zhi=80,197
for x in (-211,211):
    for y in (-163,163):
        cyl('Решётка • стойка',(x,y,(zlo+zhi)/2),2.0,zhi-zlo,STEEL,24)
        cyl('Решётка • опора',(x,y,81),5,4,STEEL,32)
        screw('Решётка • крепёж',x,y,83.5,radius=2.8)
# Horizontal side rails at top and mid-height.
for z in (126,197):
    curve('Решётка • продольная рамка',[(-211,-163,z),(-211,163,z),(211,163,z),(211,-163,z)],2.0,STEEL,cyclic=True,smooth=False)
# Fine vertical rods, sides and front/back.
for x in range(-180,181,30):
    for y in (-163,163):cyl('Решётка • вертикальный прут',(x,y,161.5),1.0,71,STEEL,16)
for y in range(-133,134,30):
    for x in (-211,211):cyl('Решётка • вертикальный прут',(x,y,161.5),1.0,71,STEEL,16)
# Top grid, sufficient finger protection while retaining visibility.
for x in range(-180,181,30):cyl('Решётка • верх X',(x,0,197),1.1,326,STEEL,16,(90,0,0),0)
for y in range(-133,134,30):cyl('Решётка • верх Y',(0,y,197),1.1,422,STEEL,16,(0,90,0),0)

# ---------- small fastener details ----------
use('11')
for x in (-213,213):
    for z in (16,64):
        cyl('Крепёж боковой накладки',(x,-168.8,z),3,2,STEEL,32,(90,0,0),.2)
for x in (-202,202):
    for z in (14,66):screw('Передний винт',x,-180.3,z,axis='Y',radius=2.4)

# ---------- studio ----------
use('90')
box('Студийный пол',(0,0,-15),(5000,5000,4),FLOOR,0)
world=bpy.data.worlds.new('Студийный мир');scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.32,.37,.43,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.30

def light(name,loc,power,size,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=m(size);data.color=color
    o=bpy.data.objects.new(name,data);CUR.objects.link(o);o.location=tuple(m(v) for v in loc);o.rotation_euler=(Vector((0,0,m(70)))-o.location).to_track_quat('-Z','Y').to_euler();return o
light('Key • large softbox',(-300,-350,600),55,420,(1,.88,.74))
light('Fill • cool',(420,-100,330),32,320,(.72,.84,1))
light('Rim • rear',(0,400,500),65,300,(1,.94,.84))
# A sun lamp guarantees robust CPU Cycles lighting.
data=bpy.data.lights.new('Sun','SUN');data.energy=.65;data.angle=.22
sun=bpy.data.objects.new('Sun',data);CUR.objects.link(sun);sun.rotation_euler=(math.radians(24),math.radians(-28),math.radians(-28))

def camera(name,loc,target,ortho):
    data=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,data);CUR.objects.link(o);o.location=tuple(m(v) for v in loc);o.rotation_euler=(Vector(tuple(m(v) for v in target))-o.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=m(ortho);data.clip_start=.001;data.clip_end=20;return o
cam=camera('CAM • hero',(510,-650,430),(0,0,75),690);scene.camera=cam
camera('CAM • interior',(440,-510,650),(0,0,30),650)
camera('CAM • rear',(-480,600,350),(0,0,72),670)
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=64
scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX'
scene.view_settings.exposure=-1.1
scene.render.filepath=OUT+'/renders/01_Корпус_общий_вид.png'
# Human-friendly viewport.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.clip_end=20
            area.spaces.active.region_3d.view_distance=.75

# Keep an editable parameter note inside the blend.
notes=bpy.data.texts.new('КОМПОНОВОЧНЫЕ ДОПУЩЕНИЯ')
notes.write('REV.3.3 CURVED — КОМПОНОВОЧНАЯ МОДЕЛЬ\n\nПодтверждено по исходным платам: Audio 271×203×2 мм; PSU 130×155×2 мм; крепёж M3.\nШасси: 450×360×78 мм; боковые накладки увеличивают ширину до 474 мм.\nT1 условно Ø140×80 мм; каждый T2 условно 92×82×88 мм. Перед механическим производством заменить фактическими габаритами.\nДроссель Hammond 193L; 4 радиатора SK409 50,8 для внешних TL783C; пластины TO-220 изолированы.\nЛампы и разъёмы — внешние компоновочные оболочки, не точные CAD производителей; компоненты на платах упрощены.\nЗащитная решётка съёмная. Электрические зазоры, вентиляция, безопасные расстояния и крепления требуют инженерной проверки.\nНе производственный чертёж.\n')

# Save editable, self-contained source before mesh conversion for GLB.
blend_path=OUT+'/model/Корпус_Rev3_3.blend'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
# Convert curves/text only in the in-memory export copy.
bpy.ops.object.select_all(action='DESELECT')
convert=[o for o in scene.objects if o.type in {'CURVE','FONT'}]
for o in convert:o.select_set(True)
if convert:
    bpy.context.view_layer.objects.active=convert[0]
    bpy.ops.object.convert(target='MESH')
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
    if any(c != COLS['90'] for c in o.users_collection): o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT+'/model/Корпус_Rev3_3.glb',export_format='GLB',export_apply=True,export_yup=True,export_materials='EXPORT',export_cameras=False,export_lights=False,use_selection=True)
print('MODEL_OK',blend_path)
print('OBJECTS',len(scene.objects))
print('GLB_OK',OUT+'/model/Корпус_Rev3_3.glb')
