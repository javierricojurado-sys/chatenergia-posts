import sys, json, urllib.parse
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import CMYKColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from PIL import Image

S = sys.argv[1]
W = S + '/work/'
OUT = sys.argv[2]
for n in ['Regular', 'SemiBold', 'Bold', 'Light']:
    pdfmetrics.registerFont(TTFont('M-' + n, f'{S}/fonts/Montserrat-{n}.ttf'))

# ---- Colores del manual (CMYK) ----
Y = CMYKColor(0, .30, .95, 0)            # amarillo-chat 0/30/95/0
KR = CMYKColor(.75, .68, .67, .98)       # negro-chat enriquecido (fondos y titulares)
K = CMYKColor(0, 0, 0, 1)                # negro 100 K (texto pequeño)
GD = CMYKColor(0, 0, 0, .67)             # gris-oscuro
GM = CMYKColor(0, 0, 0, .55)             # gris-medio
GL = CMYKColor(0, 0, 0, .06)             # fondo claro de tarjetas
WH = CMYKColor(0, 0, 0, 0)
REG = CMYKColor(1, 1, 1, 1)              # registro (marcas de corte)

TW, TH, BL, SL = 148, 210, 3, 12          # corte, sangrado, margen de marcas (mm)
PW, PH = TW + 2 * SL, TH + 2 * SL
LOGO = json.load(open(W + 'logo.json'))
LOGO_AR = LOGO['w'] / LOGO['h']


def P(v):  # mm (coordenadas de corte) -> puntos de página
    return (SL + v) * mm


class Page:
    def __init__(self, c, label):
        self.c = c
        c.setPageSize((PW * mm, PH * mm))
        c.setTrimBox((SL * mm, SL * mm, (SL + TW) * mm, (SL + TH) * mm))
        c.setBleedBox(((SL - BL) * mm, (SL - BL) * mm, (SL + TW + BL) * mm, (SL + TH + BL) * mm))
        self.label = label

    # --- primitivas ---
    def rect(self, x, y, w, h, fill, stroke=None, lw=0.3, dash=None):
        c = self.c
        c.saveState()
        c.setFillColor(fill) if fill is not None else None
        if stroke is not None:
            c.setStrokeColor(stroke); c.setLineWidth(lw)
            if dash: c.setDash(*dash)
        c.rect(P(x), P(y), w * mm, h * mm, fill=1 if fill is not None else 0, stroke=1 if stroke is not None else 0)
        c.restoreState()

    def pill(self, x, y, w, h, fill):
        c = self.c
        c.saveState(); c.setFillColor(fill)
        c.roundRect(P(x), P(y), w * mm, h * mm, h * mm / 2, fill=1, stroke=0)
        c.restoreState()

    def text(self, x, y, s, font, size, color, track=0, align='left'):
        c = self.c
        w = self.width(s, font, size, track)
        if align == 'right': x = x - w / mm
        if align == 'center': x = x - w / mm / 2
        t = c.beginText(P(x), P(y))
        t.setFont(font, size); t.setFillColor(color)
        t.setCharSpace(size * track if track else 0)
        t.textOut(s)
        c.drawText(t)
        return w / mm

    def width(self, s, font, size, track=0):
        return pdfmetrics.stringWidth(s, font, size) + (len(s) - 1) * size * track if s else 0

    def wrap(self, s, font, size, maxw_mm):
        words, lines, cur = s.split(' '), [], ''
        for wd in words:
            t = (cur + ' ' + wd).strip()
            if self.width(t, font, size) <= maxw_mm * mm or not cur:
                cur = t
            else:
                lines.append(cur); cur = wd
        lines.append(cur)
        return lines

    def para(self, x, ytop, s, font, size, color, maxw, lead=1.2, align='left'):
        """Dibuja párrafo con la primera línea de base bajo ytop. Devuelve y de la última base."""
        lines = s if isinstance(s, list) else self.wrap(s, font, size, maxw)
        y = ytop - size * 0.78 / mm * 1.0
        for i, ln in enumerate(lines):
            self.text(x, y, ln, font, size, color, align=align)
            if i < len(lines) - 1: y -= size * lead / mm
        return y

    def image(self, path, x, y, w, h, cmyk=False):
        img = Image.open(path)
        if cmyk: img = img.convert('CMYK')
        from reportlab.lib.utils import ImageReader
        self.c.drawImage(ImageReader(img), P(x), P(y), w * mm, h * mm)

    def logo(self, x, y, w, color):
        c, d = self.c, LOGO
        s = w / d['w']; H = d['h']
        X = lambda px: P(x + px * s)
        Yf = lambda py: P(y + (H - py) * s)
        p = c.beginPath()
        for cv in d['curves']:
            p.moveTo(X(cv['start'][0]), Yf(cv['start'][1]))
            for sg in cv['segs']:
                if sg[0] == 'L':
                    p.lineTo(X(sg[1]), Yf(sg[2])); p.lineTo(X(sg[3]), Yf(sg[4]))
                else:
                    p.curveTo(X(sg[1]), Yf(sg[2]), X(sg[3]), Yf(sg[4]), X(sg[5]), Yf(sg[6]))
            p.close()
        c.saveState(); c.setFillColor(color)
        c.drawPath(p, fill=1, stroke=0, fillMode=1)  # even-odd
        c.restoreState()
        return w / LOGO_AR

    def qr(self, data, x, y, size, color=K):
        wdg = QrCodeWidget(data, barLevel='M', barBorder=0)
        b = wdg.getBounds(); bw, bh = b[2] - b[0], b[3] - b[1]
        wdg.barFillColor = color
        d = Drawing(size * mm, size * mm, transform=[size * mm / bw, 0, 0, size * mm / bh, 0, 0])
        d.add(wdg)
        renderPDF.draw(d, self.c, P(x), P(y))

    # --- iconos lineales (retícula 24, trazo 2, terminaciones redondas) ---
    def _ic(self, x, y, size, color):
        c = self.c; c.saveState()
        c.translate(P(x), P(y)); k = size * mm / 24.0; c.scale(k, k)
        c.setStrokeColor(color); c.setFillColor(color); c.setLineWidth(2 if size > 6 else 2.2)
        c.setLineCap(1); c.setLineJoin(1)
        return c

    def icon(self, name, x, y, size, color):
        c = self._ic(x, y, size, color)
        if name == 'pin':
            p = c.beginPath(); p.moveTo(12, 2)
            p.curveTo(12, 2, 4, 10, 4, 15); p.curveTo(4, 19.4, 7.6, 22, 12, 22)
            p.curveTo(16.4, 22, 20, 19.4, 20, 15); p.curveTo(20, 10, 12, 2, 12, 2); p.close()
            c.drawPath(p, stroke=1, fill=0); c.circle(12, 15, 3, stroke=1, fill=0)
        elif name == 'factura':
            p = c.beginPath(); p.moveTo(5, 2); p.lineTo(5, 22); p.lineTo(15, 22); p.lineTo(19, 18); p.lineTo(19, 2); p.lineTo(16.5, 4); p.lineTo(14, 2); p.lineTo(11.5, 4); p.lineTo(9, 2); p.lineTo(7, 4); p.close()
            c.drawPath(p, stroke=1, fill=0)
            c.line(12, 8, 12, 17); c.line(9, 14, 12, 17); c.line(15, 14, 12, 17)
        elif name == 'potencia':
            p = c.beginPath(); p.arc(2, 2, 22, 22, 0, 180); c.drawPath(p, stroke=1, fill=0)
            c.line(2, 6, 22, 6); c.line(12, 6, 17, 15)
            c.circle(12, 6, 1.6, stroke=0, fill=1)
            c.line(4.5, 12, 6.5, 11); c.line(12, 18, 12, 16); c.line(19.5, 12, 17.5, 11)
        elif name == 'contrato':
            c.rect(3, 2, 13, 19, stroke=1, fill=0)
            c.line(6, 16, 13, 16); c.line(6, 12, 11, 12)
            c.circle(16, 7, 4.5, stroke=1, fill=0); c.line(19.2, 3.8, 22, 1)
        elif name == 'chat':
            p = c.beginPath(); p.moveTo(6, 4); p.lineTo(3, 2); p.lineTo(3, 7)
            p.curveTo(2, 9, 2, 10, 2, 12); p.curveTo(2, 17.5, 6.5, 21, 12, 21)
            p.curveTo(17.5, 21, 22, 17.5, 22, 12); p.curveTo(22, 6.5, 17.5, 3, 12, 3); p.curveTo(9.5, 3, 7.5, 3.4, 6, 4); p.close()
            c.drawPath(p, stroke=1, fill=0)
            for xx in (8, 12, 16): c.circle(xx, 12, 1.3, stroke=0, fill=1)
        elif name == 'web':
            c.circle(12, 12, 10, stroke=1, fill=0); c.ellipse(8, 2, 16, 22, stroke=1, fill=0)
            c.line(2, 12, 22, 12)
        elif name == 'insta':
            c.roundRect(2.5, 2.5, 19, 19, 5.5, stroke=1, fill=0); c.circle(12, 12, 4.3, stroke=1, fill=0)
            c.circle(17.3, 17.3, 1.1, stroke=0, fill=1)
        elif name == 'tijera':
            c.circle(5.5, 5.5, 3, stroke=1, fill=0); c.circle(5.5, 18.5, 3, stroke=1, fill=0)
            c.line(8, 7, 21, 18); c.line(8, 17, 21, 6)
        elif name == 'rayo':
            p = c.beginPath(); p.moveTo(13.5, 22); p.lineTo(4.5, 10.5); p.lineTo(11.5, 10.5); p.lineTo(10.5, 2); p.lineTo(19.5, 13.5); p.lineTo(12.5, 13.5); p.close()
            c.drawPath(p, stroke=1, fill=0)
        elif name == 'euro':
            c.circle(12, 12, 10, stroke=1, fill=0)
            p = c.beginPath(); p.arc(7.5, 6, 18.5, 18, 55, 250); c.drawPath(p, stroke=1, fill=0)
            c.line(6.5, 13.5, 13.5, 13.5); c.line(6.5, 10.5, 13.5, 10.5)
        c.restoreState()

    # --- bloques comunes ---
    def marks(self):
        c = self.c; c.saveState(); c.setStrokeColor(REG); c.setLineWidth(0.25)
        off, ln = 3 + 0.5, 6
        for x in (0, TW):
            for y in (0, TH):
                sx = -1 if x == 0 else 1; sy = -1 if y == 0 else 1
                c.line(P(x), P(y + sy * off), P(x), P(y + sy * (off + ln)))
                c.line(P(x + sx * off), P(y), P(x + sx * (off + ln)), P(y))
        c.setFont('M-Regular', 5.5); c.setFillColor(REG)
        c.drawString(P(0), P(-9), self.label + '  ·  A5 148 × 210 mm  ·  sangrado 3 mm  ·  CMYK')
        c.restoreState()

    def front_header(self, band_y=145):
        # Bloque del logo (versión principal: negro sobre amarillo, 1X de protección)
        self.rect(-3, 162, 72, 51, Y)
        self.logo(11, 177.5, 46, KR)
        # Banda CHIPIONA
        size = 27; tr = 0.12
        tw = self.width('CHIPIONA', 'M-Bold', size, tr) / mm
        bw = 11 + 10 + tw + 9
        self.rect(-3, band_y, bw + 3, 17, KR)
        self.icon('pin', 9, band_y + 3.5, 10, Y)
        self.text(22, band_y + 4.3, 'CHIPIONA', 'M-Bold', size, Y, tr)

    def pill_cta(self, s, fill, color, xr=138, y=8):
        size = 13
        w = self.width(s, 'M-Bold', size) / mm + 14
        self.pill(xr - w, y, w, 11, fill)
        self.text(xr - w + 7, y + 3.6, s, 'M-Bold', size, color)

    # ---------- bloques del reverso (letra grande) ----------
    def pain_band(self, big, small):
        """Mensaje de dolor: banda negra arriba, a sangre. Devuelve la y inferior de la banda."""
        y = self.para(10, 201, big, 'M-Bold', 18, Y, 128, 1.15)
        y = self.para(10, y - 3.2, small, 'M-Regular', 14, WH, 128, 1.2) if small else y
        bottom = y - 6.5
        # la banda se pinta debajo: se dibuja antes que el texto
        return bottom

    def draw_pain(self, big, small):
        # medir sin pintar
        nb = len(self.wrap(big, 'M-Bold', 18, 128)); ns = len(self.wrap(small, 'M-Regular', 14, 128))
        h_txt = (18 * .78 + (nb - 1) * 18 * 1.15) / mm + 3.2 + (14 * .78 + (ns - 1) * 14 * 1.2) / mm
        bottom = 201 - h_txt - 6.5
        self.rect(-3, bottom, 154, 216 - bottom, KR)
        self.pain_band(big, small)
        return bottom

    def items(self, data, ytop, icons=('factura', 'potencia', 'contrato'), gap=4.5):
        y = ytop
        for (q, a), ic in zip(data, icons):
            ql = self.wrap(q, 'M-SemiBold', 13, 116)
            al = self.wrap(a, 'M-Bold', 13, 110)
            top = y
            yb = self.para(24, y, ql, 'M-SemiBold', 13, K, 116, 1.18)
            bt = yb - 3.2
            bh = (13 * .72 + (len(al) - 1) * 13 * 1.18) / mm + 5.6
            self.rect(24, bt - bh, 117, bh, KR)
            self.para(28, bt - 2.6, al, 'M-Bold', 13, Y, 110, 1.18)
            bottom = bt - bh
            self.icon(ic, 8, (top + bottom) / 2 - 6, 12, K)
            y = bottom - gap
        return y + gap

    def steps(self, data, ytop, gap=6):
        y = ytop
        for i, s in enumerate(data):
            lines = self.wrap(s, 'M-SemiBold', 14, 108)
            h = max(14, (14 * .72 + (len(lines) - 1) * 14 * 1.2) / mm)
            cy = y - h / 2
            c = self.c; c.saveState(); c.setFillColor(KR); c.circle(P(16), P(cy), 7 * mm, stroke=0, fill=1); c.restoreState()
            self.text(16, cy - 2.9, str(i + 1), 'M-Bold', 18, Y, align='center')
            th = (14 * .72 + (len(lines) - 1) * 14 * 1.2) / mm
            self.para(28, cy + th / 2 + 0.3, lines, 'M-SemiBold', 14, K, 108, 1.2)
            y = y - h - gap
        return y + gap

    def cta(self, big, small, ybottom=90):
        """Llamada a la acción justo encima del bono, alineada por abajo."""
        nb = len(self.wrap(big, 'M-Bold', 16, 128)); ns = len(self.wrap(small, 'M-Regular', 13, 128)) if small else 0
        h = (16 * .78 + (nb - 1) * 16 * 1.15) / mm + ((3 + 13 * .78 + (ns - 1) * 13 * 1.2) / mm * 0 + 3 + (13 * .78 + (ns - 1) * 13 * 1.2) / mm if ns else 0)
        top = ybottom + h + 1
        y = self.para(10, top, big, 'M-Bold', 16, KR, 128, 1.15)
        if small:
            self.para(10, y - 3, small, 'M-Regular', 13, K, 128, 1.2)
        return top

    def coupon(self, title, sub, wa_line, qrtext, qrdata):
        self.rect(-3, 19, 154, 67, KR)
        self.rect(7, 24, 134, 57, Y)
        self.rect(9.5, 26.5, 129, 52, None, KR, 0.9, ([3, 2.2], 0))
        c = self.c; c.saveState(); c.setStrokeColor(KR); c.setLineWidth(0.9); c.setDash([3, 2.2], 0)
        c.line(P(101), P(26.5), P(101), P(78.5)); c.restoreState()
        c.saveState(); c.setFillColor(KR)
        c.circle(P(101), P(81), 3.2 * mm, stroke=0, fill=1); c.circle(P(101), P(24), 3.2 * mm, stroke=0, fill=1)
        c.restoreState()
        self.icon('tijera', 14, 70.3, 5.5, K)
        self.text(22, 71.4, 'BONO AHORRO · 12 MESES', 'M-Bold', 9, K, 0.12)
        y = self.para(14, 67.5, title, 'M-Bold', 17, KR, 84, 1.08)
        y = self.para(14, y - 2.8, sub, 'M-SemiBold', 11.5, K, 84, 1.15)
        self.text(14, 39.5, wa_line, 'M-SemiBold', 11, K)
        c.saveState(); c.setFillColor(KR); c.circle(P(18.5), P(32.6), 4.5 * mm, stroke=0, fill=1); c.restoreState()
        self.icon('chat', 15.3, 29.4, 6.4, Y)
        self.text(25.5, 30.0, '696 652 918', 'M-Bold', 21, KR)
        self.rect(105.5, 43, 31, 31, WH)
        self.qr(qrdata, 108, 45.5, 26)
        for i, ln in enumerate(qrtext):
            self.text(121, 37.0 - i * 4.4, ln, 'M-Bold', 10, K, align='center')

    def footer(self, place):
        self.logo(8, 2.5, 30, KR)
        self.icon('web', 46, 10.6, 4.2, K)
        self.text(52, 11.5, 'www.chatenergia.com', 'M-SemiBold', 10, K)
        self.icon('pin', 46, 3.4, 4.2, K)
        w = self.text(52, 4.3, place, 'M-SemiBold', 10, K)
        assert 52 + w <= 141, w

    def finish(self):
        self.marks(); self.c.showPage()


WA = 'https://wa.me/34696652918?text='
CHIP = 'Una empresa chipionera'


def qr_url(tag):
    return WA + urllib.parse.quote(f'Hola, quiero revisar mi factura de la luz (flyer Chipiona {tag})')


def front_text(p, head, head_color, sub_lines, sub_color, size=33, tag_color=K):
    tag = 'ESTAMOS HABLANDO DE LA FACTURA DE LA LUZ'
    ts = 11
    while p.width(tag, 'M-Bold', ts, 0.05) / mm > 120: ts -= 0.25
    p.icon('rayo', 9.5, 66.2, 5.6, tag_color)
    p.text(16.5, 67.3, tag, 'M-Bold', ts, tag_color, 0.05)
    p.rect(10, 63.6, 128, 0.5, tag_color)
    y = p.para(10, 61, head, 'M-Bold', size, head_color, 130, 1.02)
    y = y - 5.5
    for font, sz, col, s in sub_lines:
        y = p.para(10, y, s, font, sz, col if col else sub_color, 128, 1.2) - 2.2
    assert y > 20, y
    return y


# ======================= VERSIÓN 1 · JARDIEL =======================
def v1(c):
    p = Page(c, 'Chat Energía · Flyer Chipiona · V1 Jardiel · ANVERSO')
    p.image(W + 'foto_hombre.png', -3, 70, 154, 143)
    p.front_header(band_y=78)
    p.rect(-3, -3, 154, 81, Y)
    front_text(p, ['¡La Virgen!', 'Esto no es una factura.'], KR,
               [('M-Regular', 16, None, 'Es una novela por entregas donde siempre muere su bolsillo.')], K, size=30)
    p.pill_cta('Dele la vuelta  →', KR, Y)
    p.finish()

    p = Page(c, 'Chat Energía · Flyer Chipiona · V1 Jardiel · REVERSO')
    p.rect(-3, -3, 154, 216, WH)
    b = p.draw_pain('Usted apaga la luz al salir de cada habitación.',
                    'Su factura, por lo visto, no se ha enterado.')
    y = p.items([('«Jododíos, la luz ha vuelto a subir y nadie me avisa.»', 'Nosotros sí. Es una costumbre antigua.'),
                 ('«Pago una potencia que no uso.»', 'Como un abrigo en agosto. Se la ajustamos.'),
                 ('«Firmé algo que nadie me explicó.»', 'Nosotros se lo leemos en voz alta.')], b - 4.5, gap=3.2)
    top = p.cta('Mándenos una foto de su factura por WhatsApp.', 'El final feliz lo escribimos nosotros.')
    assert y - top >= 3, (y, top)
    p.coupon(['Vale por un año sin', 'sustos en el buzón'], 'Revisión gratis de su factura de luz.',
             'Escríbanos por WhatsApp o llámenos:', ['Escanéelo', 'con el móvil'], qr_url('A'))
    p.footer(CHIP); p.finish()


# ======================= VERSIÓN 2 · PIÑUEL =======================
def v2(c):
    p = Page(c, 'Chat Energía · Flyer Chipiona · V2 Piñuel · ANVERSO')
    p.image(W + 'foto_mujer.png', -3, 70, 154, 143)
    p.front_header()
    p.rect(-3, -3, 154, 81, KR)
    front_text(p, ['No es culpa tuya.'], Y,
               [('M-Regular', 15, WH, 'Te han hecho sentir culpable por cocinar.'),
                ('M-Bold', 15, Y, 'El problema no es lo que gastas: es cómo te cobran.')], WH, size=34, tag_color=Y)
    p.pill_cta('Mira las señales  →', Y, KR)
    p.finish()

    p = Page(c, 'Chat Energía · Flyer Chipiona · V2 Piñuel · REVERSO')
    p.rect(-3, -3, 154, 216, WH)
    b = p.draw_pain('Apagas luces, pones la lavadora de noche… y la factura sube igual.',
                    'No estás haciendo nada mal.')
    p.text(10, b - 8, '3 SEÑALES DE QUE TE COBRAN DE MÁS', 'M-Bold', 10, GD, 0.1)
    y = p.items([('Sube sin avisar y te hace sentir culpable.', 'La revisamos gratis.'),
                 ('Te cobra una potencia que no usas.', 'Te la ajustamos.'),
                 ('Te hizo firmar sin explicarte nada.', 'Te lo explicamos todo.')], b - 11.5, gap=3.6)
    top = p.cta('Ponle nombre. Después, ponle fin.',
                'Mándanos una foto de tu factura por WhatsApp.')
    assert y - top >= 3, (y, top)
    p.coupon(['Un año de relación', 'sana con tu factura'], 'Revisión gratis de tu factura de luz.',
             'Escríbenos por WhatsApp o llámanos:', ['Escanéalo', 'con el móvil'], qr_url('B'))
    p.footer(CHIP); p.finish()


# ======================= VERSIÓN 3 · BILLETE =======================
def v3(c):
    p = Page(c, 'Chat Energía · Flyer Chipiona · V3 Billete · ANVERSO')
    p.image(W + 'foto_billete_cmyk.tif', -3, 70, 154, 143, cmyk=True)
    p.front_header()
    p.rect(-3, -3, 154, 81, Y)
    front_text(p, ['Hasta esto', 'podrías ahorrar.'], KR,
               [('M-Bold', 19, KR, 'Hasta 500 € al año'),
                ('M-Regular', 15, K, 'en tu factura de la luz.*')], K, size=33)
    p.pill_cta('Descubre cómo  →', KR, Y, y=12)
    p.text(10, 4.0, '*Cifra orientativa: ahorro anual en los mejores casos.', 'M-Regular', 7.5, K)
    p.finish()

    p = Page(c, 'Chat Energía · Flyer Chipiona · V3 Billete · REVERSO')
    p.rect(-3, -3, 154, 216, WH)
    b = p.draw_pain('Cada mes sin revisar tu factura, ese billete se lo queda otro.',
                    'Puede que estés pagando de más sin saberlo.')
    p.text(10, b - 8, 'ASÍ DE FÁCIL', 'M-Bold', 10, GD, 0.12)
    y = p.steps(['Mándanos una foto de tu factura por WhatsApp.',
                 'La revisamos gratis y te decimos cuánto puedes ahorrar.',
                 'Si te conviene, nos encargamos de todo el cambio.'], b - 12, gap=4.5)
    top = p.cta('Si hay ahorro, es tuyo.',
                'Somos una empresa chipionera. Escríbenos y lo buscamos contigo.')
    assert y - top >= 3, (y, top)
    p.coupon(['Vale por un año', 'pagando lo justo'], 'Revisión gratis de tu factura de luz.',
             'Escríbenos por WhatsApp o llámanos:', ['Escanéalo', 'con el móvil'], qr_url('C'))
    p.footer(CHIP); p.finish()


for name, fn in [('Flyer_A5_Chipiona_V1_Jardiel_imprenta.pdf', v1),
                 ('Flyer_A5_Chipiona_V2_Pinuel_imprenta.pdf', v2),
                 ('Flyer_A5_Chipiona_V3_Billete_imprenta.pdf', v3)]:
    c = canvas.Canvas(OUT + '/' + name)
    c.setTitle(name.replace('_', ' ').replace('.pdf', '')); c.setAuthor('Chat Energía')
    fn(c); c.save(); print('ok', name)
