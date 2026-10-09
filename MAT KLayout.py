//MAT
import klayout.db as kdb
import klayout.lay as klay

# Enter your Python code here ..
# -*- coding: utf-8 -*-
"""
N x N systolic matrix-multiply array - parametric floorplan generator.

HOW TO USE INSIDE KLAYOUT (recommended)
  1. Macros > Macro Development > New Python macro, paste this whole file.
  2. Edit N and WIDTH below.
  3. Press Run (green triangle / Shift+F5). A new layout view opens with the array.
     A copy is also written to  <your home folder>/matmul_<N>x<N>_W<WIDTH>.gds

STANDALONE (pip install klayout):
  python matmul_klayout_macro.py 8 16        ->  matmul_8x8_W16.gds   (N=8, WIDTH=16)

Abstract floorplan: PE array, buses, MAC/ACC blocks, pins. Not DRC/LVS clean.
"""
import os
import sys

# ---------------------------- USER SETTINGS ----------------------------
N = 10            # array is N x N processing elements
WIDTH = 8        # data width in bits (number of wires per A / B bus)
TRACK = 1.0      # um, wire pitch inside a bus
WIRE = 0.4       # um, wire width
MARGIN = 4.0     # um, spacing inside a PE
# -----------------------------------------------------------------------

# layer, datatype (SKY130 numbering so the sky130 .lyp works; change for other PDKs)
L_MET1 = (68, 20)
L_MET2 = (69, 20)
L_MET3 = (70, 20)
L_VIA1 = (68, 44)
L_VIA2 = (69, 44)
L_MAC = (100, 0)
L_ACC = (101, 0)
L_BND = (235, 4)
L_PIN2 = (69, 16)
L_PIN3 = (70, 16)
L_TXT2 = (69, 5)
L_TXT3 = (70, 5)
L_TXT = (1, 0)


def _main_window():
    """KLayout main window if running inside the KLayout application, else None."""
    try:
        import pya
        app = pya.Application.instance()
        return app.main_window() if app is not None else None
    except Exception:
        return None


MW = _main_window()
if MW is not None:
    import pya as db
else:
    import klayout.db as db


def build(ly, n, width, track, wire, margin):
    """Populate layout `ly` with PE cell + NxN top cell. Returns (top_cell, w_um, h_um)."""
    ly.dbu = 0.001

    def um(v):
        return int(round(v / ly.dbu))

    def lyr(ld):
        return ly.layer(ld[0], ld[1])

    # ---------------- PE geometry ----------------
    bus_span = width * track
    pe_w = max(bus_span + 2 * margin + 16.0, 40.0)
    pe_h = max(bus_span + 2 * margin + 16.0, 40.0)

    pe = ly.create_cell("PE")
    pe.shapes(lyr(L_BND)).insert(db.Box(0, 0, um(pe_w), um(pe_h)))

    # A bus: horizontal met2, full PE width so neighbours abut
    a_y0 = margin
    for b in range(width):
        y = a_y0 + b * track
        pe.shapes(lyr(L_MET2)).insert(
            db.Box(0, um(y - wire / 2), um(pe_w), um(y + wire / 2)))

    # B bus: vertical met3, full PE height so neighbours abut
    b_x0 = margin
    for b in range(width):
        x = b_x0 + b * track
        pe.shapes(lyr(L_MET3)).insert(
            db.Box(um(x - wire / 2), 0, um(x + wire / 2), um(pe_h)))

    # MAC (lower) and accumulator (upper) blocks to the right of the buses
    mac_x0 = bus_span + 2 * margin
    blk_w = pe_w - mac_x0 - margin
    blk_h = (pe_h - 3 * margin) / 2
    mac = db.Box(um(mac_x0), um(margin), um(mac_x0 + blk_w), um(margin + blk_h))
    acc = db.Box(um(mac_x0), um(2 * margin + blk_h),
                 um(mac_x0 + blk_w), um(2 * margin + 2 * blk_h))
    pe.shapes(lyr(L_MAC)).insert(mac)
    pe.shapes(lyr(L_ACC)).insert(acc)
    pe.shapes(lyr(L_TXT)).insert(db.Text("MAC", mac.center().x, mac.center().y))
    pe.shapes(lyr(L_TXT)).insert(db.Text("ACC", acc.center().x, acc.center().y))

    # met1 taps from the A and B buses into the MAC block, with vias
    ax = b_x0 + (width - 1) * track + 2.0
    ay = a_y0
    bx = b_x0
    by = margin + blk_h / 2
    pe.shapes(lyr(L_MET1)).insert(
        db.Box(um(ax), um(ay - wire / 2), um(mac_x0), um(ay + wire / 2)))
    pe.shapes(lyr(L_MET1)).insert(
        db.Box(um(mac_x0 - wire), um(ay - wire / 2), um(mac_x0), um(by)))
    pe.shapes(lyr(L_MET1)).insert(
        db.Box(um(bx), um(by - wire / 2), um(mac_x0), um(by + wire / 2)))
    v = 0.3
    pe.shapes(lyr(L_VIA1)).insert(
        db.Box(um(ax), um(ay - v / 2), um(ax + v), um(ay + v / 2)))
    pe.shapes(lyr(L_VIA2)).insert(
        db.Box(um(bx - v / 2), um(by - v / 2), um(bx + v / 2), um(by + v / 2)))

    # ---------------- top cell: N x N array ----------------
    top = ly.create_cell("MATMUL_%dx%d_W%d" % (n, n, width))
    top.insert(db.CellInstArray(
        pe.cell_index(), db.Trans(0, 0),
        db.Vector(um(pe_w), 0), db.Vector(0, um(pe_h)), n, n))

    tot_w, tot_h = n * pe_w, n * pe_h
    top.shapes(lyr(L_BND)).insert(db.Box(0, 0, um(tot_w), um(tot_h)))

    pin = 0.6
    # west edge: A inputs (one pin per bit, one label per bus)
    for r in range(n):
        for b in range(width):
            y = r * pe_h + a_y0 + b * track
            top.shapes(lyr(L_PIN2)).insert(
                db.Box(0, um(y - pin / 2), um(pin), um(y + pin / 2)))
        top.shapes(lyr(L_TXT2)).insert(
            db.Text("a_in%d[%d:0]" % (r, width - 1), um(pin), um(r * pe_h + a_y0)))
    # north edge: B inputs
    for c in range(n):
        for b in range(width):
            x = c * pe_w + b_x0 + b * track
            top.shapes(lyr(L_PIN3)).insert(
                db.Box(um(x - pin / 2), um(tot_h - pin),
                       um(x + pin / 2), um(tot_h)))
        top.shapes(lyr(L_TXT3)).insert(
            db.Text("b_in%d[%d:0]" % (c, width - 1),
                    um(c * pe_w + b_x0), um(tot_h + 2)))
    # east edge: one result pin per row
    for r in range(n):
        y = r * pe_h + pe_h / 2
        top.shapes(lyr(L_PIN2)).insert(
            db.Box(um(tot_w - pin), um(y - pin / 2), um(tot_w), um(y + pin / 2)))
        top.shapes(lyr(L_TXT2)).insert(
            db.Text("c_out%d" % r, um(tot_w + 1), um(y)))

    top.shapes(lyr(L_TXT)).insert(
        db.Text("%dx%d systolic matmul, W=%d" % (n, n, width),
                um(tot_w / 2), um(tot_h + 8)))
    return top, tot_w, tot_h


def _run():
    n, width = N, WIDTH
    if MW is None and len(sys.argv) > 2:          # standalone: python file.py N WIDTH
        n, width = int(sys.argv[1]), int(sys.argv[2])
    fname = "matmul_%dx%d_W%d.gds" % (n, n, width)

    if MW is not None:
        # Build directly inside a NEW view of the running KLayout
        cv = MW.create_layout(1)                  # 1 = new view
        ly = cv.layout()
        top, w, h = build(ly, n, width, TRACK, WIRE, MARGIN)
        view = MW.current_view()
        view.select_cell(top.cell_index(), cv.index())
        view.add_missing_layers()
        view.max_hier()
        view.zoom_fit()
        out = os.path.join(os.path.expanduser("~"), fname)
        try:
            ly.write(out)
            print("saved copy: %s" % out)
        except Exception as e:
            print("could not save GDS copy (%s)" % e)
        print("opened %s  size=%.1f x %.1f um  PEs=%d" % (top.name, w, h, n * n))
    else:
        ly = db.Layout()
        top, w, h = build(ly, n, width, TRACK, WIRE, MARGIN)
        ly.write(fname)
        print("wrote %s  top=%s  size=%.1f x %.1f um  PEs=%d"
              % (fname, top.name, w, h, n * n))


if not os.environ.get("MATMUL_NO_RUN"):
    _run()
