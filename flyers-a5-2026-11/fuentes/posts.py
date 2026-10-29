import sys, json, subprocess, os
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from PIL import Image

S, OUT = sys.argv[1], sys.argv[2]
W = S + '/work/'
for n in ['Regular', 'SemiBold', 'Bold']:
    pdfmetrics.registerFont(TTFont('M-' + n, f'{S}/fonts/Montserrat-{n}.ttf'))
Y, K, WH = HexColor('#FAB714'), HexColor('#020100'), HexColor('#FFFFFF')
LOGO = json.load(open(W + 'logo.json'))
N = 1080
ZONA = 'ONLINE · TODA ESPAÑA'


def sw(s, f, z, tr=0):
    return pdfmetrics.stringWidth(s, f, z) + max(len(s) - 1, 0) * z * tr


def text(c, x, y, s, f, z, col, tr=0, align='left'):
    w = sw(s, f, z, tr)
    if align == 'right': x -= w
    t = c.beginText(x, y); t.setFont(f, z); t.setFillColor(col); t.setCharSpace(z * tr); t.textOut(s); c.drawText(t)
    return w


def wrap(s, f, z, maxw):
    out, cur = [], ''
    for w in s.split(' '):
        t = (cur + ' ' + w).strip()
        if sw(t, f, z) <= maxw or not cur: cur = t
        else: out.append(cur); cur = w
    return out + [cur]


def para(c, x, ytop, s, f, z, col, maxw=990, lead=1.15):
    lines = s if isinstance(s, list) else wrap(s, f, z, maxw)
    y = ytop - z * .78
    for i, l in enumerate(lines):
        text(c, x, y, l, f, z, col)
        if i < len(lines) - 1: y -= z * lead
    return y


def logo(c, x, y, w, col):
    s = w / LOGO['w']; H = LOGO['h']; p = c.beginPath()
    X = lambda v: x + v * s; Yf = lambda v: y + (H - v) * s
    for cv in LOGO['curves']:
        p.moveTo(X(cv['start'][0]), Yf(cv['start'][1]))
        for g in cv['segs']:
            if g[0] == 'L': p.lineTo(X(g[1]), Yf(g[2])); p.lineTo(X(g[3]), Yf(g[4]))
            else: p.curveTo(X(g[1]), Yf(g[2]), X(g[3]), Yf(g[4]), X(g[5]), Yf(g[6]))
        p.close()
    c.saveState(); c.setFillColor(col); c.drawPath(p, fill=1, stroke=0, fillMode=1); c.restoreState()


def icon(c, name, x, y, size, col):
    c.saveState(); c.translate(x, y); k = size / 24.0; c.scale(k, k)
    c.setStrokeColor(col); c.setFillColor(col); c.setLineWidth(2.2); c.setLineCap(1); c.setLineJoin(1)
    if name == 'pin':
        p = c.beginPath(); p.moveTo(12, 2)
        p.curveTo(12, 2, 4, 10, 4, 15); p.curveTo(4, 19.4, 7.6, 22, 12, 22)
        p.curveTo(16.4, 22, 20, 19.4, 20, 15); p.curveTo(20, 10, 12, 2, 12, 2); p.close()
        c.drawPath(p, stroke=1, fill=0); c.circle(12, 15, 3, stroke=1, fill=0)
    elif name == 'rayo':
        p = c.beginPath(); p.moveTo(13.5, 22); p.lineTo(4.5, 10.5); p.lineTo(11.5, 10.5); p.lineTo(10.5, 2); p.lineTo(19.5, 13.5); p.lineTo(12.5, 13.5); p.close()
        c.drawPath(p, stroke=1, fill=0)
    elif name == 'salto':
        c.circle(12, 20, 2.2, stroke=1, fill=0)                    # cabeza
        c.line(12, 17.6, 11.3, 10.5)                              # cuerpo
        c.line(11.8, 15.5, 7.2, 19.8); c.line(11.8, 15.5, 16.8, 19.6)  # brazos arriba
        p = c.beginPath(); p.moveTo(11.3, 10.5); p.lineTo(8, 8.6); p.lineTo(8.8, 5.2); c.drawPath(p, stroke=1, fill=0)    # pierna doblada
        p = c.beginPath(); p.moveTo(11.3, 10.5); p.lineTo(14.6, 7.6); p.lineTo(13.4, 4.4); c.drawPath(p, stroke=1, fill=0)  # pierna doblada
        c.line(6, 1.6, 9.5, 1.6); c.line(12, 1.6, 15.5, 1.6)        # líneas de salto
    elif name == 'mail':
        c.rect(2.5, 5, 19, 14, stroke=1, fill=0)
        p = c.beginPath(); p.moveTo(2.5, 19); p.lineTo(12, 11.5); p.lineTo(21.5, 19); c.drawPath(p, stroke=1, fill=0)
    elif name == 'tel':
        p = c.beginPath(); p.moveTo(6, 21.5); p.lineTo(9.5, 21.5); p.lineTo(11, 17); p.lineTo(8.6, 15.4)
        p.curveTo(9.8, 12.8, 11.4, 11.2, 14, 10); p.lineTo(15.6, 12.4); p.lineTo(20.5, 11); p.lineTo(20.5, 7)
        p.curveTo(20.5, 5, 19, 3, 16.5, 3); p.curveTo(9.5, 3.5, 3.5, 9.5, 3, 17.5); p.curveTo(3, 20, 4.5, 21.5, 6, 21.5); p.close()
        c.drawPath(p, stroke=1, fill=0)
    elif name == 'insta':
        c.roundRect(2.5, 2.5, 19, 19, 5.5, stroke=1, fill=0); c.circle(12, 12, 4.3, stroke=1, fill=0)
        c.circle(17.3, 17.3, 1.1, stroke=0, fill=1)
    elif name == 'fb':
        c.roundRect(2.5, 2.5, 19, 19, 5.5, stroke=1, fill=0)
        p = c.beginPath(); p.moveTo(13, 2.5); p.lineTo(13, 13.5); p.curveTo(13, 16, 14, 17, 16.5, 17); c.drawPath(p, stroke=1, fill=0)
        c.line(10, 11.5, 16.5, 11.5)
    elif name == 'chat':
        p = c.beginPath(); p.moveTo(6, 4); p.lineTo(3, 2); p.lineTo(3, 7)
        p.curveTo(2, 9, 2, 10, 2, 12); p.curveTo(2, 17.5, 6.5, 21, 12, 21)
        p.curveTo(17.5, 21, 22, 17.5, 22, 12); p.curveTo(22, 6.5, 17.5, 3, 12, 3); p.curveTo(9.5, 3, 7.5, 3.4, 6, 4); p.close()
        c.drawPath(p, stroke=1, fill=0)
        for xx in (8, 12, 16): c.circle(xx, 12, 1.3, stroke=0, fill=1)
    c.restoreState()


def photo(c, path, cropx0=None):
    im = Image.open(path).convert('RGB')
    ar = N / 540
    w, h = im.size
    if w / h > ar:
        nw = int(h * ar); x0 = (w - nw) if cropx0 is None else cropx0; im = im.crop((x0, 0, x0 + nw, h))
    else:
        nh = int(w / ar); im = im.crop((0, 0, w, nh))
    c.drawImage(ImageReader(im), 0, 540, N, 540)


def header(c):
    c.setFillColor(Y); c.rect(0, 830, 380, 250, fill=1, stroke=0)
    logo(c, 70, 890, 240, K)
    z, tr = 30, .08
    bw = 36 + 34 + 12 + sw(ZONA, 'M-Bold', z, tr) + 30
    assert bw <= 590, bw
    c.setFillColor(K); c.rect(0, 768, bw, 62, fill=1, stroke=0)
    icon(c, 'pin', 36, 782, 34, Y)
    text(c, 82, 789, ZONA, 'M-Bold', z, Y, tr)


def bottom(c, bg, tagcol):
    c.setFillColor(bg); c.rect(0, 0, N, 540, fill=1, stroke=0)
    icon(c, 'rayo', 44, 484, 32, tagcol)
    text(c, 84, 492, 'ESTAMOS HABLANDO DE LA FACTURA DE LA LUZ', 'M-Bold', 26, tagcol, .05)
    c.setFillColor(tagcol); c.rect(46, 472, 988, 3, fill=1, stroke=0)
    footer(c, bg)


def footer(c, bg):
    c.setFillColor(K); c.rect(0, 0, N, 118, fill=1, stroke=0)
    if bg == K:
        c.setFillColor(Y); c.rect(46, 118, 988, 2, fill=1, stroke=0)
    m = 'María, nuestra asistente virtual, te atiende en www.chatenergia.com'
    z = 25
    while sw(m, 'M-SemiBold', z) > 940: z -= .5
    icon(c, 'chat', 46, 64, 32, Y)
    text(c, 88, 72, m, 'M-SemiBold', z, Y)
    items = [('tel', '+34 696 652 918'), ('mail', 'info@chatenergia.com'), ('insta', '@chat_energia'), ('fb', 'Chat Energía')]
    z = 22
    tot = lambda z: sum(28 + 8 + sw(t, 'M-SemiBold', z) for _, t in items)
    while tot(z) > 900: z -= .5
    gap = (988 - tot(z)) / (len(items) - 1)
    x = 46
    for ic, t in items:
        icon(c, ic, x, 20, 28, WH)
        x += 36 + text(c, x + 36, 26, t, 'M-SemiBold', z, WH) + gap


def pill(c, s, bg, fg, y=140):
    z = 32; w = 66 + 14 + sw(s, 'M-Bold', z) + 40
    x = N - 46 - w
    c.setFillColor(bg); c.roundRect(x, y, w, 76, 38, fill=1, stroke=0)
    icon(c, 'chat', x + 30, y + 20, 36, fg)
    text(c, x + 80, y + 27, s, 'M-Bold', z, fg)


def render(name, draw):
    pdf = f'{OUT}/{name}.pdf'
    c = canvas.Canvas(pdf, pagesize=(N, N)); draw(c); c.showPage(); c.save()
    subprocess.run(['pdftoppm', '-r', '144', '-png', '-singlefile', pdf, f'{OUT}/{name}_2x'], check=True)
    Image.open(f'{OUT}/{name}_2x.png').convert('RGB').resize((N, N), Image.LANCZOS).save(f'{OUT}/{name}.jpg', quality=92)
    os.remove(pdf); os.remove(f'{OUT}/{name}_2x.png'); print('ok', name)


def v1(c):
    photo(c, W + 'full_hombre.png'); header(c); bottom(c, Y, K)
    y = para(c, 46, 450, ['¡Cobarde!', 'Tu factura sube sin avisar.'], 'M-Bold', 66, K, lead=1.05)
    icon(c, 'salto', 46 + sw('¡Cobarde!', 'M-Bold', 66) + 18, 392, 76, K)
    para(c, 46, y - 26, 'Es una novela por entregas donde siempre muere tu bolsillo.', 'M-Regular', 34, K, 990)
    pill(c, 'Escríbenos al 696 652 918', K, Y)


def v2(c):
    photo(c, W + 'full_mujer.png'); header(c); bottom(c, K, Y)
    y = para(c, 46, 450, ['No es culpa tuya.'], 'M-Bold', 80, Y)
    y = para(c, 46, y - 30, 'Te han hecho sentir culpable por cocinar.', 'M-Regular', 36, WH)
    para(c, 46, y - 14, 'El problema no es lo que gastas: es cómo te cobran.', 'M-Bold', 36, Y)
    pill(c, 'Escríbenos al 696 652 918', Y, K)


def v3(c):
    photo(c, W + 'foto_billete_rgb.png'); header(c); bottom(c, Y, K)
    y = para(c, 46, 450, ['Hasta esto', 'podrías ahorrar.'], 'M-Bold', 70, K, lead=1.05)
    text(c, 46, y - 56, 'Hasta 500 € al año en tu factura de la luz.*', 'M-Bold', 36, K)
    pill(c, 'Escríbenos al 696 652 918', K, Y, y=152)
    text(c, 46, 130, '*Cifra orientativa: ahorro anual en los mejores casos.', 'M-Regular', 19, K)


for n, f in [('post-a-jardiel', v1), ('post-b-pinuel', v2), ('post-c-billete', v3)]:
    render(n, f)
