from PIL import Image, ImageDraw, ImageFilter, ImageFont
import time
import os
import psutil


class FakeDisplay:
    width = 240
    height = 320
    rotation = 90

    def __init__(self, w=240, h=320, r=90):
        self.width = w
        self.height = h
        self.rotation = r


disp = FakeDisplay(r=90)
if disp.rotation % 180 == 90:
    height = disp.width   # we swap height/width to rotate it to landscape!
    width = disp.height
else:
    width = disp.width   # we swap height/width to rotate it to landscape!
    height = disp.height

# split the layout into top/middle/footer (footer can be a scrollable)
# book the areas into top/height attributes
fh = 25  # footer height
tt = 0  # top top
tw = width  # top width
th = round((height - fh) / 2)  # top height
mt = th + 1  # middle top
mh = th  # middle height, same as top height
mw = width  # middle width
ft = th + mh + 1  # footer top, just below middle
fw = width  # footer width

tx = (0, tt)
ty = (tw, th)
mx = (0, mt)
my = (mw, mt + mh)
fx = (0, ft)
fy = (fw, ft + fh)

print("top: x/y => (" + str(0) + "," + str(tt) + "), ("+str(width)+","+str(th)+")")

c_blck = (19, 19, 19)
c_dblu = (19, 39, 80)
c_gold = (217, 175, 44)
c_pred = (194, 78, 47)


image = Image.new('RGB', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# draw top
draw.rectangle(tx + ty, fill=c_dblu)
draw.rectangle(mx + my, fill=c_gold)
draw.rectangle(fx + fy, fill=c_pred)

# stat bars on top, horizontal bars

# cpu % 100
# mem used/free
# i/o read
# i/o write
# net in
# net out


class Stats:
    infdiff = {}

    def __init__(self):
        pass

    def getStats(self):
        stats = []
        stats.append((
            psutil.cpu_percent(),
            psutil.cpu_freq().current,
            psutil.cpu_freq().max,
            str(psutil.cpu_percent()) + "% " +
            str(psutil.cpu_freq().current) +
            ("/" + str(psutil.cpu_freq().max) if psutil.cpu_freq().max > 0 else "") + "Ghz"))

        mem = psutil.virtual_memory()
        mm = round(mem[3]/1024/1024/1024, 2)
        mt = round(mem[0]/1024/1024/1024, 2)
        stats.append((
            mem[2],
            mm,
            mt,
            str(mem[2]) + "%, " + str(mm) + "/" + str(mt) + "GB"))

        kdisks = ['/']
        for kd in kdisks:
            dv = psutil.disk_usage(kd)
            gu = round(dv.used/1024/1024/1024, 2)
            gt = round(dv.total/1024/1024/1024, 2)
            stats.append((
                dv.percent,
                gu,
                gt,
                kd + ": " + str(dv.percent) +
                "%, " + str(gu) + "/" + str(gt) + "GB"))

        kinfs = ['ens', 'eth']
        netio = psutil.net_io_counters(pernic=True)
        netis = psutil.net_if_stats()
        netus = {}
        for inf, iv in netis.items():
            for kinf in kinfs:
                if inf.startswith(kinf):
                    netus[inf] = [iv.isup]
                    if inf in netio:
                        bs = netio[inf].bytes_sent
                        br = netio[inf].bytes_recv
                        bp = 0
                        bmax = 0
                        if inf in self.infdiff:
                            (bt, bmax) = self.infdiff[inf]
                            bp = round(((bs + br) - bt)/bmax*100, 4)
                            # print("diff:" + str(((bs + br) - bt)) +
                            #      "/" + str(bmax))
                        else:
                            bmax = netis[inf].speed
                            if bmax > 0:
                                bmax = bmax*1024*1024  # supposed to be MB, take it down to bytes
                        # store current total, plus max
                        self.infdiff[inf] = ((bs + br), bmax)
                        # print(str(self.infdiff[inf]))
                        stats.append((
                            bp,
                            bs,
                            br,
                            inf + ": " + str(bp) + "%, " +
                            str(round(bs/1024/1024, 2)) + "MB, " + str(round(br/1024/1024, 2)) + "MB"))
        return stats  # [(0,1,2,txt),...]


s = Stats()
while True:
    ss = s.getStats()
    for sss in ss:
        print(sss)
    print('')
    time.sleep(1)


fontsize = 18

font = ImageFont.truetype('./fonts/vt323.ttf', fontsize)
# (font_width, font_height) = font.getsize(text)

mwidth = width

s = Stats()
ss = s.getStats()
sx = 0
sy = tt
tpadding = 0  # even number, padding top and bottom of text
tpad = 0
if tpadding > 0:
    tpad = tpadding / 2
bthickness = 4

for sss in ss:
    text = sss[3]
    p1 = sss[0]
    p2 = sss[1]
    p3 = sss[2]
    if isinstance(p1, bool):
        draw.line((sx, sy, mwidth, sy), width=bthickness, fill=c_pred)
    elif isinstance(p1, int) or isinstance(p1, float):
        print("line")
        # this is a percentage value, we'll draw graph lines relative to 100%
        # draw 100%
        draw.line((sx, sy, mwidth, sy), width=bthickness, fill=c_blck)
        # draw p1 % of mwidth
        pwidth = 0
        if p1 > 0:
            pwidth = round((p1 / 100 * mwidth), 0)
        draw.line((sx, sy, pwidth, sy), width=bthickness, fill=c_pred)

    # draw total/max/limit
    # c_blck, c_dblu, c_gold, c_pred
    # draw.line((sx, sy, mwidth, sy), width=10, fill=c_blck)

    draw.text((sx, sy + tpad), text, font=font, fill=c_gold)
    sy += fontsize + tpad  # add bottom padding

# draw.text((width//2 - font_width//2, height//2 - font_height//2),
#          text, font=font, fill=(255, 255, 0))

image.show()


# image = Image.open("blinka.jpg")
