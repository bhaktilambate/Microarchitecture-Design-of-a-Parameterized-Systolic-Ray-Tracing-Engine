//SYSTOLIC
import klayout.db as kdb
import klayout.lay as klay

# Enter your Python code here ..

# -*- coding: utf-8 -*-
"""
N x N systolic matrix-multiply array  -  floorplan generator v2

Features
  * power grid: abutting met1 rails (rows flipped so neighbours share VDD/VSS),
    met4 vertical stripes, VDD/VSS ring
  * input skew triangles (row r delayed r cycles, column c delayed c cycles)
  * per-PE labels PE[r][c] and data-flow arrows (A -> east, B -> south)
  * report block (area, pins, wire length, flops, peak GOPS) + report file
  * sweep over several N values -> GDS files + CSV (+ PNG plot if matplotlib exists)
  * layer colours (.lyp) loaded automatically

USE IN KLAYOUT: Macros > Macro Development > new Python macro, paste, edit the
USER SETTINGS, press Run.   STANDALONE: python this_file.py [N [WIDTH]]

Abstract floorplan only: the power stripes/rings are drawn, not via-connected,
and the MAC/ACC/register blocks are placeholders. Not DRC/LVS clean.
"""
import os
import sys

# ============================== USER SETTINGS ==============================
N = 6                 # array is N x N processing elements
WIDTH = 8             # bits per A / B data bus
CLOCK_MHZ = 100       # assumed clock, only used for the peak-GOPS estimate
SHOW_POWER = True     # rails + stripes + ring
SHOW_SKEW = True      # input skew register triangles
SHOW_LABELS = True    # PE[r][c] text in every PE
SHOW_ARROWS = True    # data-flow arrows in every PE
SWEEP = []            # e.g. [2, 4, 8, 16] -> also writes one GDS per size + CSV
TRACK = 1.0           # um, wire pitch inside a bus
WIRE = 0.4            # um, wire width
MARGIN = 4.0          # um, spacing inside a PE
# ===========================================================================

# layers (SKY130 numbering; change for another PDK)
L_MET1, L_MET2, L_MET3 = (68, 20), (69, 20), (70, 20)
L_MET4, L_MET5 = (71, 20), (72, 20)
L_VIA1, L_VIA2 = (68, 44), (69, 44)
L_MAC, L_ACC, L_REG = (100, 0), (101, 0), (102, 0)
L_ARR_A, L_ARR_B = (105, 0), (106, 0)
L_BND = (235, 4)
L_PIN2, L_PIN3 = (69, 16), (70, 16)
L_TXT1, L_TXT2, L_TXT3, L_TXT4 = (68, 5), (69, 5), (70, 5), (71, 5)
L_TXT = (1, 0)

# (layer, name, colour, dither)   dither "I0"=solid "I5"/"I9"... KLayout built-ins
LAYER_STYLE = [
    (L_BND, "boundary", "#00c8c8", "I1"),
    (L_MET1, "met1 rails/taps", "#4a90e2", "I5"),
    (L_MET2, "met2 A-bus", "#2ecc71", "I9"),
    (L_MET3, "met3 B-bus", "#e67e22", "I9"),
    (L_MET4, "met4 stripes", "#c0392b", "I5"),
    (L_MET5, "met5 ring", "#8e44ad", "I5"),
    (L_VIA1, "via1", "#ffffff", "I0"),
    (L_VIA2, "via2", "#ffffff", "I0"),
    (L_MAC, "MAC block", "#f1c40f", "I5"),
    (L_ACC, "ACC block", "#16a085", "I2"),
    (L_REG, "skew register", "#e84393", "I5"),
    (L_ARR_A, "arrow A (east)", "#2ecc71", "I0"),
    (L_ARR_B, "arrow B (south)", "#e67e22", "I0"),
    (L_PIN2, "met2 pin", "#ffffff", "I0"),
    (L_PIN3, "met3 pin", "#ffffff", "I0"),
    (L_TXT, "annotation", "#ffffff", "I1"),
    (L_TXT1, "met1 label", "#4a90e2", "I1"),
    (L_TXT2, "met2 label", "#2ecc71", "I1"),
    (L_TXT3, "met3 label", "#e67e22", "I1"),
    (L_TXT4, "met4 label", "#c0392b", "I1"),
]


def _main_window():
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


# ------------------------------------------------------------------ layout
def build(ly, n, width, track=TRACK, wire=WIRE, margin=MARGIN):
    """Populate `ly`; return (top_cell, info_dict)."""
    ly.dbu = 0.001

    def um(v):
        return int(round(v / ly.dbu))

    def lyr(ld):
        return ly.layer(ld[0], ld[1])

    def box(cell, ld, x0, y0, x1, y1):
        cell.shapes(lyr(ld)).insert(db.Box(um(x0), um(y0), um(x1), um(y1)))

    def text(cell, ld, s, x, y):
        cell.shapes(lyr(ld)).insert(db.Text(s, um(x), um(y)))

    def poly(cell, ld, pts):
        cell.shapes(lyr(ld)).insert(
            db.Polygon([db.Point(um(px), um(py)) for px, py in pts]))

    # ---------------- PE ----------------
    bus_span = width * track
    pe_w = max(bus_span + 2 * margin + 16.0, 40.0)
    pe_h = pe_w
    RAIL = 1.0

    pe = ly.create_cell("PE")
    box(pe, L_BND, 0, 0, pe_w, pe_h)
    a_y0 = margin + RAIL
    b_x0 = margin
    for b in range(width):                                   # A bus (met2)
        y = a_y0 + b * track
        box(pe, L_MET2, 0, y - wire / 2, pe_w, y + wire / 2)
    for b in range(width):                                   # B bus (met3)
        x = b_x0 + b * track
        box(pe, L_MET3, x - wire / 2, 0, x + wire / 2, pe_h)

    mac_x0 = bus_span + 2 * margin
    blk_w = pe_w - mac_x0 - margin
    blk_h = (pe_h - 3 * margin) / 2
    mac = (mac_x0, margin, mac_x0 + blk_w, margin + blk_h)
    acc = (mac_x0, 2 * margin + blk_h, mac_x0 + blk_w, 2 * margin + 2 * blk_h)
    box(pe, L_MAC, *mac)
    box(pe, L_ACC, *acc)
    text(pe, L_TXT, "MAC", (mac[0] + mac[2]) / 2, (mac[1] + mac[3]) / 2)
    text(pe, L_TXT, "ACC", (acc[0] + acc[2]) / 2, (acc[1] + acc[3]) / 2)

    ax, ay0 = b_x0 + (width - 1) * track + 2.0, a_y0           # taps into MAC
    bx, by = b_x0, margin + blk_h / 2
    box(pe, L_MET1, ax, ay0 - wire / 2, mac_x0, ay0 + wire / 2)
    box(pe, L_MET1, mac_x0 - wire, ay0 - wire / 2, mac_x0, by)
    box(pe, L_MET1, bx, by - wire / 2, mac_x0, by + wire / 2)
    v = 0.3
    box(pe, L_VIA1, ax, ay0 - v / 2, ax + v, ay0 + v / 2)
    box(pe, L_VIA2, bx - v / 2, by - v / 2, bx + v / 2, by + v / 2)

    if SHOW_POWER:                                           # met1 rails
        box(pe, L_MET1, 0, 0, pe_w, RAIL)                     # VSS (bottom)
        box(pe, L_MET1, 0, pe_h - RAIL, pe_w, pe_h)           # VDD (top)

    # ---------------- skew geometry ----------------
    REG_W, REG_H, GAP = 8.0, 6.0, 2.0
    skew_w = (n - 1) * (REG_W + GAP) + GAP if (SHOW_SKEW and n > 1) else 0.0
    skew_h = (n - 1) * (REG_H + GAP) + GAP if (SHOW_SKEW and n > 1) else 0.0

    tot_w, tot_h = n * pe_w, n * pe_h

    def ay(r, b):          # y of A-bus bit b in row r (odd rows are flipped)
        off = a_y0 + b * track
        return (r + 1) * pe_h - off if r % 2 else r * pe_h + off

    def bxx(c, b):         # x of B-bus bit b in column c
        return c * pe_w + b_x0 + b * track

    # ---------------- top ----------------
    top = ly.create_cell("MATMUL_%dx%d_W%d" % (n, n, width))
    for r in range(n):     # one AREF per row; odd rows mirrored so rails are shared
        if r % 2:
            tr = db.Trans(0, True, 0, um((r + 1) * pe_h))
        else:
            tr = db.Trans(0, False, 0, um(r * pe_h))
        top.insert(db.CellInstArray(pe.cell_index(), tr,
                                    db.Vector(um(pe_w), 0), db.Vector(0, um(pe_h)),
                                    n, 1))
    box(top, L_BND, 0, 0, tot_w, tot_h)

    # skew wires, registers and external pins
    pin = 0.6
    for r in range(n):
        for b in range(width):
            y = ay(r, b)
            if skew_w:
                box(top, L_MET2, -skew_w, y - wire / 2, 0, y + wire / 2)
            box(top, L_PIN2, -skew_w, y - pin / 2, -skew_w + pin, y + pin / 2)
        text(top, L_TXT2, "a_in%d[%d:0]" % (r, width - 1), -skew_w - 14, ay(r, 0))
        if skew_w and r >= 1:
            ys = (ay(r, 0), ay(r, width - 1))
            for k in range(r):
                x1 = -GAP - k * (REG_W + GAP)
                box(top, L_REG, x1 - REG_W, min(ys) - 1, x1, max(ys) + 1)
                if n <= 8:
                    text(top, L_TXT, "D", x1 - REG_W / 2, (ys[0] + ys[1]) / 2)
    for c in range(n):
        for b in range(width):
            x = bxx(c, b)
            if skew_h:
                box(top, L_MET3, x - wire / 2, tot_h, x + wire / 2, tot_h + skew_h)
            box(top, L_PIN3, x - pin / 2, tot_h + skew_h - pin,
                x + pin / 2, tot_h + skew_h)
        text(top, L_TXT3, "b_in%d[%d:0]" % (c, width - 1), bxx(c, 0), tot_h + skew_h + 2)
        if skew_h and c >= 1:
            x0, x1 = bxx(c, 0) - 1, bxx(c, width - 1) + 1
            for k in range(c):
                y0 = tot_h + GAP + k * (REG_H + GAP)
                box(top, L_REG, x0, y0, x1, y0 + REG_H)
                if n <= 8:
                    text(top, L_TXT, "D", (x0 + x1) / 2, y0 + REG_H / 2)
    if skew_w:
        text(top, L_TXT, "A skew: row r delayed r cycles", -skew_w, -8)
        text(top, L_TXT, "B skew: col c delayed c cycles", tot_w - 70, tot_h + skew_h + 10)

    # result pins (east), one per row
    for r in range(n):
        y = r * pe_h + pe_h / 2
        box(top, L_PIN2, tot_w - pin, y - pin / 2, tot_w, y + pin / 2)
        text(top, L_TXT2, "c_out%d" % r, tot_w + 1, y)

    # PE labels and arrows
    for r in range(n):
        for c in range(n):
            cx0, cy0 = c * pe_w, r * pe_h
            if SHOW_LABELS:
                text(top, L_TXT, "PE[%d][%d]" % (r, c),
                     cx0 + mac_x0 + 1.0, cy0 + pe_h / 2 + 0.3)
            if SHOW_ARROWS:
                yy = cy0 + pe_h / 2 - 1.2                    # A: east
                xa, xb = cx0 + mac_x0 + 0.5, cx0 + mac_x0 + blk_w - 0.5
                box(top, L_ARR_A, xa, yy - 0.25, xb - 1.2, yy + 0.25)
                poly(top, L_ARR_A, [(xb - 1.2, yy - 0.6), (xb, yy), (xb - 1.2, yy + 0.6)])
                xx = cx0 + pe_w - margin / 2                   # B: south
                yt, yb = cy0 + pe_h - 3.0, cy0 + 3.0
                box(top, L_ARR_B, xx - 0.25, yb + 1.2, xx + 0.25, yt)
                poly(top, L_ARR_B, [(xx - 0.6, yb + 1.2), (xx + 0.6, yb + 1.2), (xx, yb)])

    # power: stripes, rail labels, ring
    ring_out = 0.0
    if SHOW_POWER:
        for k in range(n + 1):
            name = "VSS" if k % 2 == 0 else "VDD"
            text(top, L_TXT1, name, 0.5, k * pe_h)
        for c in range(n + 1):
            x = c * pe_w
            box(top, L_MET4, x - 0.6, 0, x + 0.6, tot_h)
            text(top, L_TXT4, "VSS" if c % 2 == 0 else "VDD", x, -2)
        x0, x1, y0, y1 = -skew_w, tot_w, 0.0, tot_h + skew_h
        for off, nm in ((12.0, "VDD"), (15.0, "VSS")):
            w_ = 2.0
            ax0, ax1, ay_0, ay_1 = x0 - off - w_, x1 + off + w_, y0 - off - w_, y1 + off + w_
            box(top, L_MET5, ax0, ay_0, ax1, ay_0 + w_)       # bottom
            box(top, L_MET5, ax0, ay_1 - w_, ax1, ay_1)       # top
            box(top, L_MET5, ax0, ay_0, ax0 + w_, ay_1)       # left
            box(top, L_MET5, ax1 - w_, ay_0, ax1, ay_1)       # right
            text(top, L_TXT4, nm + " ring", ax0 + w_ + 1, ay_0 + w_ + 0.5)
            ring_out = off + w_

    text(top, L_TXT, "%dx%d systolic matmul, W=%d" % (n, n, width),
         tot_w / 2 - 30, tot_h + skew_h + 22)

    # ---------------- report numbers ----------------
    die_w = tot_w + skew_w + 2 * ring_out
    die_h = tot_h + skew_h + 2 * ring_out
    pe_area = pe_w * pe_h
    logic = (mac[2] - mac[0]) * (mac[3] - mac[1]) + (acc[2] - acc[0]) * (acc[3] - acc[1])
    skew_regs = n * (n - 1)                         # A triangle + B triangle (words)
    info = dict(
        N=n, WIDTH=width, PEs=n * n,
        pe_w_um=round(pe_w, 2), pe_h_um=round(pe_h, 2),
        array_w_um=round(tot_w, 1), array_h_um=round(tot_h, 1),
        die_w_um=round(die_w, 1), die_h_um=round(die_h, 1),
        die_area_mm2=round(die_w * die_h / 1e6, 5),
        array_area_mm2=round(tot_w * tot_h / 1e6, 5),
        logic_util_pct=round(100.0 * logic / pe_area, 1),
        pins=2 * n * width + n,
        wire_len_mm=round(n * n * width * (pe_w + pe_h) / 1000.0, 3),
        skew_flops=skew_regs * width,
        peak_gops=round(2.0 * n * n * CLOCK_MHZ / 1000.0, 2),
    )
    return top, info


def report_text(info):
    i = info
    return "\n".join([
        "=== MATMUL %dx%d  W=%d ===" % (i["N"], i["N"], i["WIDTH"]),
        "PEs (MACs)          : %d" % i["PEs"],
        "PE size             : %.1f x %.1f um" % (i["pe_w_um"], i["pe_h_um"]),
        "Array size          : %.1f x %.1f um (%.5f mm2)"
        % (i["array_w_um"], i["array_h_um"], i["array_area_mm2"]),
        "Die incl. skew+ring : %.1f x %.1f um (%.5f mm2)"
        % (i["die_w_um"], i["die_h_um"], i["die_area_mm2"]),
        "MAC+ACC fill of PE  : %.1f %%" % i["logic_util_pct"],
        "I/O pins            : %d" % i["pins"],
        "Bus wire length     : %.3f mm" % i["wire_len_mm"],
        "Skew flops          : %d" % i["skew_flops"],
        "Peak throughput    : %.2f GOPS @ %d MHz (estimate, 2 ops/MAC)"
        % (i["peak_gops"], CLOCK_MHZ),
    ])


# ------------------------------------------------------------- file helpers
def lyp_text():
    rows = []
    for (ld, name, col, dith) in LAYER_STYLE:
        rows.append(
            "<properties><frame-color>%s</frame-color><fill-color>%s</fill-color>"
            "<frame-brightness>0</frame-brightness><fill-brightness>0</fill-brightness>"
            "<dither-pattern>%s</dither-pattern><line-style/><valid>true</valid>"
            "<visible>true</visible><transparent>false</transparent><width/>"
            "<marked>false</marked><xfill>false</xfill><animation>0</animation>"
            "<name>%s %d/%d</name><source>%d/%d@1</source></properties>"
            % (col, col, dith, name, ld[0], ld[1], ld[0], ld[1]))
    return ('<?xml version="1.0" encoding="utf-8"?>\n<layer-properties>'
            + "".join(rows) + "</layer-properties>\n")


def _outdir():
    base = os.path.expanduser("~") if MW is not None else os.getcwd()
    d = os.path.join(base, "matmul_out")
    if not os.path.isdir(d):
        os.makedirs(d)
    return d


def sweep(sizes, width, outdir):
    rows = []
    for s in sizes:
        ly = db.Layout()
        top, info = build(ly, s, width)
        ly.write(os.path.join(outdir, "matmul_%dx%d_W%d.gds" % (s, s, width)))
        rows.append(info)
    keys = list(rows[0].keys())
    with open(os.path.join(outdir, "sweep_W%d.csv" % width), "w") as f:
        f.write(",".join(keys) + "\n")
        for r in rows:
            f.write(",".join(str(r[k]) for k in keys) + "\n")
    print("\nN    PEs   die_mm2     skew_flops  pins  GOPS")
    for r in rows:
        print("%-4d %-5d %-11.5f %-11d %-5d %.2f"
              % (r["N"], r["PEs"], r["die_area_mm2"], r["skew_flops"], r["pins"], r["peak_gops"]))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        xs = [r["N"] for r in rows]
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(xs, [r["die_area_mm2"] for r in rows], "o-")
        ax.set_xlabel("N (array is N x N)")
        ax.set_ylabel("die area (mm2)")
        ax.set_title("Area vs array size, W=%d" % width)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(outdir, "area_vs_N_W%d.png" % width), dpi=150)
        print("plot saved")
    except Exception:
        print("(matplotlib not available - CSV written, plot skipped)")
    print("sweep files in: %s" % outdir)


def _run():
    n, width = N, WIDTH
    if MW is None and len(sys.argv) > 1:
        n = int(sys.argv[1])
        if len(sys.argv) > 2:
            width = int(sys.argv[2])
    outdir = _outdir()
    fname = "matmul_%dx%d_W%d.gds" % (n, n, width)
    lyp = os.path.join(outdir, "matmul_layers.lyp")
    with open(lyp, "w") as f:
        f.write(lyp_text())

    if MW is not None:
        cv = MW.create_layout(1)
        ly = cv.layout()
        top, info = build(ly, n, width)
        view = MW.current_view()
        view.select_cell(top.cell_index(), cv.index())
        view.add_missing_layers()
        try:
            view.load_layer_props(lyp)
        except Exception as e:
            print("layer colours not applied (%s)" % e)
        view.add_missing_layers()
        view.max_hier()
        view.zoom_fit()
    else:
        ly = db.Layout()
        top, info = build(ly, n, width)

    out = os.path.join(outdir, fname)
    ly.write(out)
    rep = report_text(info)
    with open(os.path.join(outdir, "report_%dx%d_W%d.txt" % (n, n, width)), "w") as f:
        f.write(rep + "\n")
    print(rep)
    print("layout saved: %s" % out)
    if SWEEP:
        sweep(SWEEP, width, outdir)


if not os.environ.get("MATMUL_NO_RUN"):
    _run()
