// Procedural 1929 scene plates.
//
// These stand in for the generated background plates so the animation rig can be
// judged (camera language, Elly layer, caption/subtitle placement) before any
// background art is committed. They follow the brief's visual master: flat
// colour, thick clean outlines, simple stickmen, warm cream/gold base with the
// Part 0 colour arc (cold charcoal -> crash red -> muted bronze).
//
// Absolutely no text is drawn here: captions and labels are edit overlays.

const OUT = "#1b1a1c";        // outline ink
const INK = 7;                // outline width

function bg(ctx, top, bottom) {
  const g = ctx.createLinearGradient(0, 0, 0, 1080);
  g.addColorStop(0, top);
  g.addColorStop(1, bottom);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 1920, 1080);
}

function ground(ctx, y, color) {
  ctx.fillStyle = color;
  ctx.fillRect(0, y, 1920, 1080 - y);
  ctx.strokeStyle = OUT;
  ctx.lineWidth = INK;
  ctx.beginPath();
  ctx.moveTo(0, y);
  ctx.lineTo(1920, y);
  ctx.stroke();
}

// A stickman: circle head, thin line body. Wardrobe/props only, per the brief.
function stick(ctx, x, y, h, o = {}) {
  const head = h * 0.19;
  const bodyY = y - h + head * 2;
  ctx.save();
  ctx.translate(x, y);
  if (o.lean) ctx.rotate(o.lean);
  ctx.translate(-x, -y);

  ctx.strokeStyle = o.color || OUT;
  ctx.lineWidth = o.w || 9;
  ctx.lineCap = "round";

  // legs
  ctx.beginPath();
  ctx.moveTo(x, y - (h - head * 2));
  ctx.lineTo(x - h * 0.13, y);
  ctx.moveTo(x, y - (h - head * 2));
  ctx.lineTo(x + h * 0.13, y);
  ctx.stroke();

  // torso
  ctx.beginPath();
  ctx.moveTo(x, y - (h - head * 2));
  ctx.lineTo(x, bodyY + head * 0.6);
  ctx.stroke();

  // arms: [angle1, angle2] in turns, or a preset name
  const arms = o.arms || "down";
  ctx.beginPath();
  if (arms === "down") {
    ctx.moveTo(x, bodyY + head * 0.9);
    ctx.lineTo(x - h * 0.16, y - h * 0.28);
    ctx.moveTo(x, bodyY + head * 0.9);
    ctx.lineTo(x + h * 0.16, y - h * 0.28);
  } else if (arms === "up") {
    ctx.moveTo(x, bodyY + head * 0.9);
    ctx.lineTo(x - h * 0.18, bodyY - head * 0.5);
    ctx.moveTo(x, bodyY + head * 0.9);
    ctx.lineTo(x + h * 0.18, bodyY - head * 0.5);
  } else if (arms === "out") {
    ctx.moveTo(x, bodyY + head * 0.9);
    ctx.lineTo(x - h * 0.3, bodyY + head * 0.5);
    ctx.moveTo(x, bodyY + head * 0.9);
    ctx.lineTo(x + h * 0.3, bodyY + head * 0.5);
  } else if (arms === "point") {
    ctx.moveTo(x, bodyY + head * 0.9);
    ctx.lineTo(x - h * 0.1, y - h * 0.3);
    ctx.moveTo(x, bodyY + head * 0.9);
    ctx.lineTo(x + h * 0.34, bodyY + head * 0.2);
  } else if (arms === "beg") {
    ctx.moveTo(x, bodyY + head * 0.9);
    ctx.lineTo(x - h * 0.2, bodyY + head * 0.2);
    ctx.moveTo(x, bodyY + head * 0.9);
    ctx.lineTo(x + h * 0.2, bodyY + head * 0.2);
  }
  ctx.stroke();

  // head
  ctx.fillStyle = o.headColor || "#efe6d5";
  ctx.beginPath();
  ctx.arc(x, bodyY, head, 0, Math.PI * 2);
  ctx.fill();
  ctx.lineWidth = o.w || 9;
  ctx.stroke();

  if (o.hat) {
    ctx.fillStyle = o.hat;
    ctx.beginPath();
    ctx.ellipse(x, bodyY - head * 0.72, head * 1.5, head * 0.34, 0, 0, Math.PI * 2);
    ctx.fill(); ctx.stroke();
    ctx.beginPath();
    ctx.ellipse(x, bodyY - head * 0.9, head * 0.95, head * 0.5, 0, 0, Math.PI * 2);
    ctx.fill(); ctx.stroke();
  }
  if (o.vest) {
    ctx.fillStyle = o.vest;
    ctx.fillRect(x - h * 0.075, bodyY + head * 0.7, h * 0.15, (h - head * 2) * 0.52);
  }
  ctx.restore();
}

function coin(ctx, x, y, r, rot = 0) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rot);
  ctx.fillStyle = "#e2b552";
  ctx.beginPath();
  ctx.ellipse(0, 0, r, r * (rot ? 0.42 : 1), 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.lineWidth = INK;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.restore();
}

function building(ctx, x, w, h, color, windows) {
  ctx.fillStyle = color;
  ctx.fillRect(x, 1080 - h, w, h);
  ctx.strokeStyle = OUT;
  ctx.lineWidth = INK;
  ctx.strokeRect(x, 1080 - h, w, h);
  if (windows) {
    ctx.fillStyle = "rgba(255,214,140,.55)";
    for (let r = 0; r < Math.floor(h / 90) - 1; r++) {
      for (let c = 0; c < Math.floor(w / 70) - 1; c++) {
        if ((r * 7 + c * 3 + x) % 5 < 2) continue;
        ctx.fillRect(x + 34 + c * 70, 1080 - h + 50 + r * 90, 34, 46);
      }
    }
  }
}

function skyline(ctx, color, yBase, seed) {
  let x = -40;
  let s = seed;
  while (x < 1960) {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    const w = 90 + (s % 130);
    const h = 190 + ((s >> 7) % 380);
    building(ctx, x, w, h + (1080 - yBase) * 0, color, true);
    ctx.save();
    ctx.translate(0, 1080 - yBase - h);
    building(ctx, x, w, h, color, true);
    ctx.restore();
    x += w + 26;
  }
}

function arrow(ctx, x1, y1, x2, y2, color, w = 14) {
  ctx.strokeStyle = color;
  ctx.lineWidth = w;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
  const a = Math.atan2(y2 - y1, x2 - x1);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - 42 * Math.cos(a - 0.42), y2 - 42 * Math.sin(a - 0.42));
  ctx.lineTo(x2 - 42 * Math.cos(a + 0.42), y2 - 42 * Math.sin(a + 0.42));
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = OUT;
  ctx.lineWidth = INK;
  ctx.stroke();
}

function chart(ctx, x, y, w, h, dir, t) {
  ctx.strokeStyle = OUT;
  ctx.lineWidth = INK;
  ctx.strokeRect(x, y, w, h);
  const pts = 8;
  const shown = Math.max(2, Math.floor(pts * Math.min(1, t * 1.4)));
  ctx.beginPath();
  for (let i = 0; i < shown; i++) {
    const px = x + (w / (pts - 1)) * i;
    const k = i / (pts - 1);
    const py = dir > 0 ? y + h * (0.85 - k * 0.7) : y + h * (0.15 + k * 0.7);
    i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
  }
  ctx.strokeStyle = dir > 0 ? "#5f9e63" : "#c0453c";
  ctx.lineWidth = 16;
  ctx.lineCap = "round";
  ctx.stroke();
}

// --------------------------------------------------------------------------

export const SCENES = {
  // S01 - October 1929, calendar over Manhattan
  skyline(ctx, t) {
    bg(ctx, "#23252b", "#3a3630");
    skyline(ctx, "#2b2d34", 900, 7);
    ground(ctx, 900, "#241f1a");
    for (let i = 0; i < 9; i++) {
      stick(ctx, 120 + i * 190 + ((t * 40) % 60), 890, 90, { w: 6 });
    }
    // calendar leaf
    ctx.save();
    ctx.translate(430, 430);
    ctx.rotate(-0.12 + t * 0.05);
    ctx.fillStyle = "#efe6d5";
    ctx.fillRect(-150, -180, 300, 360);
    ctx.lineWidth = INK;
    ctx.strokeStyle = OUT;
    ctx.strokeRect(-150, -180, 300, 360);
    ctx.fillStyle = "#c0453c";
    ctx.fillRect(-150, -180, 300, 62);
    ctx.strokeRect(-150, -180, 300, 62);
    ctx.restore();
  },

  // S02 - exchange floor, traders run, chart plunges
  exchange(ctx, t) {
    bg(ctx, "#2a2226", "#4a2b2b");
    ground(ctx, 830, "#3a2422");
    chart(ctx, 1080, 250, 620, 420, -1, t);
    for (let i = 0; i < 7; i++) {
      const x = 200 + i * 150 + Math.sin(t * 6 + i) * 26;
      stick(ctx, x, 830, 150, { arms: "up", w: 8 });
    }
  },

  // S03 - coin stacks topple
  coins(ctx, t) {
    bg(ctx, "#2b2622", "#463a2c");
    ground(ctx, 870, "#3a3128");
    const fall = Math.min(1, t * 1.5);
    for (let s = 0; s < 4; s++) {
      const bx = 300 + s * 330;
      const n = 5 - s;
      for (let i = 0; i < n; i++) {
        const lean = fall * (0.5 + s * 0.25) * (i / Math.max(1, n));
        coin(ctx, bx + lean * 170, 860 - i * 62 - fall * s * 8, 52, lean);
      }
    }
    stick(ctx, 1750, 870, 210, { arms: "up", w: 10 });
  },

  // S04 - bedside breakfast, emptied envelope
  breakfast(ctx, t) {
    bg(ctx, "#33291f", "#54402c");
    ground(ctx, 900, "#3c2f22");
    ctx.fillStyle = "#efe6d5";
    ctx.fillRect(360, 430, 520, 340);
    ctx.lineWidth = INK; ctx.strokeStyle = OUT;
    ctx.strokeRect(360, 430, 520, 340);
    ctx.beginPath();
    ctx.moveTo(620, 430); ctx.lineTo(620, 770);
    ctx.stroke();
    // blank chart on the page - no text, per policy
    chart(ctx, 385, 470, 200, 250, -1, Math.min(1, t * 2));
    // envelope emptying
    ctx.fillStyle = "#e8dcc4";
    ctx.beginPath();
    ctx.moveTo(1180, 520); ctx.lineTo(1600, 520);
    ctx.lineTo(1600, 780); ctx.lineTo(1180, 780);
    ctx.closePath();
    ctx.fill(); ctx.stroke();
    for (let i = 0; i < 5; i++) {
      const k = Math.max(0, Math.min(1, t * 2 - i * 0.12));
      ctx.save();
      ctx.translate(1300 + i * 40, 560 + k * 260);
      ctx.rotate(k * 3);
      ctx.fillStyle = "#f0e8d8";
      ctx.fillRect(-40, -26, 80, 52);
      ctx.strokeRect(-40, -26, 80, 52);
      ctx.restore();
    }
  },

  // S05 - breadline outside shuttered bank
  breadline(ctx, t) {
    bg(ctx, "#26262a", "#3d3a34");
    ground(ctx, 880, "#2f2c27");
    building(ctx, 1180, 620, 470, "#3a3630", false);
    ctx.fillStyle = "#241f1b";
    ctx.fillRect(1240, 700, 500, 200);
    ctx.lineWidth = INK; ctx.strokeStyle = OUT;
    ctx.strokeRect(1240, 700, 500, 200);
    for (let i = 0; i < 3; i++) {
      ctx.beginPath();
      ctx.moveTo(1240, 720 + i * 60);
      ctx.lineTo(1740, 720 + i * 60);
      ctx.stroke();
    }
    for (let i = 0; i < 8; i++) {
      stick(ctx, 170 + i * 132, 880, 165, { arms: "down", w: 8, lean: 0.05 });
    }
  },

  // S06 - split screen: panic left, calm right
  split(ctx, t) {
    bg(ctx, "#2a2226", "#3b2b2b");
    ctx.fillStyle = "#3d2b2b";
    ctx.fillRect(0, 0, 960, 1080);
    ctx.fillStyle = "#2b3230";
    ctx.fillRect(960, 0, 960, 1080);
    ctx.strokeStyle = OUT; ctx.lineWidth = INK;
    ctx.beginPath(); ctx.moveTo(960, 0); ctx.lineTo(960, 1080); ctx.stroke();
    ground(ctx, 860, "rgba(0,0,0,.25)");
    chart(ctx, 90, 260, 520, 420, -1, t);
    for (let i = 0; i < 4; i++) stick(ctx, 200 + i * 170, 860, 160, { arms: "up", w: 8 });
    for (let i = 0; i < 5; i++) coin(ctx, 1420 + (i % 2) * 90, 820 - i * 62, 54);
    stick(ctx, 1690, 860, 230, { arms: "down", w: 10, vest: "#cfd6dd" });
  },

  // S07 - Jesse hero
  hero(ctx, t) {
    bg(ctx, "#242029", "#3b3340");
    ground(ctx, 880, "#2c2731");
    stick(ctx, 620, 880, 430, { arms: "down", w: 13, vest: "#2a2a33", headColor: "#efe6d5" });
    // ticker
    ctx.fillStyle = "#d9c9a3";
    ctx.fillRect(1150, 520, 620, 150);
    ctx.lineWidth = INK; ctx.strokeStyle = OUT;
    ctx.strokeRect(1150, 520, 620, 150);
    for (let i = 0; i < 9; i++) {
      const on = ((t * 9 + i) | 0) % 3;
      ctx.fillStyle = on ? "#8d7b52" : "#efe6d5";
      ctx.fillRect(1180 + i * 62, 560, 40, 70);
    }
  },

  // S08 - crowd staring up, Jesse points down
  crowd(ctx, t) {
    bg(ctx, "#2b2530", "#453041");
    ground(ctx, 890, "#332a34");
    const bx = 1520 + Math.sin(t * 4) * 8;
    arrow(ctx, bx, 250, bx, 620, "#c0453c", 22);
    for (let i = 0; i < 9; i++) {
      stick(ctx, 180 + i * 165, 890, 170, { arms: "up", w: 8, lean: -0.12 });
    }
    stick(ctx, 900, 890, 300, { arms: "point", w: 11, vest: "#2a2a33" });
  },

  // S09 - chart falls stepwise, coin chips accrue
  chips(ctx, t) {
    bg(ctx, "#2a2226", "#4a2f2b");
    ground(ctx, 880, "#3a2622");
    chart(ctx, 260, 260, 700, 460, -1, Math.min(1, t * 1.6));
    const n = Math.floor(Math.min(1, t * 1.4) * 7);
    for (let i = 0; i < n; i++) coin(ctx, 1250 + (i % 3) * 110, 800 - i * 60, 58);
    stick(ctx, 1700, 880, 250, { arms: "out", w: 10, vest: "#2a2a33" });
  },

  // S10 - doorway reveal: Kennedy
  doorway(ctx, t) {
    bg(ctx, "#232028", "#3a3540");
    ground(ctx, 890, "#2c2833");
    const k = Math.min(1, t * 1.8);
    ctx.fillStyle = "#1a171c";
    ctx.fillRect(1120, 250, 520, 640);
    ctx.lineWidth = INK; ctx.strokeStyle = OUT;
    ctx.strokeRect(1120, 250, 520, 640);
    ctx.save();
    ctx.beginPath();
    ctx.rect(1120, 250, 520 * k, 640);
    ctx.clip();
    ctx.fillStyle = "#4a4030";
    ctx.fillRect(1120, 250, 520, 640);
    stick(ctx, 1380, 890, 340, { arms: "down", w: 12, vest: "#d8d2c0", hat: "#3a3630" });
    ctx.restore();
    stick(ctx, 430, 890, 250, { arms: "down", w: 10, vest: "#2a2a33" });
  },

  // S11 - triptych
  triptych(ctx, t) {
    bg(ctx, "#26242a", "#3a3630");
    for (let i = 0; i < 3; i++) {
      const x = 90 + i * 610;
      const px = Math.sin(t * 2.2 + i) * 22;
      ctx.fillStyle = ["#3d2b2b", "#31403a", "#3a352c"][i];
      ctx.fillRect(x + px, 210, 540, 640);
      ctx.lineWidth = INK; ctx.strokeStyle = OUT;
      ctx.strokeRect(x + px, 210, 540, 640);
      if (i === 0) stick(ctx, x + 270 + px, 800, 230, { arms: "beg", w: 10 });
      if (i === 1) chart(ctx, x + 90 + px, 400, 360, 300, -1, Math.min(1, t * 1.5));
      if (i === 2) {
        ctx.fillStyle = "#efe6d5";
        ctx.fillRect(x + 150 + px, 430, 260, 320);
        ctx.strokeRect(x + 150 + px, 430, 260, 320);
      }
    }
  },

  // S12 - three icons: bulb, dice, paper
  icons(ctx, t) {
    bg(ctx, "#24222b", "#3b3644");
    const show = Math.min(3, Math.floor(t * 4) + 1);
    for (let i = 0; i < show; i++) {
      const x = 420 + i * 430;
      const pop = Math.max(0, Math.min(1, (t * 4 - i)));
      ctx.save();
      ctx.translate(x, 520);
      ctx.scale(0.7 + pop * 0.3, 0.7 + pop * 0.3);
      ctx.lineWidth = INK; ctx.strokeStyle = OUT;
      if (i === 0) {
        ctx.fillStyle = "#e8c65c";
        ctx.beginPath(); ctx.arc(0, 0, 110, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.fillStyle = "#8a6f2a"; ctx.fillRect(-46, 110, 92, 60); ctx.strokeRect(-46, 110, 92, 60);
      } else if (i === 1) {
        ctx.fillStyle = "#efe6d5";
        ctx.fillRect(-100, -100, 200, 200); ctx.strokeRect(-100, -100, 200, 200);
        ctx.fillStyle = OUT;
        [[-46, -46], [46, 46], [0, 0], [46, -46], [-46, 46]].forEach(([a, b]) => {
          ctx.beginPath(); ctx.arc(a, b, 20, 0, Math.PI * 2); ctx.fill();
        });
      } else {
        ctx.fillStyle = "#f0e8d8";
        ctx.fillRect(-95, -125, 190, 250); ctx.strokeRect(-95, -125, 190, 250);
      }
      ctx.restore();
    }
  },

  // S13 - question mark + ticker
  mystery(ctx, t) {
    bg(ctx, "#1f1d24", "#332c38");
    ctx.save();
    ctx.translate(760, 500);
    ctx.scale(3.1, 3.1);
    ctx.fillStyle = "#d8a24a";
    ctx.font = "bold 150px Georgia, serif";
    ctx.strokeStyle = OUT;
    ctx.lineWidth = 10;
    ctx.strokeText("?", 0, 0);
    ctx.fillText("?", 0, 0);
    ctx.restore();
    ctx.fillStyle = "#d9c9a3";
    ctx.fillRect(1180, 560, 560, 130);
    ctx.lineWidth = INK; ctx.strokeStyle = OUT;
    ctx.strokeRect(1180, 560, 560, 130);
    for (let i = 0; i < 8; i++) {
      ctx.fillStyle = ((t * 8 + i) | 0) % 3 ? "#8d7b52" : "#efe6d5";
      ctx.fillRect(1205 + i * 64, 594, 42, 62);
    }
  },

  // S14 - stacked coins vanish
  vanish(ctx, t) {
    bg(ctx, "#26222a", "#3b3138");
    ground(ctx, 900, "#2f2a31");
    const gone = Math.min(1, t * 1.3);
    for (let i = 0; i < 8; i++) {
      const k = Math.max(0, Math.min(1, gone * 1.6 - i * 0.14));
      ctx.globalAlpha = 1 - k;
      coin(ctx, 700, 870 - i * 62, 62);
      ctx.globalAlpha = 1;
    }
    stick(ctx, 1180, 900, 300, { arms: "down", w: 11, vest: "#2a2a33", lean: 0.04 });
  },

  // S15 - balance scale, MAKE vs KEEP
  scales(ctx, t) {
    bg(ctx, "#26232c", "#3d3742");
    ground(ctx, 900, "#302b34");
    const tilt = Math.sin(t * 2.4) * 0.22;
    ctx.save();
    ctx.translate(880, 300);
    ctx.rotate(tilt);
    ctx.strokeStyle = OUT; ctx.lineWidth = 16;
    ctx.beginPath(); ctx.moveTo(-420, 0); ctx.lineTo(420, 0); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, -60); ctx.lineTo(0, 60); ctx.stroke();
    [[-420, 1], [420, 1]].forEach(([x]) => {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, 150); ctx.stroke();
      ctx.beginPath(); ctx.ellipse(x, 165, 150, 34, 0, 0, Math.PI * 2);
      ctx.fillStyle = "#8a7c5e"; ctx.fill(); ctx.stroke();
    });
    ctx.restore();
    for (let i = 0; i < 3; i++) coin(ctx, -880 + 0 + 460, 300 + 165 + 130, 0); // no-op guard
    ctx.save();
    ctx.translate(880, 300);
    ctx.rotate(tilt);
    coin(ctx, -420, 120, 56); coin(ctx, -360, 88, 56);
    coin(ctx, 420, 120, 56);
    ctx.restore();
    stick(ctx, 1600, 900, 250, { arms: "point", w: 10 });
  },

  // S16 - brightening 1920s city, crash recedes
  city(ctx, t) {
    const warm = Math.min(1, t * 1.4);
    bg(ctx,
      `rgb(${35 + warm * 90},${37 + warm * 80},${43 + warm * 40})`,
      `rgb(${58 + warm * 120},${54 + warm * 90},${48 + warm * 40})`);
    skyline(ctx, `rgb(${43 + warm * 90},${45 + warm * 80},${52 + warm * 50})`, 920, 21);
    ground(ctx, 920, "#4a3f2c");
    for (let i = 0; i < 6; i++) {
      stick(ctx, 240 + i * 280, 920, 150, { arms: "up", w: 8 });
    }
    ctx.globalAlpha = 1 - warm;
    chart(ctx, 1330, 250, 480, 300, -1, 1);
    ctx.globalAlpha = 1;
    for (let i = 0; i < 26; i++) {
      const s = (i * 9301 + 49297) % 233280;
      ctx.fillStyle = ["#e8c65c", "#c0453c", "#e2b552", "#efe6d5"][i % 4];
      ctx.fillRect((s % 1900), ((s / 7) % 700) + warm * 120, 14, 22);
    }
  },
};

export const SCENE_KEYS = Object.keys(SCENES);
