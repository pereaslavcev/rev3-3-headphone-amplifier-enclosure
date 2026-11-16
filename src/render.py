import bpy, os, sys, math
from mathutils import Vector
OUT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MM=.001
bpy.ops.wm.open_mainfile(filepath=OUT+'/model/Корпус_Rev3_3.blend')
s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.use_denoising=True
s.render.use_persistent_data=True
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
cols={c.name[:2]:c for c in bpy.data.collections if ' • ' in c.name}

def vis(default=True, **changes):
    for k,c in cols.items():
        if k!='90':c.hide_render=not default
    for k,shown in changes.items():cols[k].hide_render=not shown

def cam(name,loc,target,ortho):
    o=bpy.data.objects.get(name)
    if not o:
        d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);s.collection.objects.link(o)
    o.location=tuple(v*MM for v in loc)
    o.rotation_euler=(Vector(tuple(v*MM for v in target))-o.location).to_track_quat('-Z','Y').to_euler()
    o.data.type='ORTHO';o.data.ortho_scale=ortho*MM;o.data.clip_start=.001;o.data.clip_end=20
    s.camera=o;return o

def render(path,w=1600,h=1200,samples=72):
    s.render.resolution_x=w;s.render.resolution_y=h;s.render.resolution_percentage=100;s.cycles.samples=samples
    s.render.filepath=path
    bpy.ops.render.render(write_still=True)
    print('RENDER_OK',path,flush=True)

mode=sys.argv[-1] if len(sys.argv)>1 else 'main'
os.makedirs(OUT+'/renders',exist_ok=True)
if mode=='main':
    vis(True,**{'10':False})
    cam('CAM • hero',(510,-650,430),(0,0,75),690)
    render(OUT+'/renders/01_Корпус_общий_вид.png',samples=80)
elif mode=='interior':
    vis(False,**{'01':True,'02':False,'03':True,'04':True,'05':False,'06':True,'07':True,'08':True,'09':True,'10':False,'11':True})
    # Transformer shrouds remain as spatial references; top decks and tubes removed.
    cam('CAM • interior',(390,-470,680),(0,0,28),610)
    render(OUT+'/renders/02_Внутренняя_компоновка.png',w=1400,h=1100,samples=56)
elif mode=='guard':
    vis(True)
    cam('CAM • guard',(510,-650,430),(0,0,90),720)
    render(OUT+'/renders/03_Защитная_решётка.png',w=1400,h=1100,samples=56)
elif mode=='rear':
    vis(True)
    cam('CAM • rear',(-480,600,350),(0,0,82),710)
    render(OUT+'/renders/04_Задняя_панель.png',w=1400,h=1100,samples=56)
elif mode=='verify':
    vd=OUT+'/verification-shots';os.makedirs(vd,exist_ok=True)
    vis(True,**{'10':False})
    for i in range(8):
        a=math.radians(i*45-90);x=570*math.cos(a);y=570*math.sin(a)
        cam('VERIFY orbit',(x,y,370),(0,0,75),690)
        render(f'{vd}/orbit_{i:02d}.png',800,800,12)
    cam('VERIFY top',(0,0,850),(0,0,40),600)
    render(f'{vd}/top.png',800,800,12)
    # Chassis close inspection, five angles.
    for i in range(5):
        a=math.radians(i*72-90)
        cam('VERIFY chassis',(460*math.cos(a),460*math.sin(a),220),(0,-15,45),530)
        render(f'{vd}/chassis_{i:02d}.png',800,800,12)
    # Audio PCB close inspection, service configuration.
    vis(False,**{'01':True,'03':True,'07':True,'08':True,'09':True})
    for i in range(5):
        a=math.radians(i*72-90)
        cam('VERIFY audio',(35+270*math.cos(a),-60+270*math.sin(a),280),(35,-60,43),345)
        render(f'{vd}/audio_{i:02d}.png',800,800,12)
    # T1 close inspection, full exterior without guard.
    vis(True,**{'10':False})
    for i in range(5):
        a=math.radians(i*72-90)
        cam('VERIFY T1',(15+220*math.cos(a),112+220*math.sin(a),245),(15,112,112),210)
        render(f'{vd}/t1_{i:02d}.png',800,800,12)
print('DONE',mode)
